from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import UpdateView

from base.models import (
    Day,
    Location,
    DayExpense,
)

from base.forms import (
    DayForm,
    DayRecordForm,
    DayExpenseForm,
)


# =========================================
# Day編集
#
# 旅行の「計画」を編集する
#
# ・Dayタイトル
# ・1日の予算
# ・訪問先
# =========================================

class DayUpdateView(
    LoginRequiredMixin,
    UpdateView,
):

    model = Day
    form_class = DayForm
    template_name = "pages/day_edit.html"

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        self.object = self.get_object()
        self.trip = self.object.trip

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def get_queryset(self):

        return Day.objects.filter(
            trip__user=self.request.user
        )

    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )

        context["trip"] = self.trip

        # =====================================
        # 現在のDayに登録されている
        # 訪問先を国ごとにまとめる
        # =====================================

        location_groups = {}

        for location in self.object.locations.all():

            if (
                location.country
                not in location_groups
            ):

                location_groups[
                    location.country
                ] = []

            if (
                location.region
                not in location_groups[
                    location.country
                ]
            ):

                location_groups[
                    location.country
                ].append(
                    location.region
                )

        context["location_groups"] = (
            location_groups
        )

        # =====================================
        # Trip全体で登録済みの
        # 訪問先候補
        # =====================================

        trip_location_groups = {}

        for location in self.trip.locations.all():

            if (
                location.country
                not in trip_location_groups
            ):

                trip_location_groups[
                    location.country
                ] = []

            if (
                location.region
                not in trip_location_groups[
                    location.country
                ]
            ):

                trip_location_groups[
                    location.country
                ].append(
                    location.region
                )

        context["trip_location_groups"] = (
            trip_location_groups
        )

        return context

    # =====================================
    # Day編集保存
    # =====================================

    def form_valid(self, form):

        countries = (
            self.request.POST.getlist(
                "countries"
            )
        )

        location_data = []
        registered_locations = set()

        for index, country in enumerate(
            countries
        ):

            country = country.strip()

            regions = (
                self.request.POST.getlist(
                    f"regions_{index}"
                )
            )

            for region in regions:

                region = region.strip()

                if country and region:

                    location_key = (
                        country,
                        region,
                    )

                    # -------------------------
                    # 同じDayに
                    # 同じ国・地域を重複登録しない
                    # -------------------------
                    if (
                        location_key
                        in registered_locations
                    ):

                        form.add_error(
                            None,
                            (
                                f"「{country} / "
                                f"{region}」"
                                "はすでにこのDayに"
                                "登録されています。"
                            )
                        )

                        return self.form_invalid(
                            form
                        )

                    registered_locations.add(
                        location_key
                    )

                    location_data.append(
                        location_key
                    )

        response = super().form_valid(
            form
        )

        # -------------------------
        # 一度DayとLocationの
        # 紐付けを解除
        # -------------------------
        self.object.locations.clear()

        # -------------------------
        # 入力されたLocationを登録
        # -------------------------
        for country, region in location_data:

            location, created = (
                Location.objects.get_or_create(
                    trip=self.trip,
                    country=country,
                    region=region,
                )
            )

            self.object.locations.add(
                location
            )

        # -------------------------
        # どのDayからも
        # 使われなくなったLocationを削除
        # -------------------------
        self.trip.locations.filter(
            days__isnull=True
        ).delete()

        return response

    # =====================================
    # Day編集保存後
    # =====================================

    def get_success_url(self):

        # -------------------------
        # 作成中
        # → 通常Trip詳細へ戻る
        # -------------------------
        if self.trip.status == "draft":

            return reverse(
                "trip_detail",
                kwargs={
                    "pk": self.trip.trip_id,
                },
            )

        # -------------------------
        # 出発待ち・旅中・旅完了
        # → Trip全体編集モードへ戻る
        # -------------------------
        return (
            reverse(
                "trip_detail",
                kwargs={
                    "pk": self.trip.trip_id,
                },
            )
            + "?edit=1"
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

        # -------------------------
        # 作成中・出発待ち
        # → 入力不可
        # -------------------------
        if trip.status in (
            "draft",
            "planned",
        ):

            return False

        # -------------------------
        # 旅中
        #
        # 今日・過去のDay
        # → 通常画面から入力可能
        #
        # 未来のDay
        # → 入力不可
        # -------------------------
        if trip.status == "traveling":

            return (
                day.date
                <= today
            )

        # -------------------------
        # 旅完了
        #
        # 通常画面
        # → 入力・編集不可
        #
        # Trip全体編集モード
        # → 入力・編集可能
        # -------------------------
        if trip.status == "completed":

            return (
                request.POST.get(
                    "edit_mode"
                )
                == "1"
            )

        return False

    # =====================================
    # Trip詳細へ戻るURL
    # =====================================

    def get_return_url(
        self,
        trip,
        request,
    ):

        url = reverse(
            "trip_detail",
            kwargs={
                "pk": trip.trip_id,
            },
        )

        # -------------------------
        # Trip全体編集モードから
        # 操作した場合
        # -------------------------
        if (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        ):

            url += "?edit=1"

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

        # =====================================
        # 旅の記録を入力・編集できるか確認
        #
        # completedでは
        # edit_mode=1 がない限り
        # 保存処理を行わない
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

        action = request.POST.get(
            "action"
        )

        # -------------------------
        # Day費用明細追加
        # -------------------------
        if action == "add_day_expense":

            return self.add_expense(
                request,
                day,
                trip,
            )

        # -------------------------
        # Day費用明細編集
        # -------------------------
        if action == "update_day_expense":

            return self.update_expense(
                request,
                day,
                trip,
            )

        # -------------------------
        # Day費用明細削除
        # -------------------------
        if action == "delete_day_expense":

            return self.delete_expense(
                request,
                day,
                trip,
            )

        # -------------------------
        # 写真・感想・実際の合計費用
        # を保存
        # -------------------------
        return self.update_record(
            request,
            day,
            trip,
        )

    # =====================================
    # 写真・感想・実際の合計費用
    # =====================================

    def update_record(
        self,
        request,
        day,
        trip,
    ):

        form = DayRecordForm(
            request.POST,
            request.FILES,
            instance=day,
            prefix=f"day_{day.day_id}",
        )

        if form.is_valid():

            form.save()

        return redirect(
            self.get_return_url(
                trip,
                request,
            )
        )

    # =====================================
    # Day費用明細追加
    # =====================================

    def add_expense(
        self,
        request,
        day,
        trip,
    ):

        expense_form = DayExpenseForm(
            request.POST
        )

        if expense_form.is_valid():

            amount = (
                expense_form.cleaned_data.get(
                    "amount"
                )
            )

            # -------------------------
            # DayExpenseは
            # 登録する場合は金額必須
            # -------------------------
            if amount is not None:

                day_expense = (
                    expense_form.save(
                        commit=False
                    )
                )

                day_expense.day = day

                # -------------------------
                # 表示順を自動採番
                # -------------------------
                max_order = (
                    day.day_expenses.aggregate(
                        Max(
                            "expense_order"
                        )
                    )[
                        "expense_order__max"
                    ]
                )

                if max_order is None:

                    max_order = 0

                day_expense.expense_order = (
                    max_order + 1
                )

                day_expense.save()

        return redirect(
            self.get_return_url(
                trip,
                request,
            )
        )

    # =====================================
    # Day費用明細編集
    # =====================================

    def update_expense(
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

        expense_form = DayExpenseForm(
            request.POST,
            instance=expense,
        )

        if expense_form.is_valid():

            amount = (
                expense_form.cleaned_data.get(
                    "amount"
                )
            )

            # -------------------------
            # 金額がある場合のみ保存
            # -------------------------
            if amount is not None:

                expense_form.save()

        return redirect(
            self.get_return_url(
                trip,
                request,
            )
        )

    # =====================================
    # Day費用明細削除
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

        expense.delete()

        return redirect(
            self.get_return_url(
                trip,
                request,
            )
        )