from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views import View

from base.forms import (
    TripReuseForm,
)

from base.models import (
    Trip,
    Location,
    DayLocation,
    Schedule,
    TripExpense,
    TripHashtag,
    TripReferenceUrl,
    DayReferenceUrl,
    ScheduleReferenceUrl,
    TripExpenseReferenceUrl,
)

from .trip_services import (
    sync_trip_days,
)


# =========================================
# Trip再利用
# =========================================

class TripReuseView(
    LoginRequiredMixin,
    View,
):

    template_name = (
        "pages/trip/trip_reuse.html"
    )

    # =====================================
    # 参考元Trip取得
    #
    # 自分のTrip
    # ・旅完了であれば再利用可能
    # ・公開 / 非公開は問わない
    # ・保存は不要
    #
    # 他ユーザーのTrip
    # ・旅完了
    # ・公開中
    # ・自分が保存しているTrip
    # =====================================

    def get_source_trip(
        self,
    ):

        queryset = (
            Trip.objects
            .filter(
                Q(
                    user=self.request.user,
                    status="completed",
                )
                | Q(
                    status="completed",
                    is_public=True,
                    saves__user=(
                        self.request.user
                    ),
                )
            )
            .select_related(
                "user",
                "category",
            )
            .distinct()
        )

        return get_object_or_404(
            queryset,
            pk=self.kwargs["pk"],
        )

    # =====================================
    # Context
    # =====================================

    def get_context_data(
        self,
        source_trip,
        form,
    ):

        trip_days = (
            (
                source_trip.end_date
                - source_trip.start_date
            ).days
            + 1
        )

        return {
            "source_trip": (
                source_trip
            ),
            "form": (
                form
            ),
            "trip_days": (
                trip_days
            ),
        }

    # =====================================
    # 開始日入力画面
    # =====================================

    def get(
        self,
        request,
        *args,
        **kwargs,
    ):

        source_trip = (
            self.get_source_trip()
        )

        form = (
            TripReuseForm()
        )

        context = (
            self.get_context_data(
                source_trip,
                form,
            )
        )

        return render(
            request,
            self.template_name,
            context,
        )

    # =====================================
    # Trip再利用実行
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):

        source_trip = (
            self.get_source_trip()
        )

        form = (
            TripReuseForm(
                request.POST
            )
        )

        if not form.is_valid():

            context = (
                self.get_context_data(
                    source_trip,
                    form,
                )
            )

            return render(
                request,
                self.template_name,
                context,
            )

        new_start_date = (
            form.cleaned_data[
                "start_date"
            ]
        )

        # =====================================
        # 元Tripと同じ旅行日数で
        # 新しい終了日を計算
        # =====================================

        date_difference = (
            source_trip.end_date
            - source_trip.start_date
        )

        new_end_date = (
            new_start_date
            + date_difference
        )

        # =====================================
        # Trip一式をコピー
        # =====================================

        with transaction.atomic():

            new_trip = (
                self.create_reused_trip(
                    source_trip=(
                        source_trip
                    ),
                    start_date=(
                        new_start_date
                    ),
                    end_date=(
                        new_end_date
                    ),
                )
            )

        return redirect(
            "trip_detail",
            pk=new_trip.trip_id,
        )

    # =====================================
    # 新しいTrip作成
    # =====================================

    def create_reused_trip(
        self,
        source_trip,
        start_date,
        end_date,
    ):

        new_trip = (
            Trip.objects.create(
                user=(
                    self.request.user
                ),

                # =================================
                # 参考元情報
                #
                # 自分のTrip再利用時も
                # DB上では参考元を保持する
                #
                # ただし画面では
                # 「参考：自分」は表示しない
                # =================================

                source_trip=(
                    source_trip
                ),
                source_user=(
                    source_trip.user
                ),

                category=(
                    source_trip.category
                ),
                title=(
                    source_trip.title
                ),
                start_date=(
                    start_date
                ),
                end_date=(
                    end_date
                ),

                # =================================
                # コピーしない情報
                # =================================

                main_media="",
                total_cost=None,
                memo="",
                overview="",

                # =================================
                # 新規Tripとして作成
                # =================================

                status="draft",
                is_public=False,
            )
        )

        # =====================================
        # 新しい期間に合わせて
        # Dayを自動生成
        # =====================================

        sync_trip_days(
            new_trip
        )

        # =====================================
        # 訪問先
        # =====================================

        location_map = (
            self.copy_locations(
                source_trip,
                new_trip,
            )
        )

        # =====================================
        # ハッシュタグ
        # =====================================

        self.copy_hashtags(
            source_trip,
            new_trip,
        )

        # =====================================
        # Trip参考URL
        # =====================================

        self.copy_trip_reference_urls(
            source_trip,
            new_trip,
        )

        # =====================================
        # Trip全体費用
        # =====================================

        self.copy_trip_expenses(
            source_trip,
            new_trip,
        )

        # =====================================
        # Day・Schedule
        # =====================================

        self.copy_days(
            source_trip=(
                source_trip
            ),
            new_trip=(
                new_trip
            ),
            location_map=(
                location_map
            ),
        )

        return new_trip

    # =====================================
    # Locationコピー
    #
    # 元Location ID
    # ↓
    # 新Location
    #
    # の対応表も返す
    # =====================================

    def copy_locations(
        self,
        source_trip,
        new_trip,
    ):

        location_map = {}

        source_locations = (
            source_trip
            .locations
            .all()
            .order_by(
                "location_id"
            )
        )

        for source_location in (
            source_locations
        ):

            new_location = (
                Location.objects.create(
                    trip=(
                        new_trip
                    ),
                    country=(
                        source_location.country
                    ),
                    region=(
                        source_location.region
                    ),
                )
            )

            location_map[
                source_location.location_id
            ] = new_location

        return location_map

    # =====================================
    # ハッシュタグコピー
    # =====================================

    def copy_hashtags(
        self,
        source_trip,
        new_trip,
    ):

        source_trip_hashtags = (
            source_trip
            .trip_hashtags
            .select_related(
                "hashtag"
            )
            .all()
        )

        for source_trip_hashtag in (
            source_trip_hashtags
        ):

            TripHashtag.objects.create(
                trip=(
                    new_trip
                ),
                hashtag=(
                    source_trip_hashtag.hashtag
                ),
            )

    # =====================================
    # Trip参考URLコピー
    # =====================================

    def copy_trip_reference_urls(
        self,
        source_trip,
        new_trip,
    ):

        source_reference_urls = (
            source_trip
            .reference_urls
            .order_by(
                "url_order"
            )
        )

        for source_url in (
            source_reference_urls
        ):

            TripReferenceUrl.objects.create(
                trip=(
                    new_trip
                ),
                title=(
                    source_url.title
                ),
                url=(
                    source_url.url
                ),
                url_order=(
                    source_url.url_order
                ),
            )

    # =====================================
    # Trip全体費用コピー
    #
    # 元の予定金額がある
    # → 予定金額を使用
    #
    # 元の予定金額がなく
    # 実際支払額がある
    # → 実際支払額を
    #   新Tripの予定金額として使用
    #
    # 実際支払額そのものはコピーしない
    # =====================================

    def copy_trip_expenses(
        self,
        source_trip,
        new_trip,
    ):

        source_expenses = (
            source_trip
            .trip_expenses
            .order_by(
                "expense_order",
                "trip_expense_id",
            )
        )

        for source_expense in (
            source_expenses
        ):

            # =================================
            # 新Tripの予定金額
            #
            # 予定金額あり
            # → 予定金額
            #
            # 予定金額なし
            # → 実際支払額
            # =================================

            if (
                source_expense.planned_amount
                is not None
            ):

                planned_amount = (
                    source_expense
                    .planned_amount
                )

            else:

                planned_amount = (
                    source_expense
                    .actual_amount
                )

            new_expense = (
                TripExpense.objects.create(
                    trip=(
                        new_trip
                    ),
                    name=(
                        source_expense.name
                    ),
                    planned_amount=(
                        planned_amount
                    ),

                    # =================================
                    # 実際支払額はコピーしない
                    # =================================

                    actual_amount=None,

                    memo=(
                        source_expense.memo
                    ),
                    expense_order=(
                        source_expense
                        .expense_order
                    ),
                )
            )

            # =====================================
            # Trip全体費用参考URL
            # =====================================

            source_reference_urls = (
                source_expense
                .reference_urls
                .order_by(
                    "url_order"
                )
            )

            for source_url in (
                source_reference_urls
            ):

                TripExpenseReferenceUrl.objects.create(
                    trip_expense=(
                        new_expense
                    ),
                    title=(
                        source_url.title
                    ),
                    url=(
                        source_url.url
                    ),
                    url_order=(
                        source_url.url_order
                    ),
                )

    # =====================================
    # Dayコピー
    # =====================================

    def copy_days(
        self,
        source_trip,
        new_trip,
        location_map,
    ):

        source_days = (
            source_trip
            .days
            .all()
            .order_by(
                "day_order"
            )
        )

        for source_day in (
            source_days
        ):

            # =================================
            # 元Trip開始日から
            # 何日目か計算
            # =================================

            date_offset = (
                source_day.date
                - source_trip.start_date
            ).days

            new_day_date = (
                new_trip.start_date
                + timedelta(
                    days=date_offset
                )
            )

            # =================================
            # sync_trip_daysで
            # 作られたDayを取得
            # =================================

            new_day = (
                new_trip
                .days
                .get(
                    date=new_day_date
                )
            )

            # =================================
            # Day予定金額
            #
            # 元の予定金額あり
            # → 予定金額を使用
            #
            # 元の予定金額なし
            # ＋
            # 元の実際支払額あり
            # → 実際支払額を
            #   新Dayの予定金額として使用
            # =================================

            if (
                source_day.planned_amount
                is not None
            ):

                planned_amount = (
                    source_day
                    .planned_amount
                )

            else:

                planned_amount = (
                    source_day
                    .actual_amount
                )

            # =================================
            # 計画情報をコピー
            # =================================

            new_day.title = (
                source_day.title
            )

            new_day.memo = (
                source_day.memo
            )

            new_day.budget = (
                source_day.budget
            )

            new_day.planned_amount = (
                planned_amount
            )

            # =================================
            # 実際支払額・旅の記録はコピーしない
            # =================================

            new_day.actual_amount = (
                None
            )

            new_day.actual_cost = (
                None
            )

            new_day.content = (
                ""
            )

            new_day.media = (
                ""
            )

            new_day.save(
                update_fields=[
                    "title",
                    "memo",
                    "budget",
                    "planned_amount",
                    "actual_amount",
                    "actual_cost",
                    "content",
                    "media",
                ]
            )

            # =================================
            # Day訪問先
            # =================================

            self.copy_day_locations(
                source_day=(
                    source_day
                ),
                new_day=(
                    new_day
                ),
                location_map=(
                    location_map
                ),
            )

            # =================================
            # Day参考URL
            # =================================

            self.copy_day_reference_urls(
                source_day,
                new_day,
            )

            # =================================
            # Schedule
            # =================================

            self.copy_schedules(
                source_day,
                new_day,
            )

            # =================================
            # DayExpenseはコピーしない
            #
            # 食事・コンビニ・細かな交通費など
            # 元の旅行で実際に使った費用明細のため
            # =================================

    # =====================================
    # DayLocationコピー
    # =====================================

    def copy_day_locations(
        self,
        source_day,
        new_day,
        location_map,
    ):

        source_day_locations = (
            source_day
            .day_locations
            .select_related(
                "location"
            )
            .order_by(
                "location_order"
            )
        )

        for source_day_location in (
            source_day_locations
        ):

            new_location = (
                location_map.get(
                    source_day_location
                    .location_id
                )
            )

            if new_location is None:

                continue

            DayLocation.objects.create(
                day=(
                    new_day
                ),
                location=(
                    new_location
                ),
                location_order=(
                    source_day_location
                    .location_order
                ),
            )

    # =====================================
    # Day参考URLコピー
    # =====================================

    def copy_day_reference_urls(
        self,
        source_day,
        new_day,
    ):

        source_reference_urls = (
            source_day
            .reference_urls
            .order_by(
                "url_order"
            )
        )

        for source_url in (
            source_reference_urls
        ):

            DayReferenceUrl.objects.create(
                day=(
                    new_day
                ),
                title=(
                    source_url.title
                ),
                url=(
                    source_url.url
                ),
                url_order=(
                    source_url.url_order
                ),
            )

    # =====================================
    # Scheduleコピー
    # =====================================

    def copy_schedules(
        self,
        source_day,
        new_day,
    ):

        source_schedules = (
            source_day
            .schedules
            .order_by(
                "schedule_order",
                "schedule_id",
            )
        )

        for source_schedule in (
            source_schedules
        ):

            # =================================
            # Schedule予定金額
            #
            # 元の予定金額あり
            # → 予定金額を使用
            #
            # 元の予定金額なし
            # ＋
            # 元の実際支払額あり
            # → 実際支払額を
            #   新Scheduleの予定金額として使用
            # =================================

            if (
                source_schedule.planned_amount
                is not None
            ):

                planned_amount = (
                    source_schedule
                    .planned_amount
                )

            else:

                planned_amount = (
                    source_schedule
                    .actual_amount
                )

            new_schedule = (
                Schedule.objects.create(
                    day=(
                        new_day
                    ),
                    start_time=(
                        source_schedule
                        .start_time
                    ),
                    end_time=(
                        source_schedule
                        .end_time
                    ),
                    name=(
                        source_schedule.name
                    ),
                    memo=(
                        source_schedule.memo
                    ),

                    # =================================
                    # 金額
                    # =================================

                    planned_amount=(
                        planned_amount
                    ),

                    # =================================
                    # 実際支払額はコピーしない
                    # =================================

                    actual_amount=None,

                    schedule_order=(
                        source_schedule
                        .schedule_order
                    ),
                )
            )

            # =====================================
            # Schedule参考URL
            # =====================================

            source_reference_urls = (
                source_schedule
                .reference_urls
                .order_by(
                    "url_order"
                )
            )

            for source_url in (
                source_reference_urls
            ):

                ScheduleReferenceUrl.objects.create(
                    schedule=(
                        new_schedule
                    ),
                    title=(
                        source_url.title
                    ),
                    url=(
                        source_url.url
                    ),
                    url_order=(
                        source_url.url_order
                    ),
                )