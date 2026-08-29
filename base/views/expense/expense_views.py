from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView

from base.models import (
    Trip,
    Day,
    TripExpense,
    DayExpense,
)

from base.forms import (
    TripExpenseForm,
    DayExpenseForm,
)


# Trip詳細画面のURLを作成する関数
def get_trip_detail_url(
    trip,
    edit_mode=False,
):

    url = reverse(
        "trip_detail",
        kwargs={
            "pk": trip.trip_id,
        },
    )

    if edit_mode:

        url += "?edit=1"

    return url


# Trip共通費用作成
class TripExpenseCreateView(
    LoginRequiredMixin,
    CreateView,
):

    model = TripExpense
    form_class = TripExpenseForm
    template_name = "pages/trip_expense_create.html"

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        self.trip = get_object_or_404(
            Trip,
            trip_id=self.kwargs["trip_id"],
            user=request.user,
        )

        # -------------------------
        # Trip共通費用の編集ルール
        #
        # 作成中・出発待ち・旅中
        # → いつでも編集可能
        #
        # 旅完了
        # → Trip全体編集モードのみ
        # -------------------------
        if self.trip.status == "completed":

            if (
                request.GET.get("edit")
                != "1"
            ):

                return redirect(
                    get_trip_detail_url(
                        self.trip
                    )
                )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def form_valid(self, form):

        form.instance.trip = self.trip

        max_order = (
            self.trip.trip_expenses.aggregate(
                Max("expense_order")
            )["expense_order__max"]
        )

        if max_order is None:

            max_order = 0

        form.instance.expense_order = (
            max_order + 1
        )

        return super().form_valid(
            form
        )

    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )

        context["trip"] = self.trip

        return context

    def get_success_url(self):

        # -------------------------
        # 旅完了前
        # → 通常Trip詳細画面へ戻る
        # -------------------------
        if self.trip.status != "completed":

            return get_trip_detail_url(
                self.trip
            )

        # -------------------------
        # 旅完了後
        # → Trip全体編集モードへ戻る
        # -------------------------
        return get_trip_detail_url(
            self.trip,
            edit_mode=True,
        )


# Day費用作成
class DayExpenseCreateView(
    LoginRequiredMixin,
    CreateView,
):

    model = DayExpense
    form_class = DayExpenseForm
    template_name = "pages/day_expense_create.html"

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        self.day = get_object_or_404(
            Day,
            day_id=self.kwargs["day_id"],
            trip__user=request.user,
        )

        self.trip = self.day.trip

        today = timezone.localdate()

        # -------------------------
        # Day費用の入力ルール
        #
        # 作成中
        # → 入力不可
        #
        # 出発待ち
        # → 入力不可
        #
        # 旅中
        # → 今日または過去のDayのみ
        #
        # 旅完了
        # → Trip全体編集モードのみ
        # -------------------------

        if self.trip.status in (
            "draft",
            "planned",
        ):

            return redirect(
                get_trip_detail_url(
                    self.trip
                )
            )

        if self.trip.status == "traveling":

            if self.day.date > today:

                return redirect(
                    get_trip_detail_url(
                        self.trip
                    )
                )

        if self.trip.status == "completed":

            if (
                request.GET.get("edit")
                != "1"
            ):

                return redirect(
                    get_trip_detail_url(
                        self.trip
                    )
                )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def form_valid(self, form):

        form.instance.day = self.day

        max_order = (
            self.day.day_expenses.aggregate(
                Max("expense_order")
            )["expense_order__max"]
        )

        if max_order is None:

            max_order = 0

        form.instance.expense_order = (
            max_order + 1
        )

        return super().form_valid(
            form
        )

    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )

        context["day"] = self.day
        context["trip"] = self.trip

        return context

    def get_success_url(self):

        # -------------------------
        # 旅中
        # → 通常Trip詳細画面へ戻る
        # -------------------------
        if self.trip.status == "traveling":

            return get_trip_detail_url(
                self.trip
            )

        # -------------------------
        # 旅完了
        # → Trip全体編集モードへ戻る
        # -------------------------
        if self.trip.status == "completed":

            return get_trip_detail_url(
                self.trip,
                edit_mode=True,
            )

        return get_trip_detail_url(
            self.trip
        )