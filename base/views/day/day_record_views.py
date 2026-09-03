from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import reverse
from django.utils import timezone
from django.views import View

from base.models import (
    Day,
    DayExpense,
)

from base.forms import (
    DayRecordForm,
    DayExpenseFormSet,
    ScheduleRecordForm,
)


# =========================================
# Day旅の記録
#
# ・写真
# ・感想
# ・自由実費
# ・Day実際支払額
# ・Day費用明細
# ・Schedule実際支払額
#
# Schedule実際支払額は、
#
# ・予定金額が登録されている
# ・実際支払額が未入力
#
# のScheduleだけを入力対象とする
# =========================================

class DayRecordUpdateView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # このDayに旅の記録を
    # 入力・編集できるか
    # =====================================

    def can_edit_record(
        self,
        request,
        day,
        trip,
    ):

        today = timezone.localdate()

        # =====================================
        # 作成中・出発待ち
        # → 旅の記録は入力不可
        # =====================================

        if trip.status in (
            "draft",
            "planned",
        ):

            return False

        # =====================================
        # 旅中
        #
        # 今日・過去のDay
        # → 通常画面から入力可能
        #
        # 未来のDay
        # → 入力不可
        # =====================================

        if trip.status == "traveling":

            return (
                day.date
                <= today
            )

        # =====================================
        # 旅完了
        #
        # 通常画面
        # → 入力・編集不可
        #
        # Trip全体編集モード
        # → 入力・編集可能
        # =====================================

        if trip.status == "completed":

            return (
                request.POST.get(
                    "edit_mode"
                )
                == "1"
            )

        return False

    # =====================================
    # Day実際支払額を
    # 個別登録できるか
    #
    # 作成中
    # → 登録可能
    #
    # 出発待ち
    # → 事前支払いがあるため登録可能
    #
    # 旅中
    # → 登録可能
    #
    # 旅完了
    # → Trip全体編集モードのみ登録可能
    # =====================================

    def can_save_day_actual_amount(
        self,
        request,
        day,
        trip,
    ):

        if trip.status in (
            "draft",
            "planned",
            "traveling",
        ):

            return True

        if trip.status == "completed":

            return (
                request.POST.get(
                    "edit_mode"
                )
                == "1"
            )

        return False

    # =====================================
    # Schedule実際支払額を
    # 個別登録できるか
    #
    # 作成中
    # → 登録可能
    #
    # 出発待ち
    # → 事前支払いがあるため登録可能
    #
    # 旅中
    # → 登録可能
    #
    # 旅完了
    # → Trip全体編集モードのみ登録可能
    # =====================================

    def can_save_schedule_actual_amount(
        self,
        request,
        day,
        trip,
    ):

        if trip.status in (
            "draft",
            "planned",
            "traveling",
        ):

            return True

        if trip.status == "completed":

            return (
                request.POST.get(
                    "edit_mode"
                )
                == "1"
            )

        return False

    # =====================================
    # 旅の記録の各項目を削除できるか
    #
    # 作成中・出発待ち
    # → 削除不可
    #
    # 旅中
    # → 今日・過去のDayのみ削除可能
    #
    # 旅完了
    # → Trip全体編集モードのみ削除可能
    #
    # 対象
    # ・写真
    # ・感想
    # ・自由実費
    # ・費用明細1件
    # =====================================

    def can_delete_record_item(
        self,
        request,
        day,
        trip,
    ):

        today = timezone.localdate()

        if trip.status in (
            "draft",
            "planned",
        ):

            return False

        if trip.status == "traveling":

            return (
                day.date
                <= today
            )

        if trip.status == "completed":

            return (
                request.POST.get(
                    "edit_mode"
                )
                == "1"
            )

        return False

    # =====================================
    # 削除済み・未登録の旅の記録項目を
    # 個別に登録できるか
    #
    # 作成中・出発待ち
    # → 登録不可
    #
    # 旅中
    # → 今日・過去のDayのみ登録可能
    #
    # 旅完了
    # → Trip全体編集モードのみ個別登録可能
    #
    # 登録済みの項目はこの個別処理では
    # 上書きしない
    # =====================================

    def can_save_record_item(
        self,
        request,
        day,
        trip,
    ):

        today = timezone.localdate()

        if trip.status in (
            "draft",
            "planned",
        ):

            return False

        if trip.status == "traveling":

            return (
                day.date
                <= today
            )

        if trip.status == "completed":

            return (
                request.POST.get(
                    "edit_mode"
                )
                == "1"
            )

        return False

    # =====================================
    # Day費用明細 FormSet の prefix
    # =====================================

    def get_expense_formset_prefix(
        self,
        day,
    ):

        return (
            f"day_expenses_{day.day_id}"
        )

    # =====================================
    # Day費用明細 FormSet を作成
    # =====================================

    def get_expense_formset(
        self,
        day,
        data=None,
    ):

        return DayExpenseFormSet(
            data,
            instance=day,
            prefix=(
                self.get_expense_formset_prefix(
                    day
                )
            ),
        )

    # =====================================
    # Schedule実際支払額フォームの
    # prefix
    # =====================================

    def get_schedule_record_form_prefix(
        self,
        schedule,
    ):

        return (
            f"schedule_{schedule.schedule_id}"
        )

    # =====================================
    # 実際支払額の入力対象となるSchedule
    #
    # 条件
    # ・予定金額が登録されている
    # ・実際支払額が未入力
    #
    # 予定金額が登録されていないScheduleは
    # 金額入力の対象にしない
    # =====================================

    def get_unpaid_schedules(
        self,
        day,
    ):

        return (
            day.schedules
            .filter(
                planned_amount__isnull=False,
                actual_amount__isnull=True,
            )
            .order_by(
                "schedule_order",
                "schedule_id",
            )
        )

    # =====================================
    # Schedule実際支払額フォーム一覧
    #
    # ・予定金額あり
    # ・実際支払額なし
    #
    # のScheduleだけを対象にする
    # =====================================

    def get_schedule_record_items(
        self,
        day,
        data=None,
    ):

        items = []

        for schedule in (
            self.get_unpaid_schedules(
                day
            )
        ):

            form = (
                ScheduleRecordForm(
                    data,
                    instance=schedule,
                    prefix=(
                        self
                        .get_schedule_record_form_prefix(
                            schedule
                        )
                    ),
                )
            )

            items.append(
                {
                    "schedule": schedule,
                    "form": form,
                }
            )

        return items

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
        # Trip全体編集モードから
        # 操作した場合
        # =====================================

        if (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        ):

            url += "?edit=1"

        # =====================================
        # 操作したDay位置まで移動する
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

        action = (
            request.POST.get(
                "action"
            )
        )

        # =====================================
        # Day実際支払額を個別登録
        #
        # ・予定金額あり
        # ・実際支払額なし
        #
        # の場合のみ登録する
        # =====================================

        if (
            action
            == "save_day_actual_amount"
        ):

            if not (
                self.can_save_day_actual_amount(
                    request,
                    day,
                    trip,
                )
            ):

                return redirect(
                    self.get_return_url(
                        trip,
                        day,
                        request,
                    )
                )

            return (
                self.save_day_actual_amount(
                    request,
                    day,
                    trip,
                )
            )

        # =====================================
        # Schedule実際支払額を個別登録
        #
        # ・予定金額あり
        # ・実際支払額なし
        #
        # の場合のみ登録する
        # =====================================

        if (
            action
            == "save_schedule_actual_amount"
        ):

            if not (
                self.can_save_schedule_actual_amount(
                    request,
                    day,
                    trip,
                )
            ):

                return redirect(
                    self.get_return_url(
                        trip,
                        day,
                        request,
                    )
                )

            return (
                self.save_schedule_actual_amount(
                    request,
                    day,
                    trip,
                )
            )

        # =====================================
        # 旅の記録の各項目を個別削除
        #
        # 旅完了後は
        # edit_mode=1 のときだけ削除可能
        # =====================================

        delete_actions = (
            "delete_day_media",
            "delete_day_content",
            "delete_day_actual_cost",
            "delete_day_expense",
        )

        if action in delete_actions:

            if not (
                self.can_delete_record_item(
                    request,
                    day,
                    trip,
                )
            ):

                return redirect(
                    self.get_return_url(
                        trip,
                        day,
                        request,
                    )
                )

            if (
                action
                == "delete_day_media"
            ):

                return self.delete_media(
                    request,
                    day,
                    trip,
                )

            if (
                action
                == "delete_day_content"
            ):

                return self.delete_content(
                    request,
                    day,
                    trip,
                )

            if (
                action
                == "delete_day_actual_cost"
            ):

                return self.delete_actual_cost(
                    request,
                    day,
                    trip,
                )

            if (
                action
                == "delete_day_expense"
            ):

                return self.delete_expense(
                    request,
                    day,
                    trip,
                )

        # =====================================
        # 未登録になっている旅の記録項目を
        # 個別に再登録
        #
        # completedでは
        # edit_mode=1 のときだけ可能
        #
        # 登録済みの項目は上書きしない
        # =====================================

        save_item_actions = (
            "save_day_media",
            "save_day_content",
            "save_day_actual_cost",
            "save_day_expenses",
        )

        if action in save_item_actions:

            if not (
                self.can_save_record_item(
                    request,
                    day,
                    trip,
                )
            ):

                return redirect(
                    self.get_return_url(
                        trip,
                        day,
                        request,
                    )
                )

            if (
                action
                == "save_day_media"
            ):

                return self.save_media(
                    request,
                    day,
                    trip,
                )

            if (
                action
                == "save_day_content"
            ):

                return self.save_content(
                    request,
                    day,
                    trip,
                )

            if (
                action
                == "save_day_actual_cost"
            ):

                return self.save_actual_cost(
                    request,
                    day,
                    trip,
                )

            if (
                action
                == "save_day_expenses"
            ):

                return self.save_expenses(
                    request,
                    day,
                    trip,
                )

        # =====================================
        # 旅の記録を入力・編集できるか確認
        #
        # completedでは
        # edit_mode=1 がない限り
        # 保存・費用明細編集を行わない
        # =====================================

        if not self.can_edit_record(
            request,
            day,
            trip,
        ):

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        # =====================================
        # 旅の記録を保存
        #
        # ・Day本体
        # ・Day費用明細
        # ・Schedule実際支払額
        #
        # をまとめて保存する
        # =====================================

        return self.update_record(
            request,
            day,
            trip,
        )

    # =====================================
    # Day実際支払額を個別登録
    #
    # 条件
    # ・Day予定金額あり
    # ・Day実際支払額なし
    #
    # planned_amountは変更せず
    # actual_amountだけ保存する
    # =====================================

    def save_day_actual_amount(
        self,
        request,
        day,
        trip,
    ):

        # =====================================
        # 予定金額がないDayは
        # この個別登録の対象外
        # =====================================

        if (
            day.planned_amount
            is None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # すでに実際支払額がある場合は
        # 上書きしない
        # =====================================

        if (
            day.actual_amount
            is not None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        actual_amount = (
            request.POST.get(
                "actual_amount"
            )
        )

        # =====================================
        # DayRecordFormと同じ
        # actual_amountフィールドで検証
        # =====================================

        actual_amount_field = (
            DayRecordForm()
            .fields["actual_amount"]
        )

        try:

            cleaned_actual_amount = (
                actual_amount_field.clean(
                    actual_amount
                )
            )

        except ValidationError:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        if (
            cleaned_actual_amount
            is None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # 実際支払額だけ保存
        #
        # planned_amountは
        # 既存の予定金額をそのまま残す
        # =====================================

        day.actual_amount = (
            cleaned_actual_amount
        )

        day.save(
            update_fields=[
                "actual_amount",
            ]
        )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # Schedule実際支払額を個別登録
    #
    # 条件
    # ・このDayに属するSchedule
    # ・予定金額あり
    # ・実際支払額なし
    #
    # planned_amountは変更せず
    # actual_amountだけ保存する
    # =====================================

    def save_schedule_actual_amount(
        self,
        request,
        day,
        trip,
    ):

        # =====================================
        # POSTされたScheduleを取得
        #
        # 必ず現在のDayに属するScheduleだけ
        # 対象にする
        # =====================================

        schedule = get_object_or_404(
            day.schedules,
            schedule_id=(
                request.POST.get(
                    "schedule_id"
                )
            ),
        )

        # =====================================
        # 予定金額がないScheduleは
        # 個別登録の対象外
        # =====================================

        if (
            schedule.planned_amount
            is None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # すでに実際支払額がある場合は
        # 上書きしない
        # =====================================

        if (
            schedule.actual_amount
            is not None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        actual_amount = (
            request.POST.get(
                "actual_amount"
            )
        )

        # =====================================
        # ScheduleRecordFormと同じ
        # actual_amountフィールドで検証
        # =====================================

        actual_amount_field = (
            ScheduleRecordForm()
            .fields["actual_amount"]
        )

        try:

            cleaned_actual_amount = (
                actual_amount_field.clean(
                    actual_amount
                )
            )

        except ValidationError:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        if (
            cleaned_actual_amount
            is None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # 実際支払額だけ保存
        #
        # planned_amountは
        # 旅行前の予定金額として残す
        # =====================================

        schedule.actual_amount = (
            cleaned_actual_amount
        )

        schedule.save(
            update_fields=[
                "actual_amount",
            ]
        )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # 写真を削除
    # =====================================

    def delete_media(
        self,
        request,
        day,
        trip,
    ):

        if day.media:

            day.media.delete(
                save=False
            )

            day.media = ""

            day.save(
                update_fields=[
                    "media",
                ]
            )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # 感想を削除
    # =====================================

    def delete_content(
        self,
        request,
        day,
        trip,
    ):

        if day.content:

            day.content = ""

            day.save(
                update_fields=[
                    "content",
                ]
            )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # 自由実費を削除
    #
    # Day費用明細が残っている場合は、
    # その合計を自由実費として
    # 後ほど集計時に利用できる
    # =====================================

    def delete_actual_cost(
        self,
        request,
        day,
        trip,
    ):

        if (
            day.actual_cost
            is not None
        ):

            day.actual_cost = None

            day.save(
                update_fields=[
                    "actual_cost",
                ]
            )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # Day費用明細を1件削除
    #
    # 削除後はexpense_orderを
    # 1, 2, 3... に振り直す
    # =====================================

    def delete_expense(
        self,
        request,
        day,
        trip,
    ):

        expense = get_object_or_404(
            DayExpense,
            day_expense_id=(
                request.POST.get(
                    "expense_id"
                )
            ),
            day=day,
        )

        with transaction.atomic():

            expense.delete()

            remaining_expenses = (
                day.day_expenses
                .order_by(
                    "expense_order",
                    "day_expense_id",
                )
            )

            for expense_order, item in enumerate(
                remaining_expenses,
                start=1,
            ):

                if (
                    item.expense_order
                    != expense_order
                ):

                    item.expense_order = (
                        expense_order
                    )

                    item.save(
                        update_fields=[
                            "expense_order",
                        ]
                    )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # 写真を個別登録
    #
    # 写真が未登録の場合だけ保存する
    # 登録済みの場合は上書きしない
    # =====================================

    def save_media(
        self,
        request,
        day,
        trip,
    ):

        if day.media:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        uploaded_media = (
            request.FILES.get(
                "media"
            )
            or request.FILES.get(
                f"day_{day.day_id}-media"
            )
        )

        if (
            uploaded_media
            is None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        media_field = (
            DayRecordForm()
            .fields["media"]
        )

        try:

            cleaned_media = (
                media_field.clean(
                    uploaded_media
                )
            )

        except ValidationError:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        if cleaned_media:

            day.media = (
                cleaned_media
            )

            day.save(
                update_fields=[
                    "media",
                ]
            )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # 感想を個別登録
    #
    # 感想が未登録の場合だけ保存する
    # 登録済みの場合は上書きしない
    # =====================================

    def save_content(
        self,
        request,
        day,
        trip,
    ):

        if day.content:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        content = (
            request.POST.get(
                "content",
                ""
            )
            or ""
        ).strip()

        if not content:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        content_field = (
            DayRecordForm()
            .fields["content"]
        )

        try:

            cleaned_content = (
                content_field.clean(
                    content
                )
            )

        except ValidationError:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        cleaned_content = (
            cleaned_content
            or ""
        ).strip()

        if cleaned_content:

            day.content = (
                cleaned_content
            )

            day.save(
                update_fields=[
                    "content",
                ]
            )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # 自由実費を個別登録
    #
    # actual_costが未登録の場合だけ保存する
    #
    # Day費用明細が登録されていても
    # actual_costを手入力できる
    #
    # actual_costが入力されている場合は
    # 自由実費としてこちらを優先する
    # =====================================

    def save_actual_cost(
        self,
        request,
        day,
        trip,
    ):

        if (
            day.actual_cost
            is not None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        actual_cost = (
            request.POST.get(
                "actual_cost"
            )
        )

        actual_cost_field = (
            DayRecordForm()
            .fields["actual_cost"]
        )

        try:

            cleaned_actual_cost = (
                actual_cost_field.clean(
                    actual_cost
                )
            )

        except ValidationError:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        if (
            cleaned_actual_cost
            is None
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        day.actual_cost = (
            cleaned_actual_cost
        )

        day.save(
            update_fields=[
                "actual_cost",
            ]
        )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # Day費用明細 FormSet を保存
    #
    # ・既存明細の編集
    # ・既存明細の削除
    # ・新規明細の追加
    #
    # をまとめて処理する
    #
    # expense_order は保存時に
    # 1, 2, 3... と振り直す
    # =====================================

    def save_expense_formset(
        self,
        day,
        expense_formset,
    ):

        # =====================================
        # 削除指定された既存費用を削除
        # =====================================

        for deleted_form in (
            expense_formset.deleted_forms
        ):

            if (
                deleted_form.instance
                and deleted_form.instance.pk
            ):

                deleted_form.instance.delete()

        # =====================================
        # 画面に残っている順番で保存
        # =====================================

        expense_order = 1

        for expense_form in (
            expense_formset.forms
        ):

            cleaned_data = getattr(
                expense_form,
                "cleaned_data",
                None,
            )

            if not cleaned_data:

                continue

            if cleaned_data.get(
                "DELETE"
            ):

                continue

            name = (
                cleaned_data.get(
                    "name",
                    ""
                )
                or ""
            ).strip()

            amount = (
                cleaned_data.get(
                    "amount"
                )
            )

            if (
                not name
                and amount is None
            ):

                continue

            day_expense = (
                expense_form.save(
                    commit=False
                )
            )

            day_expense.day = day

            day_expense.expense_order = (
                expense_order
            )

            day_expense.save()

            expense_order += 1

    # =====================================
    # Schedule実際支払額をまとめて保存
    #
    # この処理へ来るScheduleは
    #
    # ・予定金額あり
    # ・実際支払額なし
    #
    # のものだけ
    #
    # 実際支払額が入力された場合のみ
    # 保存する
    # =====================================

    def save_schedule_record_items(
        self,
        schedule_record_items,
    ):

        for item in (
            schedule_record_items
        ):

            form = (
                item["form"]
            )

            schedule = (
                form.save(
                    commit=False
                )
            )

            if (
                schedule.actual_amount
                is None
            ):

                continue

            schedule.save(
                update_fields=[
                    "actual_amount",
                ]
            )

    # =====================================
    # 費用明細だけを個別保存
    #
    # 写真・感想・自由実費には
    # 一切触れない
    # =====================================

    def save_expenses(
        self,
        request,
        day,
        trip,
    ):

        expense_formset = (
            self.get_expense_formset(
                day,
                data=request.POST,
            )
        )

        if (
            expense_formset.is_valid()
        ):

            with transaction.atomic():

                self.save_expense_formset(
                    day,
                    expense_formset,
                )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )

    # =====================================
    # 旅の記録を保存
    #
    # ・写真
    # ・感想
    # ・自由実費
    # ・Day実際支払額
    # ・Day費用明細
    # ・Schedule実際支払額
    #
    # をまとめて保存する
    # =====================================

    def update_record(
        self,
        request,
        day,
        trip,
    ):

        # =====================================
        # Day旅の記録
        # =====================================

        record_form = DayRecordForm(
            request.POST,
            request.FILES,
            instance=day,
            prefix=(
                f"day_{day.day_id}"
            ),
        )

        # =====================================
        # Day費用明細
        # =====================================

        expense_formset = (
            self.get_expense_formset(
                day,
                data=request.POST,
            )
        )

        # =====================================
        # Schedule実際支払額
        #
        # ・予定金額あり
        # ・実際支払額なし
        #
        # のScheduleだけ対象
        # =====================================

        schedule_record_items = (
            self.get_schedule_record_items(
                day,
                data=request.POST,
            )
        )

        # =====================================
        # Validation
        # =====================================

        record_valid = (
            record_form.is_valid()
        )

        expenses_valid = (
            expense_formset.is_valid()
        )

        schedules_valid = all(
            item["form"].is_valid()
            for item in schedule_record_items
        )

        # =====================================
        # すべて有効な場合だけ
        # まとめて保存する
        # =====================================

        if (
            record_valid
            and expenses_valid
            and schedules_valid
        ):

            with transaction.atomic():

                # =====================================
                # Day
                #
                # ・写真
                # ・感想
                # ・自由実費
                # ・Day実際支払額
                # =====================================

                record_form.save()

                # =====================================
                # Day費用明細
                # =====================================

                self.save_expense_formset(
                    day,
                    expense_formset,
                )

                # =====================================
                # Schedule実際支払額
                # =====================================

                self.save_schedule_record_items(
                    schedule_record_items
                )

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )