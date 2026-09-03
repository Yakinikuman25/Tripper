from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import (
    F,
    Max,
    Q,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.utils import timezone
from django.views.generic import DetailView

from base.models import (
    Trip,
    TripExpense,
    TripSave,
)

from base.forms import (
    DayRecordForm,
    ScheduleRecordForm,
    TripExpenseForm,
    TripExpenseReferenceUrlFormSet,
)

from .trip_services import (
    sync_trip_status,
    get_trip_detail_url,
    get_trip_expense_reference_url_items,
    sync_trip_expense_reference_urls,
)


# =========================================
# Trip詳細
# =========================================

class TripDetailView(
    LoginRequiredMixin,
    DetailView,
):

    model = Trip

    template_name = (
        "pages/trip/trip_detail.html"
    )

    context_object_name = "trip"

    # =====================================
    # 表示可能なTrip
    #
    # ・自分のTrip
    # ・旅完了かつ公開中のTrip
    # =====================================

    def get_queryset(
        self,
    ):

        return (
            Trip.objects
            .filter(
                Q(
                    user=self.request.user
                )
                | Q(
                    status="completed",
                    is_public=True,
                )
            )
            .prefetch_related(
                "reference_urls",
                "trip_expenses__reference_urls",
                "days__reference_urls",
                "days__day_expenses",
                "days__schedules__reference_urls",
            )
            .distinct()
        )

    # =====================================
    # Trip取得
    #
    # 現在の日付に合わせて
    # ステータスも更新する
    # =====================================

    def get_object(
        self,
        queryset=None,
    ):

        trip = (
            super().get_object(
                queryset
            )
        )

        sync_trip_status(
            trip
        )

        return trip

    # =====================================
    # Trip所有者か
    # =====================================

    def is_owner(
        self,
    ):

        return (
            self.object.user
            == self.request.user
        )

    # =====================================
    # Trip全体編集モードか
    # =====================================

    def is_edit_mode(
        self,
    ):

        return (
            self.is_owner()
            and self.request.GET.get(
                "edit"
            )
            == "1"
        )

    # =====================================
    # Trip全体費用を
    # 新しく追加できるか
    #
    # 作成中・出発待ち・旅中
    # → 追加可能
    #
    # 旅完了
    # → Trip全体編集時のみ追加可能
    # =====================================

    def can_add_trip_expense(
        self,
    ):

        if not self.is_owner():

            return False

        if (
            self.object.status
            != "completed"
        ):

            return True

        return (
            self.is_edit_mode()
        )

    # =====================================
    # Trip全体費用1件を
    # 編集できるか
    # =====================================

    def can_edit_trip_expense(
        self,
        trip_expense,
    ):

        if not self.is_owner():

            return False

        if (
            self.object.status
            == "completed"
        ):

            return (
                self.is_edit_mode()
            )

        return True

    # =====================================
    # Trip全体費用を
    # 並び替えできるか
    # =====================================

    def can_move_trip_expense(
        self,
        trip_expense,
    ):

        return (
            self.can_edit_trip_expense(
                trip_expense
            )
        )

    # =====================================
    # 新規Trip全体費用用
    # 参考URL FormSet
    # =====================================

    def get_new_trip_expense_reference_url_formset(
        self,
        data=None,
    ):

        instance = TripExpense(
            trip=self.object
        )

        return (
            TripExpenseReferenceUrlFormSet(
                data,
                instance=instance,
                prefix=(
                    "expense_reference_urls_new"
                ),
            )
        )

    # =====================================
    # 既存Trip全体費用用
    # 参考URL FormSet
    # =====================================

    def get_trip_expense_reference_url_formset(
        self,
        trip_expense,
        data=None,
    ):

        return (
            TripExpenseReferenceUrlFormSet(
                data,
                instance=trip_expense,
                prefix=(
                    "expense_reference_urls_"
                    f"{trip_expense.trip_expense_id}"
                ),
            )
        )

    # =====================================
    # Trip全体費用参考URLの
    # management_formがPOSTされているか
    # =====================================

    def has_trip_expense_reference_url_formset_data(
        self,
        request,
        prefix,
    ):

        return (
            f"{prefix}-TOTAL_FORMS"
            in request.POST
        )

    # =====================================
    # Trip全体費用操作後の戻り先
    # =====================================

    def get_trip_expense_return_url(
        self,
        expense_id=None,
    ):

        url = (
            get_trip_detail_url(
                self.object,
                edit_mode=(
                    self.is_edit_mode()
                ),
            )
        )

        if (
            expense_id
            is not None
        ):

            url += (
                f"#trip-expense-"
                f"{expense_id}"
            )

        else:

            url += (
                "#trip-expenses"
            )

        return url

    # =====================================
    # Context
    # =====================================

    def get_context_data(
        self,
        **kwargs,
    ):

        context = (
            super().get_context_data(
                **kwargs
            )
        )

        today = (
            timezone.localdate()
        )

        context[
            "today"
        ] = today

        context[
            "is_owner"
        ] = (
            self.is_owner()
        )

        # =====================================
        # Trip保存
        # =====================================

        can_save_trip = (
            not self.is_owner()
            and self.object.status
            == "completed"
            and self.object.is_public
        )

        context[
            "can_save_trip"
        ] = (
            can_save_trip
        )

        if can_save_trip:

            is_saved = (
                TripSave.objects
                .filter(
                    user=self.request.user,
                    trip=self.object,
                )
                .exists()
            )

        else:

            is_saved = False

        context[
            "is_saved"
        ] = (
            is_saved
        )

        # =====================================
        # Trip再利用
        # =====================================

        if self.is_owner():

            can_reuse_trip = (
                self.object.status
                == "completed"
            )

        else:

            can_reuse_trip = (
                self.object.status
                == "completed"
                and self.object.is_public
                and is_saved
            )

        context[
            "can_reuse_trip"
        ] = (
            can_reuse_trip
        )

        # =====================================
        # Trip全体編集モード
        # =====================================

        edit_mode = (
            self.is_edit_mode()
        )

        context[
            "edit_mode"
        ] = edit_mode

        # =====================================
        # 作成中では
        # Day実費を表示しない
        # =====================================

        context[
            "show_day_actual"
        ] = (
            self.object.status
            != "draft"
        )

        # =====================================
        # Trip全体費用
        # =====================================

        trip_expenses = list(
            self.object
            .trip_expenses
            .order_by(
                "expense_order",
                "trip_expense_id",
            )
        )

        editing_expense_id = (
            kwargs.get(
                "editing_expense_id"
            )
        )

        editing_reference_url_formset = (
            kwargs.get(
                "editing_reference_url_formset"
            )
        )

        editing_expense_form = (
            kwargs.get(
                "editing_expense_form"
            )
        )

        # =====================================
        # Trip全体費用1件ごとの
        # 編集可否・参考URL FormSet
        # =====================================

        for trip_expense in (
            trip_expenses
        ):

            trip_expense.can_edit = (
                self.can_edit_trip_expense(
                    trip_expense
                )
            )

            trip_expense.can_move = (
                self.can_move_trip_expense(
                    trip_expense
                )
            )

            trip_expense.reference_url_formset = (
                None
            )

            trip_expense.edit_form = (
                None
            )

            if trip_expense.can_edit:

                if (
                    editing_expense_id
                    == trip_expense.trip_expense_id
                    and (
                        editing_reference_url_formset
                        is not None
                    )
                ):

                    trip_expense.reference_url_formset = (
                        editing_reference_url_formset
                    )

                else:

                    trip_expense.reference_url_formset = (
                        self
                        .get_trip_expense_reference_url_formset(
                            trip_expense
                        )
                    )

                if (
                    editing_expense_id
                    == trip_expense.trip_expense_id
                    and (
                        editing_expense_form
                        is not None
                    )
                ):

                    trip_expense.edit_form = (
                        editing_expense_form
                    )

                else:

                    trip_expense.edit_form = (
                        TripExpenseForm(
                            instance=(
                                trip_expense
                            )
                        )
                    )

        context[
            "trip_expenses"
        ] = trip_expenses

        # =====================================
        # 新規追加フォームを
        # 表示できるか
        # =====================================

        context[
            "can_add_trip_expense"
        ] = (
            self.can_add_trip_expense()
        )

        # =====================================
        # 既存HTMLとの互換用
        # =====================================

        context[
            "can_edit_trip_expenses"
        ] = (
            self.can_add_trip_expense()
        )

        if (
            "trip_expense_form"
            not in context
        ):

            context[
                "trip_expense_form"
            ] = TripExpenseForm()

        # =====================================
        # 新規Trip全体費用用
        # 参考URL FormSet
        # =====================================

        if (
            "trip_expense_reference_url_formset"
            not in context
        ):

            context[
                "trip_expense_reference_url_formset"
            ] = (
                self
                .get_new_trip_expense_reference_url_formset()
            )

        # =====================================
        # 旅を完了できるか
        # =====================================

        context[
            "can_complete_trip"
        ] = (
            self.object.status
            == "traveling"
            and today
            >= self.object.end_date
        )

        # =====================================
        # ハッシュタグ
        # =====================================

        context[
            "trip_hashtags"
        ] = (
            self.object
            .trip_hashtags
            .select_related(
                "hashtag"
            )
            .all()
        )

        # =====================================
        # Trip参考URL
        # =====================================

        context[
            "trip_reference_urls"
        ] = (
            self.object
            .reference_urls
            .order_by(
                "url_order"
            )
        )

        # =====================================
        # Trip全体の訪問先
        # =====================================

        locations_by_country = {}

        for location in (
            self.object
            .locations
            .all()
        ):

            if (
                location.country
                not in locations_by_country
            ):

                locations_by_country[
                    location.country
                ] = []

            if (
                location.region
                not in locations_by_country[
                    location.country
                ]
            ):

                locations_by_country[
                    location.country
                ].append(
                    location.region
                )

        context[
            "locations_by_country"
        ] = (
            locations_by_country
        )

        # =====================================
        # Trip全体の訪問ルート
        # =====================================

        trip_route = []

        route_days = (
            self.object
            .days
            .order_by(
                "day_order"
            )
        )

        previous_location_id = (
            None
        )

        for route_day in (
            route_days
        ):

            route_day_locations = (
                route_day
                .day_locations
                .select_related(
                    "location"
                )
                .order_by(
                    "location_order"
                )
            )

            for day_location in (
                route_day_locations
            ):

                location = (
                    day_location.location
                )

                if (
                    previous_location_id
                    == location.location_id
                ):

                    continue

                trip_route.append(
                    {
                        "location": location,
                        "date": route_day.date,
                        "day_order": (
                            route_day.day_order
                        ),
                        "location_order": (
                            day_location.location_order
                        ),
                    }
                )

                previous_location_id = (
                    location.location_id
                )

        context[
            "trip_route"
        ] = trip_route

        # =====================================
        # Trip全体費用
        #
        # TripExpenseのみの予定・実際支払額
        # =====================================

        trip_planned_total = 0

        has_trip_planned_cost = (
            False
        )

        trip_actual_total = 0

        has_trip_actual_cost = (
            False
        )

        for expense in (
            trip_expenses
        ):

            if (
                expense.planned_amount
                is not None
            ):

                trip_planned_total += (
                    expense.planned_amount
                )

                has_trip_planned_cost = (
                    True
                )

            if (
                expense.actual_amount
                is not None
            ):

                trip_actual_total += (
                    expense.actual_amount
                )

                has_trip_actual_cost = (
                    True
                )

        # =====================================
        # Dayごとの処理
        # =====================================

        days = (
            self.object
            .days
            .all()
        )

        # =====================================
        # Day予定内訳
        # =====================================

        day_budget_total = 0

        day_planned_amount_total = 0

        schedule_planned_total = 0

        day_planned_total = 0

        has_day_budget = (
            False
        )

        has_day_planned_amount = (
            False
        )

        has_schedule_planned_cost = (
            False
        )

        has_day_planned_cost = (
            False
        )

        # =====================================
        # Day実費内訳
        # =====================================

        day_free_actual_total = 0

        day_actual_amount_total = 0

        schedule_actual_total = 0

        day_actual_total = 0

        has_day_free_actual = (
            False
        )

        has_day_actual_amount = (
            False
        )

        has_schedule_actual_cost = (
            False
        )

        has_day_actual_cost = (
            False
        )

        for day in days:

            # =====================================
            # このDayの予定合計
            # =====================================

            current_day_planned_total = 0

            current_day_has_planned_cost = (
                False
            )

            # =====================================
            # 自由費予算
            # =====================================

            if (
                day.budget
                is not None
            ):

                current_day_planned_total += (
                    day.budget
                )

                day_budget_total += (
                    day.budget
                )

                has_day_budget = (
                    True
                )

                current_day_has_planned_cost = (
                    True
                )

            # =====================================
            # Day予定金額
            # =====================================

            if (
                day.planned_amount
                is not None
            ):

                current_day_planned_total += (
                    day.planned_amount
                )

                day_planned_amount_total += (
                    day.planned_amount
                )

                has_day_planned_amount = (
                    True
                )

                current_day_has_planned_cost = (
                    True
                )

            # =====================================
            # Day費用明細
            # =====================================

            day_expense_total = 0

            has_day_expense = (
                False
            )

            for expense in (
                day.day_expenses.all()
            ):

                if (
                    expense.amount
                    is not None
                ):

                    day_expense_total += (
                        expense.amount
                    )

                    has_day_expense = (
                        True
                    )

            if has_day_expense:

                day.day_expense_total = (
                    day_expense_total
                )

            else:

                day.day_expense_total = (
                    None
                )

            day.has_day_expense = (
                has_day_expense
            )

            # =====================================
            # 自由実費
            #
            # 手入力を優先
            #
            # 手入力なしの場合だけ
            # 費用明細合計を採用
            # =====================================

            if (
                day.actual_cost
                is not None
            ):

                day.adopted_actual_cost = (
                    day.actual_cost
                )

                day.has_actual_cost = (
                    True
                )

            elif has_day_expense:

                day.adopted_actual_cost = (
                    day_expense_total
                )

                day.has_actual_cost = (
                    True
                )

            else:

                day.adopted_actual_cost = (
                    None
                )

                day.has_actual_cost = (
                    False
                )

            # =====================================
            # Schedule
            # =====================================

            schedules_sorted = list(
                day.schedules
                .order_by(
                    F(
                        "start_time"
                    ).asc(
                        nulls_last=True
                    ),
                    "schedule_order",
                )
            )

            day.schedules_sorted = (
                schedules_sorted
            )

            # =====================================
            # このDayのSchedule集計
            # =====================================

            current_schedule_planned_total = 0

            current_schedule_actual_total = 0

            # =====================================
            # Day最低必要額の計算用
            #
            # 画面には直接表示しない
            # =====================================

            current_unpaid_schedule_total = 0

            current_has_schedule_planned = (
                False
            )

            current_has_schedule_actual = (
                False
            )

            for schedule in (
                schedules_sorted
            ):

                # =====================================
                # Schedule予定金額
                # =====================================

                if (
                    schedule.planned_amount
                    is not None
                ):

                    current_schedule_planned_total += (
                        schedule.planned_amount
                    )

                    schedule_planned_total += (
                        schedule.planned_amount
                    )

                    has_schedule_planned_cost = (
                        True
                    )

                    current_has_schedule_planned = (
                        True
                    )

                    current_day_has_planned_cost = (
                        True
                    )

                    # =================================
                    # 実際支払額が未入力の場合だけ
                    # Day最低必要額へ加える
                    # =================================

                    if (
                        schedule.actual_amount
                        is None
                    ):

                        current_unpaid_schedule_total += (
                            schedule.planned_amount
                        )

                # =====================================
                # Schedule実際支払額
                # =====================================

                if (
                    schedule.actual_amount
                    is not None
                ):

                    current_schedule_actual_total += (
                        schedule.actual_amount
                    )

                    schedule_actual_total += (
                        schedule.actual_amount
                    )

                    has_schedule_actual_cost = (
                        True
                    )

                    current_has_schedule_actual = (
                        True
                    )

            # =====================================
            # Schedule予定金額を
            # Day予定合計へ加える
            # =====================================

            if current_has_schedule_planned:

                current_day_planned_total += (
                    current_schedule_planned_total
                )

            # =====================================
            # Schedule予定合計
            # =====================================

            if current_has_schedule_planned:

                day.schedule_planned_total = (
                    current_schedule_planned_total
                )

            else:

                day.schedule_planned_total = (
                    None
                )

            # =====================================
            # Schedule実際支払額合計
            # =====================================

            if current_has_schedule_actual:

                day.schedule_actual_total = (
                    current_schedule_actual_total
                )

            else:

                day.schedule_actual_total = (
                    None
                )

            # =====================================
            # Day最低必要額
            #
            # 自由費予算は含めない
            #
            # =
            # 未払いDay予定金額
            # +
            # 未払いSchedule予定金額
            # =====================================

            current_day_minimum_remaining_amount = 0

            current_day_has_fixed_planned_cost = (
                day.planned_amount
                is not None
                or current_has_schedule_planned
            )

            # =====================================
            # 未払いDay予定金額
            # =====================================

            if (
                day.planned_amount
                is not None
                and day.actual_amount
                is None
            ):

                current_day_minimum_remaining_amount += (
                    day.planned_amount
                )

            # =====================================
            # 未払いSchedule予定金額
            # =====================================

            current_day_minimum_remaining_amount += (
                current_unpaid_schedule_total
            )

            # =====================================
            # Day最低必要額
            #
            # 予定金額が1件でもある場合
            # 全て支払済みなら0円
            #
            # 予定金額自体がない場合はNone
            # =====================================

            if current_day_has_fixed_planned_cost:

                day.minimum_remaining_amount = (
                    current_day_minimum_remaining_amount
                )

            else:

                day.minimum_remaining_amount = (
                    None
                )

            day.has_fixed_planned_cost = (
                current_day_has_fixed_planned_cost
            )

            # =====================================
            # 当日予算目安
            #
            # =
            # Day最低必要額
            # +
            # 自由費予算
            #
            # 自由費予算は
            # Day最低必要額には含めない
            # =====================================

            if (
                day.minimum_remaining_amount
                is not None
                or day.budget
                is not None
            ):

                day.daily_budget_guide = (
                    (
                        day.minimum_remaining_amount
                        or 0
                    )
                    + (
                        day.budget
                        or 0
                    )
                )

                day.has_daily_budget_guide = (
                    True
                )

            else:

                day.daily_budget_guide = (
                    None
                )

                day.has_daily_budget_guide = (
                    False
                )

            # =====================================
            # Day予定合計
            # =====================================

            if current_day_has_planned_cost:

                day.planned_cost_total = (
                    current_day_planned_total
                )

                day.has_planned_cost = (
                    True
                )

                day_planned_total += (
                    current_day_planned_total
                )

                has_day_planned_cost = (
                    True
                )

            else:

                day.planned_cost_total = (
                    None
                )

                day.has_planned_cost = (
                    False
                )

            # =====================================
            # このDayの実際合計
            # =====================================

            current_day_actual_total = 0

            current_day_has_actual_cost = (
                False
            )

            # =====================================
            # 自由実費
            # =====================================

            if day.has_actual_cost:

                current_day_actual_total += (
                    day.adopted_actual_cost
                )

                day_free_actual_total += (
                    day.adopted_actual_cost
                )

                has_day_free_actual = (
                    True
                )

                current_day_has_actual_cost = (
                    True
                )

            # =====================================
            # Day実際支払額
            # =====================================

            if (
                day.actual_amount
                is not None
            ):

                current_day_actual_total += (
                    day.actual_amount
                )

                day_actual_amount_total += (
                    day.actual_amount
                )

                has_day_actual_amount = (
                    True
                )

                current_day_has_actual_cost = (
                    True
                )

            # =====================================
            # Schedule実際支払額
            # =====================================

            if current_has_schedule_actual:

                current_day_actual_total += (
                    current_schedule_actual_total
                )

                current_day_has_actual_cost = (
                    True
                )

            # =====================================
            # Day実際合計
            # =====================================

            if current_day_has_actual_cost:

                day.actual_cost_total = (
                    current_day_actual_total
                )

                day.has_actual_total = (
                    True
                )

                day_actual_total += (
                    current_day_actual_total
                )

                has_day_actual_cost = (
                    True
                )

            else:

                day.actual_cost_total = (
                    None
                )

                day.has_actual_total = (
                    False
                )

            # =====================================
            # Day訪問先
            # =====================================

            day_locations = {}

            ordered_day_locations = (
                day.day_locations
                .select_related(
                    "location"
                )
                .order_by(
                    "location_order"
                )
            )

            for day_location in (
                ordered_day_locations
            ):

                location = (
                    day_location.location
                )

                if (
                    location.country
                    not in day_locations
                ):

                    day_locations[
                        location.country
                    ] = []

                if (
                    location.region
                    not in day_locations[
                        location.country
                    ]
                ):

                    day_locations[
                        location.country
                    ].append(
                        location.region
                    )

            day.location_groups = (
                day_locations
            )

            # =====================================
            # このDayの旅の記録を
            # 入力・編集できるか
            # =====================================

            day.can_edit_record = (
                False
            )

            if (
                self.object.status
                == "traveling"
            ):

                if (
                    day.date
                    <= today
                ):

                    day.can_edit_record = (
                        True
                    )

            elif (
                self.object.status
                == "completed"
            ):

                if edit_mode:

                    day.can_edit_record = (
                        True
                    )

            # =====================================
            # Schedule実際支払額入力フォーム
            # =====================================

            day.schedule_record_items = []

            if day.can_edit_record:

                day.record_form = (
                    DayRecordForm(
                        instance=day,
                        prefix=(
                            f"day_{day.day_id}"
                        ),
                    )
                )

                for schedule in (
                    schedules_sorted
                ):

                    if (
                        schedule.planned_amount
                        is None
                    ):

                        continue

                    if (
                        schedule.actual_amount
                        is not None
                    ):

                        continue

                    schedule_record_form = (
                        ScheduleRecordForm(
                            instance=schedule,
                            prefix=(
                                f"schedule_"
                                f"{schedule.schedule_id}"
                            ),
                        )
                    )

                    day.schedule_record_items.append(
                        {
                            "schedule": schedule,
                            "form": (
                                schedule_record_form
                            ),
                        }
                    )

        context[
            "days"
        ] = days

        # =====================================
        # Trip予定合計
        # =====================================

        has_planned_cost = (
            has_trip_planned_cost
            or has_day_planned_cost
        )

        if has_planned_cost:

            planned_total = (
                trip_planned_total
                + day_planned_total
            )

        else:

            planned_total = (
                None
            )

        # =====================================
        # TripExpense予定合計
        # =====================================

        context[
            "trip_planned_cost_total"
        ] = (
            trip_planned_total
            if has_trip_planned_cost
            else None
        )

        context[
            "has_trip_planned_cost"
        ] = (
            has_trip_planned_cost
        )

        # =====================================
        # 自由費予算合計
        # =====================================

        context[
            "day_budget_total"
        ] = (
            day_budget_total
            if has_day_budget
            else None
        )

        context[
            "has_day_budget"
        ] = (
            has_day_budget
        )

        # =====================================
        # Day予定金額合計
        # =====================================

        context[
            "day_planned_amount_total"
        ] = (
            day_planned_amount_total
            if has_day_planned_amount
            else None
        )

        context[
            "has_day_planned_amount"
        ] = (
            has_day_planned_amount
        )

        # =====================================
        # Schedule予定金額合計
        # =====================================

        context[
            "schedule_planned_total"
        ] = (
            schedule_planned_total
            if has_schedule_planned_cost
            else None
        )

        context[
            "has_schedule_planned_cost"
        ] = (
            has_schedule_planned_cost
        )

        # =====================================
        # 全Day予定合計
        # =====================================

        context[
            "day_planned_cost_total"
        ] = (
            day_planned_total
            if has_day_planned_cost
            else None
        )

        context[
            "has_day_planned_cost"
        ] = (
            has_day_planned_cost
        )

        # =====================================
        # Trip全体予定合計
        # =====================================

        context[
            "planned_total"
        ] = planned_total

        context[
            "has_planned_cost"
        ] = (
            has_planned_cost
        )

        # =====================================
        # Trip実際支払額合計
        # =====================================

        has_reference_actual_cost = (
            has_trip_actual_cost
            or has_day_actual_cost
        )

        if has_reference_actual_cost:

            reference_actual_total = (
                trip_actual_total
                + day_actual_total
            )

        else:

            reference_actual_total = (
                None
            )

        # =====================================
        # TripExpense実際支払額合計
        # =====================================

        context[
            "trip_actual_cost_total"
        ] = (
            trip_actual_total
            if has_trip_actual_cost
            else None
        )

        context[
            "has_trip_actual_cost"
        ] = (
            has_trip_actual_cost
        )

        # =====================================
        # 自由実費合計
        # =====================================

        context[
            "day_free_actual_total"
        ] = (
            day_free_actual_total
            if has_day_free_actual
            else None
        )

        context[
            "has_day_free_actual"
        ] = (
            has_day_free_actual
        )

        # =====================================
        # Day実際支払額合計
        # =====================================

        context[
            "day_actual_amount_total"
        ] = (
            day_actual_amount_total
            if has_day_actual_amount
            else None
        )

        context[
            "has_day_actual_amount"
        ] = (
            has_day_actual_amount
        )

        # =====================================
        # Schedule実際支払額合計
        # =====================================

        context[
            "schedule_actual_total"
        ] = (
            schedule_actual_total
            if has_schedule_actual_cost
            else None
        )

        context[
            "has_schedule_actual_cost"
        ] = (
            has_schedule_actual_cost
        )

        # =====================================
        # 全Day実際合計
        # =====================================

        context[
            "day_actual_cost_total"
        ] = (
            day_actual_total
            if has_day_actual_cost
            else None
        )

        context[
            "has_day_actual_cost"
        ] = (
            has_day_actual_cost
        )

        context[
            "day_actual_total"
        ] = (
            day_actual_total
            if has_day_actual_cost
            else None
        )

        # =====================================
        # Trip全体の集計実費
        # =====================================

        context[
            "reference_actual_total"
        ] = (
            reference_actual_total
        )

        context[
            "has_reference_actual_cost"
        ] = (
            has_reference_actual_cost
        )

        # =====================================
        # Trip最終実費
        # =====================================

        if (
            self.object.total_cost
            is not None
        ):

            final_actual_total = (
                self.object.total_cost
            )

        elif has_reference_actual_cost:

            final_actual_total = (
                reference_actual_total
            )

        else:

            final_actual_total = (
                None
            )

        has_final_actual_cost = (
            final_actual_total
            is not None
        )

        context[
            "is_manual_total_cost"
        ] = (
            self.object.total_cost
            is not None
        )

        context[
            "final_actual_total"
        ] = (
            final_actual_total
        )

        context[
            "has_final_actual_cost"
        ] = (
            has_final_actual_cost
        )

        # =====================================
        # 予定と実費の差額
        # =====================================

        if (
            has_planned_cost
            and has_final_actual_cost
        ):

            context[
                "cost_difference"
            ] = (
                final_actual_total
                - planned_total
            )

            context[
                "has_cost_difference"
            ] = True

        else:

            context[
                "cost_difference"
            ] = None

            context[
                "has_cost_difference"
            ] = False

        # =====================================
        # 今後最低必要額
        #
        # 自由費予算・自由実費は含めない
        #
        # =
        # 未払いTrip全体費用
        # +
        # 各Day最低必要額
        # =====================================

        has_fixed_planned_cost = (
            has_trip_planned_cost
            or has_day_planned_amount
            or has_schedule_planned_cost
        )

        # =====================================
        # 固定費予定合計
        # =====================================

        if has_fixed_planned_cost:

            fixed_planned_total = (
                trip_planned_total
                + day_planned_amount_total
                + schedule_planned_total
            )

        else:

            fixed_planned_total = (
                None
            )

        # =====================================
        # 固定費実際支払額合計
        # =====================================

        has_fixed_actual_cost = (
            has_trip_actual_cost
            or has_day_actual_amount
            or has_schedule_actual_cost
        )

        if has_fixed_actual_cost:

            fixed_actual_total = (
                trip_actual_total
                + day_actual_amount_total
                + schedule_actual_total
            )

        else:

            fixed_actual_total = 0

        # =====================================
        # Trip全体の今後最低必要額
        # =====================================

        minimum_remaining_amount = 0

        # =====================================
        # 未払いTrip全体費用
        # =====================================

        for expense in (
            trip_expenses
        ):

            if (
                expense.planned_amount
                is not None
                and expense.actual_amount
                is None
            ):

                minimum_remaining_amount += (
                    expense.planned_amount
                )

        # =====================================
        # 各Day最低必要額
        # =====================================

        for day in (
            days
        ):

            if (
                day.minimum_remaining_amount
                is not None
            ):

                minimum_remaining_amount += (
                    day.minimum_remaining_amount
                )

        # =====================================
        # 固定費予定が全くない場合
        # =====================================

        if not has_fixed_planned_cost:

            minimum_remaining_amount = (
                None
            )

        # =====================================
        # 固定費予定合計
        # =====================================

        context[
            "fixed_planned_total"
        ] = (
            fixed_planned_total
        )

        context[
            "has_fixed_planned_cost"
        ] = (
            has_fixed_planned_cost
        )

        # =====================================
        # 固定費実際支払額合計
        # =====================================

        context[
            "fixed_actual_total"
        ] = (
            fixed_actual_total
        )

        context[
            "has_fixed_actual_cost"
        ] = (
            has_fixed_actual_cost
        )

        # =====================================
        # 今後最低必要額
        # =====================================

        context[
            "minimum_remaining_amount"
        ] = (
            minimum_remaining_amount
        )

        return context

    # =====================================
    # Trip詳細から
    # Trip全体費用を操作
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):

        self.object = (
            self.get_object()
        )

        if not self.is_owner():

            return redirect(
                get_trip_detail_url(
                    self.object
                )
            )

        action = (
            request.POST.get(
                "action"
            )
        )

        if (
            action
            == "add_trip_expense"
        ):

            if not (
                self.can_add_trip_expense()
            ):

                return redirect(
                    self.get_trip_expense_return_url()
                )

            return (
                self.add_trip_expense(
                    request
                )
            )

        if (
            action
            == "update_trip_expense"
        ):

            trip_expense = (
                get_object_or_404(
                    TripExpense,
                    trip_expense_id=(
                        request.POST.get(
                            "expense_id"
                        )
                    ),
                    trip=self.object,
                )
            )

            if not (
                self.can_edit_trip_expense(
                    trip_expense
                )
            ):

                return redirect(
                    self.get_trip_expense_return_url(
                        expense_id=(
                            trip_expense
                            .trip_expense_id
                        ),
                    )
                )

            return (
                self.update_trip_expense(
                    request,
                    trip_expense,
                )
            )

        if (
            action
            == "move_trip_expense"
        ):

            trip_expense = (
                get_object_or_404(
                    TripExpense,
                    trip_expense_id=(
                        request.POST.get(
                            "expense_id"
                        )
                    ),
                    trip=self.object,
                )
            )

            if not (
                self.can_move_trip_expense(
                    trip_expense
                )
            ):

                return redirect(
                    self.get_trip_expense_return_url(
                        expense_id=(
                            trip_expense
                            .trip_expense_id
                        ),
                    )
                )

            direction = (
                request.POST.get(
                    "direction",
                    "",
                )
            )

            return (
                self.move_trip_expense(
                    trip_expense,
                    direction,
                )
            )

        if (
            action
            == "delete_trip_expense"
        ):

            trip_expense = (
                get_object_or_404(
                    TripExpense,
                    trip_expense_id=(
                        request.POST.get(
                            "expense_id"
                        )
                    ),
                    trip=self.object,
                )
            )

            if not (
                self.can_edit_trip_expense(
                    trip_expense
                )
            ):

                return redirect(
                    self.get_trip_expense_return_url(
                        expense_id=(
                            trip_expense
                            .trip_expense_id
                        ),
                    )
                )

            return (
                self.delete_trip_expense(
                    trip_expense
                )
            )

        return redirect(
            self.get_trip_expense_return_url()
        )

    # =====================================
    # Trip全体費用追加
    # =====================================

    def add_trip_expense(
        self,
        request,
    ):

        expense_form = (
            TripExpenseForm(
                request.POST
            )
        )

        expense_name = (
            request.POST.get(
                "name",
                "",
            )
            .strip()
        )

        if not expense_name:

            expense_form.add_error(
                "name",
                "費用名を入力してください。",
            )

        reference_url_prefix = (
            "expense_reference_urls_new"
        )

        has_reference_url_data = (
            self
            .has_trip_expense_reference_url_formset_data(
                request,
                reference_url_prefix,
            )
        )

        if has_reference_url_data:

            reference_url_formset = (
                self
                .get_new_trip_expense_reference_url_formset(
                    data=request.POST
                )
            )

            reference_urls_valid = (
                reference_url_formset
                .is_valid()
            )

        else:

            reference_url_formset = (
                self
                .get_new_trip_expense_reference_url_formset()
            )

            reference_urls_valid = (
                True
            )

        if (
            expense_form.is_valid()
            and reference_urls_valid
        ):

            with transaction.atomic():

                trip_expense = (
                    expense_form.save(
                        commit=False
                    )
                )

                trip_expense.name = (
                    expense_name
                )

                trip_expense.trip = (
                    self.object
                )

                max_order = (
                    self.object
                    .trip_expenses
                    .aggregate(
                        Max(
                            "expense_order"
                        )
                    )[
                        "expense_order__max"
                    ]
                )

                if (
                    max_order
                    is None
                ):

                    max_order = 0

                trip_expense.expense_order = (
                    max_order + 1
                )

                trip_expense.save()

                if has_reference_url_data:

                    reference_url_items = (
                        get_trip_expense_reference_url_items(
                            reference_url_formset
                        )
                    )

                    sync_trip_expense_reference_urls(
                        trip_expense,
                        reference_url_items,
                    )

            return redirect(
                self.get_trip_expense_return_url(
                    expense_id=(
                        trip_expense
                        .trip_expense_id
                    ),
                )
            )

        context = (
            self.get_context_data(
                trip_expense_form=(
                    expense_form
                ),
                trip_expense_reference_url_formset=(
                    reference_url_formset
                ),
            )
        )

        return (
            self.render_to_response(
                context
            )
        )

    # =====================================
    # Trip全体費用編集
    # =====================================

    def update_trip_expense(
        self,
        request,
        trip_expense,
    ):

        expense_form = (
            TripExpenseForm(
                request.POST,
                instance=(
                    trip_expense
                ),
            )
        )

        expense_name = (
            request.POST.get(
                "name",
                "",
            )
            .strip()
        )

        if not expense_name:

            expense_form.add_error(
                "name",
                "費用名を入力してください。",
            )

        reference_url_prefix = (
            "expense_reference_urls_"
            f"{trip_expense.trip_expense_id}"
        )

        has_reference_url_data = (
            self
            .has_trip_expense_reference_url_formset_data(
                request,
                reference_url_prefix,
            )
        )

        if has_reference_url_data:

            reference_url_formset = (
                self
                .get_trip_expense_reference_url_formset(
                    trip_expense,
                    data=request.POST,
                )
            )

            reference_urls_valid = (
                reference_url_formset
                .is_valid()
            )

        else:

            reference_url_formset = (
                self
                .get_trip_expense_reference_url_formset(
                    trip_expense
                )
            )

            reference_urls_valid = (
                True
            )

        if (
            expense_form.is_valid()
            and reference_urls_valid
        ):

            with transaction.atomic():

                updated_expense = (
                    expense_form.save(
                        commit=False
                    )
                )

                updated_expense.name = (
                    expense_name
                )

                updated_expense.save()

                if has_reference_url_data:

                    reference_url_items = (
                        get_trip_expense_reference_url_items(
                            reference_url_formset
                        )
                    )

                    sync_trip_expense_reference_urls(
                        updated_expense,
                        reference_url_items,
                    )

            return redirect(
                self.get_trip_expense_return_url(
                    expense_id=(
                        trip_expense
                        .trip_expense_id
                    ),
                )
            )

        context = (
            self.get_context_data(
                editing_expense_id=(
                    trip_expense
                    .trip_expense_id
                ),
                editing_expense_form=(
                    expense_form
                ),
                editing_reference_url_formset=(
                    reference_url_formset
                ),
            )
        )

        return (
            self.render_to_response(
                context
            )
        )

    # =====================================
    # Trip全体費用並び替え
    # =====================================

    def move_trip_expense(
        self,
        trip_expense,
        direction,
    ):

        if direction not in (
            "up",
            "down",
        ):

            return redirect(
                self.get_trip_expense_return_url(
                    expense_id=(
                        trip_expense
                        .trip_expense_id
                    ),
                )
            )

        ordered_expenses = list(
            self.object
            .trip_expenses
            .order_by(
                "expense_order",
                "trip_expense_id",
            )
        )

        current_index = None

        for index, expense in enumerate(
            ordered_expenses
        ):

            if (
                expense.trip_expense_id
                == trip_expense.trip_expense_id
            ):

                current_index = (
                    index
                )

                break

        if (
            current_index
            is None
        ):

            return redirect(
                self.get_trip_expense_return_url()
            )

        if (
            direction
            == "up"
        ):

            target_index = (
                current_index - 1
            )

        else:

            target_index = (
                current_index + 1
            )

        if (
            target_index < 0
            or target_index
            >= len(
                ordered_expenses
            )
        ):

            return redirect(
                self.get_trip_expense_return_url(
                    expense_id=(
                        trip_expense
                        .trip_expense_id
                    ),
                )
            )

        target_expense = (
            ordered_expenses[
                target_index
            ]
        )

        current_order = (
            trip_expense
            .expense_order
        )

        target_order = (
            target_expense
            .expense_order
        )

        if (
            current_order
            == target_order
        ):

            with transaction.atomic():

                for order, expense in enumerate(
                    ordered_expenses,
                    start=1,
                ):

                    expense.expense_order = (
                        order
                    )

                    expense.save(
                        update_fields=[
                            "expense_order"
                        ]
                    )

            trip_expense.refresh_from_db()

            ordered_expenses = list(
                self.object
                .trip_expenses
                .order_by(
                    "expense_order",
                    "trip_expense_id",
                )
            )

            current_index = next(
                index
                for index, expense
                in enumerate(
                    ordered_expenses
                )
                if (
                    expense.trip_expense_id
                    == trip_expense.trip_expense_id
                )
            )

            if (
                direction
                == "up"
            ):

                target_index = (
                    current_index - 1
                )

            else:

                target_index = (
                    current_index + 1
                )

            if (
                target_index < 0
                or target_index
                >= len(
                    ordered_expenses
                )
            ):

                return redirect(
                    self.get_trip_expense_return_url(
                        expense_id=(
                            trip_expense
                            .trip_expense_id
                        ),
                    )
                )

            target_expense = (
                ordered_expenses[
                    target_index
                ]
            )

            current_order = (
                trip_expense
                .expense_order
            )

            target_order = (
                target_expense
                .expense_order
            )

        max_order = (
            self.object
            .trip_expenses
            .aggregate(
                Max(
                    "expense_order"
                )
            )[
                "expense_order__max"
            ]
            or 0
        )

        temporary_order = (
            max_order + 1
        )

        with transaction.atomic():

            trip_expense.expense_order = (
                temporary_order
            )

            trip_expense.save(
                update_fields=[
                    "expense_order"
                ]
            )

            target_expense.expense_order = (
                current_order
            )

            target_expense.save(
                update_fields=[
                    "expense_order"
                ]
            )

            trip_expense.expense_order = (
                target_order
            )

            trip_expense.save(
                update_fields=[
                    "expense_order"
                ]
            )

        return redirect(
            self.get_trip_expense_return_url(
                expense_id=(
                    trip_expense
                    .trip_expense_id
                ),
            )
        )

    # =====================================
    # Trip全体費用削除
    # =====================================

    def delete_trip_expense(
        self,
        trip_expense,
    ):

        with transaction.atomic():

            trip_expense.delete()

            remaining_expenses = (
                self.object
                .trip_expenses
                .order_by(
                    "expense_order",
                    "trip_expense_id",
                )
            )

            for expense_order, expense in enumerate(
                remaining_expenses,
                start=1,
            ):

                if (
                    expense.expense_order
                    != expense_order
                ):

                    expense.expense_order = (
                        expense_order
                    )

                    expense.save(
                        update_fields=[
                            "expense_order"
                        ]
                    )

        return redirect(
            self.get_trip_expense_return_url()
        )