from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import reverse
from django.views import View

from base.models import (
    Day,
    Schedule,
    DayExpense,
    DayReferenceUrl,
)

from base.models.day_models import DayLocation


# =========================================
# Day入れ替え
#
# Dayの日付・Day番号は固定したまま、
# 隣のDayと「内容」だけを入れ替える
#
# 入れ替えるもの
# ・タイトル
# ・メモ
# ・旅の記録
# ・写真
# ・予算
# ・実際の合計費用
# ・訪問先
# ・Day参考URL
# ・Schedule
# ・Day費用明細
#
# 入れ替えないもの
# ・date
# ・day_order
# =========================================

class DayMoveView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # Trip詳細へ戻るURL
    # =====================================

    def get_return_url(
        self,
        trip,
        day,
        request,
    ):

        url = reverse(
            "trip_detail",
            kwargs={
                "pk": trip.trip_id,
            },
        )

        # =====================================
        # Trip全体編集モードを維持
        # =====================================

        if (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        ):

            url += "?edit=1"

        # =====================================
        # 入れ替え後に
        # 移動した内容のDay位置へ戻る
        # =====================================

        url += (
            f"#day-{day.day_id}"
        )

        return url

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        day = get_object_or_404(
            Day,
            pk=self.kwargs["pk"],
            trip__user=request.user,
        )

        trip = day.trip

        direction = (
            request.POST.get(
                "direction"
            )
        )

        # =====================================
        # 入れ替え可能か確認
        #
        # 作成中
        # → 入れ替え可能
        #
        # 作成完了後
        # → Trip全体編集モードのみ可能
        # =====================================

        is_edit_mode = (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        )

        if (
            trip.status != "draft"
            and not is_edit_mode
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # 入れ替え先のDayを取得
        # =====================================

        if direction == "up":

            target_day = (
                Day.objects
                .filter(
                    trip=trip,
                    day_order__lt=(
                        day.day_order
                    ),
                )
                .order_by(
                    "-day_order"
                )
                .first()
            )

        elif direction == "down":

            target_day = (
                Day.objects
                .filter(
                    trip=trip,
                    day_order__gt=(
                        day.day_order
                    ),
                )
                .order_by(
                    "day_order"
                )
                .first()
            )

        else:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # 最初のDayで↑、
        # 最後のDayで↓を押した場合
        # =====================================

        if target_day is None:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # Dayの内容を入れ替える
        # =====================================

        with transaction.atomic():

            # =====================================
            # Day本体の値を退避
            # =====================================

            day_data = {
                "title": day.title,
                "memo": day.memo,
                "content": day.content,
                "media": (
                    day.media.name
                    if day.media
                    else ""
                ),
                "budget": day.budget,
                "actual_cost": (
                    day.actual_cost
                ),
            }

            target_day_data = {
                "title": (
                    target_day.title
                ),
                "memo": (
                    target_day.memo
                ),
                "content": (
                    target_day.content
                ),
                "media": (
                    target_day.media.name
                    if target_day.media
                    else ""
                ),
                "budget": (
                    target_day.budget
                ),
                "actual_cost": (
                    target_day.actual_cost
                ),
            }

            # =====================================
            # DayLocationを退避
            #
            # Locationだけでなく
            # 訪問順も一緒に保持する
            # =====================================

            day_location_data = list(
                day.day_locations
                .order_by(
                    "location_order"
                )
                .values(
                    "location_id",
                    "location_order",
                )
            )

            target_location_data = list(
                target_day.day_locations
                .order_by(
                    "location_order"
                )
                .values(
                    "location_id",
                    "location_order",
                )
            )

            # =====================================
            # Day参考URLを退避
            # =====================================

            day_reference_url_ids = list(
                day.reference_urls
                .values_list(
                    "pk",
                    flat=True,
                )
            )

            target_reference_url_ids = list(
                target_day.reference_urls
                .values_list(
                    "pk",
                    flat=True,
                )
            )

            # =====================================
            # Scheduleを退避
            # =====================================

            day_schedule_ids = list(
                day.schedules
                .values_list(
                    "pk",
                    flat=True,
                )
            )

            target_schedule_ids = list(
                target_day.schedules
                .values_list(
                    "pk",
                    flat=True,
                )
            )

            # =====================================
            # Day費用明細を退避
            # =====================================

            day_expense_ids = list(
                day.day_expenses
                .values_list(
                    "pk",
                    flat=True,
                )
            )

            target_expense_ids = list(
                target_day.day_expenses
                .values_list(
                    "pk",
                    flat=True,
                )
            )

            # =====================================
            # Day本体を交換
            #
            # date・day_orderは変更しない
            # =====================================

            day.title = (
                target_day_data[
                    "title"
                ]
            )

            day.memo = (
                target_day_data[
                    "memo"
                ]
            )

            day.content = (
                target_day_data[
                    "content"
                ]
            )

            day.media = (
                target_day_data[
                    "media"
                ]
            )

            day.budget = (
                target_day_data[
                    "budget"
                ]
            )

            day.actual_cost = (
                target_day_data[
                    "actual_cost"
                ]
            )

            day.save(
                update_fields=[
                    "title",
                    "memo",
                    "content",
                    "media",
                    "budget",
                    "actual_cost",
                ]
            )

            target_day.title = (
                day_data[
                    "title"
                ]
            )

            target_day.memo = (
                day_data[
                    "memo"
                ]
            )

            target_day.content = (
                day_data[
                    "content"
                ]
            )

            target_day.media = (
                day_data[
                    "media"
                ]
            )

            target_day.budget = (
                day_data[
                    "budget"
                ]
            )

            target_day.actual_cost = (
                day_data[
                    "actual_cost"
                ]
            )

            target_day.save(
                update_fields=[
                    "title",
                    "memo",
                    "content",
                    "media",
                    "budget",
                    "actual_cost",
                ]
            )

            # =====================================
            # DayLocationを交換
            #
            # throughモデルを使用しているため、
            # locations.set() は使わず
            # DayLocationを作り直す
            # =====================================

            day.day_locations.all().delete()

            target_day.day_locations.all().delete()

            DayLocation.objects.bulk_create(
                [
                    DayLocation(
                        day=day,
                        location_id=(
                            location_data[
                                "location_id"
                            ]
                        ),
                        location_order=(
                            location_data[
                                "location_order"
                            ]
                        ),
                    )
                    for location_data
                    in target_location_data
                ]
            )

            DayLocation.objects.bulk_create(
                [
                    DayLocation(
                        day=target_day,
                        location_id=(
                            location_data[
                                "location_id"
                            ]
                        ),
                        location_order=(
                            location_data[
                                "location_order"
                            ]
                        ),
                    )
                    for location_data
                    in day_location_data
                ]
            )

            # =====================================
            # Day参考URLを交換
            # =====================================

            if day_reference_url_ids:

                DayReferenceUrl.objects.filter(
                    pk__in=(
                        day_reference_url_ids
                    )
                ).update(
                    day=target_day
                )

            if target_reference_url_ids:

                DayReferenceUrl.objects.filter(
                    pk__in=(
                        target_reference_url_ids
                    )
                ).update(
                    day=day
                )

            # =====================================
            # Scheduleを交換
            # =====================================

            if day_schedule_ids:

                Schedule.objects.filter(
                    pk__in=(
                        day_schedule_ids
                    )
                ).update(
                    day=target_day
                )

            if target_schedule_ids:

                Schedule.objects.filter(
                    pk__in=(
                        target_schedule_ids
                    )
                ).update(
                    day=day
                )

            # =====================================
            # Day費用明細を交換
            # =====================================

            if day_expense_ids:

                DayExpense.objects.filter(
                    pk__in=(
                        day_expense_ids
                    )
                ).update(
                    day=target_day
                )

            if target_expense_ids:

                DayExpense.objects.filter(
                    pk__in=(
                        target_expense_ids
                    )
                ).update(
                    day=day
                )

        # =====================================
        # 元のDay内容が移動した先へ戻る
        # =====================================

        return redirect(
            self.get_return_url(
                trip,
                target_day,
                request,
            )
        )