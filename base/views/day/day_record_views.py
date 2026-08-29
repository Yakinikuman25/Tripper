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
)


# =========================================
# Day旅の記録
#
# 旅行の「実績」を記録する
#
# ・写真
# ・感想
# ・実際の合計費用
# ・費用明細
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
        # → 入力不可
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
    # ・実際の合計費用
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
        # Day費用明細も
        # この保存処理でまとめて保存する
        # =====================================

        return self.update_record(
            request,
            day,
            trip,
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
    # 実際の合計費用を削除
    #
    # Day費用明細が残っている場合は、
    # その合計がDay実績として採用される
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

        # =====================================
        # DayRecordFormのmediaフィールドを使い
        # ファイル形式・モデル側の検証を行う
        # =====================================

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
    # 実際の合計費用を個別登録
    #
    # actual_costが未登録の場合だけ保存する
    # 登録済みの場合は上書きしない
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

            # =====================================
            # 完全に空欄の追加フォームは
            # 保存しない
            # =====================================

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
    # 費用明細だけを個別保存
    #
    # 写真・感想・実際の合計費用には
    # 一切触れない
    #
    # そのため、
    # 写真や感想が登録済みでも
    # 費用明細だけ後から追加・編集できる
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
    # ・実際の合計費用
    # ・Day費用明細
    #
    # を最後の「保存」でまとめて保存する
    #
    # 「＋ 費用を追加」はJavaScriptで
    # 入力欄を増やすだけで、
    # この保存処理まではDBへ反映しない
    # =====================================

    def update_record(
        self,
        request,
        day,
        trip,
    ):

        record_form = DayRecordForm(
            request.POST,
            request.FILES,
            instance=day,
            prefix=(
                f"day_{day.day_id}"
            ),
        )

        expense_formset = (
            self.get_expense_formset(
                day,
                data=request.POST,
            )
        )

        record_valid = (
            record_form.is_valid()
        )

        expenses_valid = (
            expense_formset.is_valid()
        )

        # =====================================
        # 旅の記録・費用明細の両方が
        # 有効な場合だけまとめて保存
        # =====================================

        if (
            record_valid
            and expenses_valid
        ):

            with transaction.atomic():

                # =====================================
                # 写真・感想・実際の合計費用
                # =====================================

                record_form.save()

                # =====================================
                # Day費用明細
                # =====================================

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
        # エラー時
        #
        # 現在のTrip詳細はPOST内容を
        # そのまま再描画する構成ではないため、
        # DB保存はせず元のDay位置へ戻す
        # =====================================

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )