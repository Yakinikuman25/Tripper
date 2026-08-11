from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Max
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    DeleteView,
)

from base.models import (
    Trip,
    Day,
    Hashtag,
    TripHashtag,
    TripExpense,
)

from base.forms import (
    TripForm,
    TripCompleteForm,
    DayRecordForm,
    TripExpenseForm,
)


# =========================================
# Trip期間に合わせてDayを作成・整理する関数
# =========================================

def sync_trip_days(trip):

    current_date = trip.start_date
    day_order = 1

    while current_date <= trip.end_date:

        day, created = Day.objects.get_or_create(
            trip=trip,
            date=current_date,
            defaults={
                "day_order": day_order,
            },
        )

        # 既存Dayの場合もDay番号を更新
        if day.day_order != day_order:

            day.day_order = day_order

            day.save(
                update_fields=[
                    "day_order"
                ]
            )

        current_date += timedelta(
            days=1
        )

        day_order += 1

    # Trip期間外のDayを取得
    outside_days = trip.days.exclude(
        date__range=(
            trip.start_date,
            trip.end_date,
        )
    )

    # ここまで来る時点では削除してよいDayなので削除
    outside_days.delete()

    # Dayから使われなくなったLocationを削除
    trip.locations.filter(
        days__isnull=True
    ).delete()


# =========================================
# Tripのハッシュタグを保存・整理する関数
# =========================================

def sync_trip_hashtags(
    trip,
    hashtag_names,
):

    # 現在のTripとの紐付けを一度すべて削除
    trip.trip_hashtags.all().delete()

    # 入力されたハッシュタグを登録
    for hashtag_name in hashtag_names:

        hashtag, created = (
            Hashtag.objects.get_or_create(
                name=hashtag_name
            )
        )

        TripHashtag.objects.get_or_create(
            trip=trip,
            hashtag=hashtag,
        )


# =========================================
# Dayに何か記入されているか確認する関数
# =========================================

def day_has_data(day):

    return (
        bool(day.title)
        or bool(day.memo)
        or bool(day.content)
        or bool(day.media)
        or day.budget is not None
        or day.actual_cost is not None
        or day.locations.exists()
        or day.spots.exists()
        or day.day_expenses.exists()
    )


# =========================================
# Tripの日付に合わせてステータスを更新する関数
# =========================================

def sync_trip_status(trip):

    today = timezone.localdate()

    # 作成中は
    # 「コース作成完了」を押すまで変更しない
    if trip.status == "draft":

        return

    # 旅完了は自動変更しない
    if trip.status == "completed":

        return

    # 旅行開始日前
    if today < trip.start_date:

        new_status = "planned"

    # 旅行開始日以降
    else:

        new_status = "traveling"

    # 現在のステータスと違う場合だけ更新
    if trip.status != new_status:

        trip.status = new_status

        trip.save(
            update_fields=[
                "status"
            ]
        )


# =========================================
# Trip詳細画面のURLを作る関数
# =========================================

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


# =========================================
# Trip一覧
# =========================================

class TripListView(
    LoginRequiredMixin,
    ListView,
):

    model = Trip

    template_name = (
        "pages/trip_list.html"
    )

    context_object_name = "trips"

    def get_queryset(self):

        trips = Trip.objects.filter(
            user=self.request.user
        ).order_by(
            "-created_at"
        )

        for trip in trips:

            sync_trip_status(
                trip
            )

            locations_by_country = {}

            for location in trip.locations.all():

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

            trip.locations_by_country = (
                locations_by_country
            )

        return trips


# =========================================
# Trip作成
# =========================================

class TripCreateView(
    LoginRequiredMixin,
    CreateView,
):

    model = Trip

    template_name = (
        "pages/trip_create.html"
    )

    form_class = TripForm

    success_url = "/trips/"

    def form_valid(
        self,
        form
    ):

        form.instance.user = (
            self.request.user
        )

        form.instance.status = "draft"

        response = super().form_valid(
            form
        )

        sync_trip_hashtags(
            self.object,
            form.cleaned_data.get(
                "hashtags",
                [],
            ),
        )

        sync_trip_days(
            self.object
        )

        return response


# =========================================
# Trip詳細
# =========================================

class TripDetailView(
    LoginRequiredMixin,
    DetailView,
):

    model = Trip

    template_name = (
        "pages/trip_detail.html"
    )

    context_object_name = "trip"

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def get_object(
        self,
        queryset=None
    ):

        trip = super().get_object(
            queryset
        )

        sync_trip_status(
            trip
        )

        return trip

    # =====================================
    # Trip全体編集モードか
    # =====================================

    def is_edit_mode(self):

        return (
            self.request.GET.get("edit")
            == "1"
        )

    # =====================================
    # Trip共通費用を新しく追加できるか
    #
    # 作成中・出発待ち・旅中
    # → 今までどおり追加可能
    #
    # 旅完了
    # → Trip全体編集時のみ追加可能
    # =====================================

    def can_add_trip_expense(self):

        if self.object.status != "completed":

            return True

        return self.is_edit_mode()

    # =====================================
    # Trip共通費用1件を編集できるか
    #
    # 作成中
    # → 常に編集可能
    #
    # Trip全体編集モード
    # → 常に編集可能
    #
    # それ以外
    # → actual_amount未入力なら編集可能
    # → actual_amount入力済みなら表示のみ
    # =====================================

    def can_edit_trip_expense(
        self,
        trip_expense,
    ):

        # -------------------------
        # 作成中
        # -------------------------
        if self.object.status == "draft":

            return True

        # -------------------------
        # Trip全体編集モード
        # -------------------------
        if self.is_edit_mode():

            return True

        # -------------------------
        # 作成完了後の通常画面
        #
        # 実際支払額が未入力なら
        # 編集可能
        # -------------------------
        if (
            trip_expense.actual_amount
            is None
        ):

            return True

        # -------------------------
        # 実際支払額入力済み
        # → 通常画面では編集不可
        # -------------------------
        return False

    # =====================================
    # Trip共通費用操作後の戻り先
    # =====================================

    def get_trip_expense_return_url(
        self
    ):

        return get_trip_detail_url(
            self.object,
            edit_mode=self.is_edit_mode(),
        )

    # =====================================
    # Context
    # =====================================

    def get_context_data(
        self,
        **kwargs
    ):

        context = (
            super().get_context_data(
                **kwargs
            )
        )

        today = timezone.localdate()

        context["today"] = today

        # -------------------------
        # Trip全体編集モード
        # -------------------------

        edit_mode = self.is_edit_mode()

        context["edit_mode"] = (
            edit_mode
        )

        # -------------------------
        # 作成中ではDay実績を表示しない
        #
        # HTML側で使用
        # -------------------------

        context["show_day_actual"] = (
            self.object.status
            != "draft"
        )

        # =====================================
        # Trip共通費用
        # =====================================

        trip_expenses = list(
            self.object.trip_expenses.all()
        )

        # -------------------------
        # Trip共通費用1件ごとの
        # 編集可否を設定
        # -------------------------

        for trip_expense in trip_expenses:

            trip_expense.can_edit = (
                self.can_edit_trip_expense(
                    trip_expense
                )
            )

        context["trip_expenses"] = (
            trip_expenses
        )

        # -------------------------
        # 新規追加フォームを
        # 表示できるか
        # -------------------------

        context[
            "can_add_trip_expense"
        ] = self.can_add_trip_expense()

        # -------------------------
        # 既存HTMLとの互換用
        #
        # 次にtrip_detail.html側で
        # can_add_trip_expenseへ変更する
        # -------------------------

        context[
            "can_edit_trip_expenses"
        ] = self.can_add_trip_expense()

        if (
            "trip_expense_form"
            not in context
        ):

            context[
                "trip_expense_form"
            ] = TripExpenseForm()

        # -------------------------
        # 旅を完了できるか
        # -------------------------

        context[
            "can_complete_trip"
        ] = (
            self.object.status
            == "traveling"
            and today
            >= self.object.end_date
        )

        # -------------------------
        # ハッシュタグ
        # -------------------------

        context["trip_hashtags"] = (
            self.object.trip_hashtags
            .select_related(
                "hashtag"
            )
            .all()
        )

        # =====================================
        # Trip全体の訪問先
        # =====================================

        locations_by_country = {}

        for location in (
            self.object.locations.all()
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
        ] = locations_by_country

        # =====================================
        # 費用計算
        # =====================================

        # -------------------------
        # Trip共通費用
        # 予定合計
        # -------------------------

        trip_planned_total = 0

        has_trip_planned_cost = False

        for expense in trip_expenses:

            if (
                expense.planned_amount
                is not None
            ):

                trip_planned_total += (
                    expense.planned_amount
                )

                has_trip_planned_cost = True

        # -------------------------
        # Trip共通費用
        # 実績合計
        # -------------------------

        trip_actual_total = 0

        has_trip_actual_cost = False

        for expense in trip_expenses:

            if (
                expense.actual_amount
                is not None
            ):

                trip_actual_total += (
                    expense.actual_amount
                )

                has_trip_actual_cost = True

        # =====================================
        # Dayごとの処理
        # =====================================

        days = self.object.days.all()

        day_budget_total = 0
        day_actual_total = 0

        has_day_budget = False
        has_day_actual_cost = False

        for day in days:

            # -------------------------
            # Day予算
            # -------------------------

            if day.budget is not None:

                day_budget_total += (
                    day.budget
                )

                has_day_budget = True

            # -------------------------
            # Day費用明細合計
            # -------------------------

            day_expense_total = 0

            has_day_expense = False

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

                    has_day_expense = True

            # -------------------------
            # HTML側で使用する
            # Day費用明細参考合計
            # -------------------------

            if has_day_expense:

                day.day_expense_total = (
                    day_expense_total
                )

            else:

                day.day_expense_total = None

            day.has_day_expense = (
                has_day_expense
            )

            # =====================================
            # Day採用実績
            #
            # actual_costあり
            # → actual_cost
            #
            # actual_costなし
            # DayExpenseあり
            # → 費用明細合計
            # =====================================

            if (
                day.actual_cost
                is not None
            ):

                day.adopted_actual_cost = (
                    day.actual_cost
                )

                day.has_actual_cost = True

            elif has_day_expense:

                day.adopted_actual_cost = (
                    day_expense_total
                )

                day.has_actual_cost = True

            else:

                day.adopted_actual_cost = None

                day.has_actual_cost = False

            # -------------------------
            # Trip全体のDay実績へ加算
            # -------------------------

            if day.has_actual_cost:

                day_actual_total += (
                    day.adopted_actual_cost
                )

                has_day_actual_cost = True

            # =====================================
            # Dayごとの訪問先
            # =====================================

            day_locations = {}

            for location in (
                day.locations.all()
            ):

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
            # Spotの並び順
            # =====================================

            day.spots_sorted = (
                day.spots.order_by(
                    F("time").asc(
                        nulls_last=True
                    ),
                    "spot_order",
                )
            )

            # =====================================
            # 旅の記録を入力・編集できるか
            # =====================================

            day.can_edit_record = False

            # -------------------------
            # 旅中
            #
            # 今日・過去のDayのみ
            # 入力可能
            # -------------------------

            if (
                self.object.status
                == "traveling"
            ):

                if day.date <= today:

                    day.can_edit_record = True

            # -------------------------
            # 旅完了
            #
            # Trip全体編集モードのみ
            # 入力・編集可能
            # -------------------------

            elif (
                self.object.status
                == "completed"
            ):

                if edit_mode:

                    day.can_edit_record = True

            # -------------------------
            # 編集可能な場合のみ
            # DayRecordFormを作る
            # -------------------------

            if day.can_edit_record:

                day.record_form = (
                    DayRecordForm(
                        instance=day,
                        prefix=(
                            f"day_{day.day_id}"
                        ),
                    )
                )

        context["days"] = days

        # =====================================
        # Trip予定合計
        # =====================================

        has_planned_cost = (
            has_trip_planned_cost
            or has_day_budget
        )

        if has_planned_cost:

            planned_total = (
                trip_planned_total
                + day_budget_total
            )

        else:

            planned_total = None

        context[
            "trip_planned_cost_total"
        ] = (
            trip_planned_total
            if has_trip_planned_cost
            else None
        )

        context[
            "has_trip_planned_cost"
        ] = has_trip_planned_cost

        context[
            "day_budget_total"
        ] = (
            day_budget_total
            if has_day_budget
            else None
        )

        context[
            "has_day_budget"
        ] = has_day_budget

        context[
            "planned_total"
        ] = planned_total

        context[
            "has_planned_cost"
        ] = has_planned_cost

        # =====================================
        # Trip参考実績
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

            reference_actual_total = None

        context[
            "trip_actual_cost_total"
        ] = (
            trip_actual_total
            if has_trip_actual_cost
            else None
        )

        context[
            "has_trip_actual_cost"
        ] = has_trip_actual_cost

        context[
            "day_actual_cost_total"
        ] = (
            day_actual_total
            if has_day_actual_cost
            else None
        )

        context[
            "has_day_actual_cost"
        ] = has_day_actual_cost

        context[
            "reference_actual_total"
        ] = reference_actual_total

        context[
            "has_reference_actual_cost"
        ] = has_reference_actual_cost

        # =====================================
        # Trip最終実績
        # =====================================

        if (
            self.object.total_cost
            is not None
        ):

            final_actual_total = (
                self.object.total_cost
            )

            has_final_actual_cost = True

            context[
                "is_manual_total_cost"
            ] = True

        elif has_reference_actual_cost:

            final_actual_total = (
                reference_actual_total
            )

            has_final_actual_cost = True

            context[
                "is_manual_total_cost"
            ] = False

        else:

            final_actual_total = None

            has_final_actual_cost = False

            context[
                "is_manual_total_cost"
            ] = False

        context[
            "final_actual_total"
        ] = final_actual_total

        context[
            "has_final_actual_cost"
        ] = has_final_actual_cost

        # =====================================
        # 予定と実績の差額
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

        return context

    # =====================================
    # Trip詳細からTrip共通費用を操作
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        self.object = (
            self.get_object()
        )

        action = request.POST.get(
            "action"
        )

        # =================================
        # 新規追加
        # =================================

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

            return self.add_trip_expense(
                request
            )

        # =================================
        # 更新
        # =================================

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

            # -------------------------
            # この費用が編集可能か
            # サーバー側でも確認
            # -------------------------

            if not (
                self.can_edit_trip_expense(
                    trip_expense
                )
            ):

                return redirect(
                    self.get_trip_expense_return_url()
                )

            return (
                self.update_trip_expense(
                    request,
                    trip_expense,
                )
            )

        # =================================
        # 削除
        # =================================

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

            # -------------------------
            # 編集不可の費用は
            # 通常画面から削除も不可
            # -------------------------

            if not (
                self.can_edit_trip_expense(
                    trip_expense
                )
            ):

                return redirect(
                    self.get_trip_expense_return_url()
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
    # Trip共通費用追加
    # =====================================

    def add_trip_expense(
        self,
        request
    ):

        expense_form = (
            TripExpenseForm(
                request.POST
            )
        )

        if expense_form.is_valid():

            trip_expense = (
                expense_form.save(
                    commit=False
                )
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

            if max_order is None:

                max_order = 0

            trip_expense.expense_order = (
                max_order + 1
            )

            trip_expense.save()

            return redirect(
                self.get_trip_expense_return_url()
            )

        context = (
            self.get_context_data(
                trip_expense_form=(
                    expense_form
                )
            )
        )

        return (
            self.render_to_response(
                context
            )
        )

    # =====================================
    # Trip共通費用編集
    # =====================================

    def update_trip_expense(
        self,
        request,
        trip_expense,
    ):

        expense_form = (
            TripExpenseForm(
                request.POST,
                instance=trip_expense,
            )
        )

        if expense_form.is_valid():

            expense_form.save()

        return redirect(
            self.get_trip_expense_return_url()
        )

    # =====================================
    # Trip共通費用削除
    # =====================================

    def delete_trip_expense(
        self,
        trip_expense,
    ):

        trip_expense.delete()

        return redirect(
            self.get_trip_expense_return_url()
        )


# =========================================
# Trip編集
# =========================================

class TripUpdateView(
    LoginRequiredMixin,
    UpdateView,
):

    model = Trip

    form_class = TripForm

    template_name = (
        "pages/trip_create.html"
    )

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def form_valid(
        self,
        form
    ):

        new_start_date = (
            form.cleaned_data[
                "start_date"
            ]
        )

        new_end_date = (
            form.cleaned_data[
                "end_date"
            ]
        )

        hashtag_names = (
            form.cleaned_data.get(
                "hashtags",
                [],
            )
        )

        outside_days = (
            self.object.days.exclude(
                date__range=(
                    new_start_date,
                    new_end_date,
                )
            )
        )

        filled_outside_days = []

        for day in outside_days:

            if day_has_data(day):

                filled_outside_days.append(
                    day
                )

        if filled_outside_days:

            category = (
                form.cleaned_data.get(
                    "category"
                )
            )

            self.request.session[
                "pending_trip_update"
            ] = {

                "trip_id": (
                    self.object.trip_id
                ),

                "title": (
                    form.cleaned_data[
                        "title"
                    ]
                ),

                "category_id": (
                    category.category_id
                    if category
                    else None
                ),

                "start_date": (
                    new_start_date.isoformat()
                ),

                "end_date": (
                    new_end_date.isoformat()
                ),

                "memo": (
                    form.cleaned_data.get(
                        "memo",
                        "",
                    )
                ),

                "hashtags": (
                    hashtag_names
                ),
            }

            return redirect(
                "trip_period_confirm",
                pk=self.object.trip_id,
            )

        response = (
            super().form_valid(
                form
            )
        )

        sync_trip_hashtags(
            self.object,
            hashtag_names,
        )

        sync_trip_days(
            self.object
        )

        sync_trip_status(
            self.object
        )

        return response

    def get_success_url(self):

        if (
            self.object.status
            == "draft"
        ):

            return (
                get_trip_detail_url(
                    self.object
                )
            )

        return get_trip_detail_url(
            self.object,
            edit_mode=True,
        )


# =========================================
# Trip期間短縮確認
# =========================================

class TripPeriodConfirmView(
    LoginRequiredMixin,
    View,
):

    template_name = (
        "pages/trip_period_confirm.html"
    )

    def get_trip(self):

        return get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=self.request.user,
        )

    def get_pending_data(self):

        pending_data = (
            self.request.session.get(
                "pending_trip_update"
            )
        )

        if not pending_data:

            return None

        if (
            pending_data.get(
                "trip_id"
            )
            != self.kwargs["pk"]
        ):

            return None

        return pending_data

    def get(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = self.get_trip()

        pending_data = (
            self.get_pending_data()
        )

        if not pending_data:

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        new_start_date = (
            date.fromisoformat(
                pending_data[
                    "start_date"
                ]
            )
        )

        new_end_date = (
            date.fromisoformat(
                pending_data[
                    "end_date"
                ]
            )
        )

        outside_days = (
            trip.days.exclude(
                date__range=(
                    new_start_date,
                    new_end_date,
                )
            )
        )

        return render(
            request,
            self.template_name,
            {
                "trip": trip,

                "outside_days": (
                    outside_days
                ),

                "new_start_date": (
                    new_start_date
                ),

                "new_end_date": (
                    new_end_date
                ),
            },
        )

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = self.get_trip()

        pending_data = (
            self.get_pending_data()
        )

        if not pending_data:

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        action = request.POST.get(
            "action"
        )

        # -------------------------
        # キャンセル
        # -------------------------

        if action == "cancel":

            del request.session[
                "pending_trip_update"
            ]

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        # -------------------------
        # 変更確定
        # -------------------------

        if action == "confirm":

            new_start_date = (
                date.fromisoformat(
                    pending_data[
                        "start_date"
                    ]
                )
            )

            new_end_date = (
                date.fromisoformat(
                    pending_data[
                        "end_date"
                    ]
                )
            )

            with transaction.atomic():

                outside_days = (
                    trip.days.exclude(
                        date__range=(
                            new_start_date,
                            new_end_date,
                        )
                    )
                )

                outside_days.delete()

                trip.title = (
                    pending_data[
                        "title"
                    ]
                )

                trip.category_id = (
                    pending_data[
                        "category_id"
                    ]
                )

                trip.start_date = (
                    new_start_date
                )

                trip.end_date = (
                    new_end_date
                )

                trip.memo = (
                    pending_data.get(
                        "memo",
                        "",
                    )
                )

                trip.save()

                sync_trip_hashtags(
                    trip,
                    pending_data.get(
                        "hashtags",
                        [],
                    ),
                )

                sync_trip_days(
                    trip
                )

                sync_trip_status(
                    trip
                )

            del request.session[
                "pending_trip_update"
            ]

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        return redirect(
            "trip_period_confirm",
            pk=trip.trip_id,
        )


# =========================================
# Tripステータス変更
#
# ・作成中 → コース作成完了
# ・旅完了 → 旅中へ戻す
# =========================================

class TripStatusUpdateView(
    LoginRequiredMixin,
    View,
):

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=request.user,
        )

        action = request.POST.get(
            "action"
        )

        # =====================================
        # コース作成完了
        # =====================================

        if (
            action
            == "complete_plan"
        ):

            # 作成中Tripのみ
            if (
                trip.status
                != "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            today = timezone.localdate()

            # -------------------------
            # 旅行開始日前
            # → 出発待ち
            # -------------------------

            if today < trip.start_date:

                trip.status = "planned"

            # -------------------------
            # 旅行開始日以降
            # → 旅中
            # -------------------------

            else:

                trip.status = "traveling"

            trip.save(
                update_fields=[
                    "status"
                ]
            )

            return redirect(
                get_trip_detail_url(
                    trip
                )
            )

        # =====================================
        # 旅完了から旅中へ戻す
        # =====================================

        if (
            action
            == "reopen_trip"
        ):

            # 旅完了Tripのみ
            if (
                trip.status
                != "completed"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            # -------------------------
            # ステータスを旅中へ戻す
            # -------------------------

            trip.status = "traveling"

            # -------------------------
            # 旅中は非公開固定
            # 代表写真・感想は削除しない
            # -------------------------

            trip.is_public = False

            trip.save(
                update_fields=[
                    "status",
                    "is_public",
                ]
            )

            return redirect(
                get_trip_detail_url(
                    trip
                )
            )

        return redirect(
            get_trip_detail_url(
                trip
            )
        )


# =========================================
# Trip完了・旅完了情報編集
# =========================================

class TripCompleteView(
    LoginRequiredMixin,
    UpdateView,
):

    model = Trip

    form_class = TripCompleteForm

    template_name = (
        "pages/trip_complete.html"
    )

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        self.trip = get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=request.user,
        )

        self.was_completed = (
            self.trip.status
            == "completed"
        )

        sync_trip_status(
            self.trip
        )

        today = timezone.localdate()

        if (
            self.trip.status
            == "traveling"
        ):

            if (
                today
                < self.trip.end_date
            ):

                return redirect(
                    get_trip_detail_url(
                        self.trip
                    )
                )

        elif (
            self.trip.status
            == "completed"
        ):

            pass

        else:

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

    def get_context_data(
        self,
        **kwargs
    ):

        context = (
            super().get_context_data(
                **kwargs
            )
        )

        context["trip"] = (
            self.object
        )

        context[
            "is_completed_edit"
        ] = (
            self.object.status
            == "completed"
        )

        return context

    def form_valid(
        self,
        form
    ):

        form.instance.status = (
            "completed"
        )

        return super().form_valid(
            form
        )

    def get_success_url(self):

        if self.was_completed:

            return get_trip_detail_url(
                self.object,
                edit_mode=True,
            )

        return get_trip_detail_url(
            self.object
        )


# =========================================
# Trip削除
# =========================================

class TripDeleteView(
    LoginRequiredMixin,
    DeleteView,
):

    model = Trip

    template_name = (
        "pages/trip_delete.html"
    )

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def get_success_url(self):

        return reverse_lazy(
            "trip_list"
        )


# =========================================
# Trip公開設定変更
# =========================================

class TripPublicUpdateView(
    LoginRequiredMixin,
    View,
):

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=request.user,
        )

        # 旅完了以外では
        # 公開設定を変更しない
        if (
            trip.status
            != "completed"
        ):

            return redirect(
                get_trip_detail_url(
                    trip
                )
            )

        action = request.POST.get(
            "action"
        )

        if action == "public":

            if (
                not trip.main_media
                or not trip.overview
            ):

                return redirect(
                    get_trip_detail_url(
                        trip,
                        edit_mode=True,
                    )
                )

            trip.is_public = True

            trip.save(
                update_fields=[
                    "is_public"
                ]
            )

        elif action == "private":

            trip.is_public = False

            trip.save(
                update_fields=[
                    "is_public"
                ]
            )

        return redirect(
            get_trip_detail_url(
                trip,
                edit_mode=True,
            )
        )