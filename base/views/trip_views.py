from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F, Max, Q
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
    TripReferenceUrl,
    TripHashtag,
    TripExpense,
    TripExpenseReferenceUrl,
    Category,
)

from base.forms import (
    TripForm,
    TripCompleteForm,
    DayRecordForm,
    TripExpenseForm,
    TripReferenceUrlFormSet,
    TripExpenseReferenceUrlFormSet,
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

    # DayLocationから使われなくなったLocationを削除
    trip.locations.filter(
        day_locations__isnull=True
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
# Trip参考URL FormSetから
# 保存対象データを取り出す関数
# =========================================

def get_trip_reference_url_items(
    formset,
):

    reference_url_items = []

    for url_form in formset.forms:

        cleaned_data = getattr(
            url_form,
            "cleaned_data",
            None,
        )

        if not cleaned_data:

            continue

        if cleaned_data.get(
            "DELETE"
        ):

            continue

        url = (
            cleaned_data.get(
                "url",
                "",
            )
            or ""
        ).strip()

        title = (
            cleaned_data.get(
                "title",
                "",
            )
            or ""
        ).strip()

        # URLが空欄の追加フォームは保存しない
        if not url:

            continue

        reference_url_items.append(
            {
                "title": title,
                "url": url,
            }
        )

    return reference_url_items


# =========================================
# Trip参考URLを保存・整理する関数
#
# 編集時は現在の参考URLを一度削除して、
# フォーム上に残っているURLを
# 表示順どおりに作り直す
# =========================================

def sync_trip_reference_urls(
    trip,
    reference_url_items,
):

    trip.reference_urls.all().delete()

    for url_order, item in enumerate(
        reference_url_items,
        start=1,
    ):

        TripReferenceUrl.objects.create(
            trip=trip,
            title=item.get(
                "title",
                "",
            ),
            url=item["url"],
            url_order=url_order,
        )


# =========================================
# Trip全体費用参考URL FormSetから
# 保存対象データを取り出す関数
# =========================================

def get_trip_expense_reference_url_items(
    formset,
):

    reference_url_items = []

    for url_form in formset.forms:

        cleaned_data = getattr(
            url_form,
            "cleaned_data",
            None,
        )

        if not cleaned_data:

            continue

        if cleaned_data.get(
            "DELETE"
        ):

            continue

        title = (
            cleaned_data.get(
                "title",
                "",
            )
            or ""
        ).strip()

        url = (
            cleaned_data.get(
                "url",
                "",
            )
            or ""
        ).strip()

        # URLが空欄の追加フォームは保存しない
        if not url:

            continue

        reference_url_items.append(
            {
                "title": title,
                "url": url,
            }
        )

    return reference_url_items


# =========================================
# Trip全体費用参考URLを保存・整理する関数
#
# 現在の参考URLを一度削除して、
# フォーム上に残っているURLを
# 表示順どおりに作り直す
# =========================================

def sync_trip_expense_reference_urls(
    trip_expense,
    reference_url_items,
):

    trip_expense.reference_urls.all().delete()

    for url_order, item in enumerate(
        reference_url_items,
        start=1,
    ):

        TripExpenseReferenceUrl.objects.create(
            trip_expense=trip_expense,
            title=item.get(
                "title",
                "",
            ),
            url=item["url"],
            url_order=url_order,
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
        or day.reference_urls.exists()
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
# 旅行全体の実際費用を計算する関数
#
# 1. Trip.total_cost が手入力されている場合
#    → その金額を最優先
#
# 2. Trip.total_cost が未入力の場合
#    → Trip全体費用の実績合計
#      ＋ 各Dayの採用実績
#
# Dayの採用実績
# ・day.actual_cost がある場合
#   → day.actual_cost
# ・day.actual_cost がなくDayExpenseがある場合
#   → DayExpenseの合計
#
# 3. 実績が1件もない場合
#    → None
# =========================================

def calculate_trip_actual_total(trip):

    # -------------------------
    # 手入力されたTrip全体費用を最優先
    # -------------------------
    if trip.total_cost is not None:

        return trip.total_cost

    actual_total = 0
    has_actual_cost = False

    # =====================================
    # Trip全体費用の実績
    # =====================================

    for expense in trip.trip_expenses.all():

        if expense.actual_amount is not None:

            actual_total += expense.actual_amount
            has_actual_cost = True

    # =====================================
    # Day実績
    # =====================================

    for day in trip.days.all():

        # -------------------------
        # Day全体の実際費用がある場合
        # -------------------------
        if day.actual_cost is not None:

            actual_total += day.actual_cost
            has_actual_cost = True

        # -------------------------
        # Day全体の実際費用がない場合
        # → DayExpenseを合計
        # -------------------------
        else:

            day_expense_total = 0
            has_day_expense = False

            for expense in day.day_expenses.all():

                if expense.amount is not None:

                    day_expense_total += expense.amount
                    has_day_expense = True

            if has_day_expense:

                actual_total += day_expense_total
                has_actual_cost = True

    # =====================================
    # 実績が1件もない場合
    # =====================================

    if not has_actual_cost:

        return None

    return actual_total


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
# みんなのTrip一覧
# =========================================

class PublicTripListView(
    LoginRequiredMixin,
    ListView,
):

    model = Trip

    template_name = (
        "pages/public_trip.html"
    )

    context_object_name = (
        "public_trips"
    )

    # 1ページに表示する公開Trip数
    paginate_by = 30

    # =====================================
    # GETパラメータを整数に変換する関数
    #
    # 空欄・数字以外・条件外の値は
    # Noneとして扱う
    # =====================================

    def parse_int_param(
        self,
        name,
        minimum=None,
    ):

        value = self.request.GET.get(
            name,
            "",
        ).strip()

        if not value:

            return None

        try:

            number = int(value)

        except ValueError:

            return None

        if (
            minimum is not None
            and number < minimum
        ):

            return None

        return number

    # =====================================
    # 公開Trip取得・検索・絞り込み
    # =====================================

    def get_queryset(self):

        self.filter_errors = []

        trips = (
            Trip.objects
            .filter(
                status="completed",
                is_public=True,
            )
            .select_related(
                "user",
                "user__profile",
                "category",
            )
            .prefetch_related(
                "locations",
                "trip_hashtags__hashtag",
                "trip_expenses",
                "days__day_expenses",
            )
        )

        # =====================================
        # キーワード検索
        #
        # 対象
        # ・Tripタイトル
        # ・訪問国
        # ・地域
        # ・カテゴリ
        # ・ハッシュタグ
        # ・感想
        # =====================================

        keyword = self.request.GET.get(
            "q",
            "",
        ).strip()

        if keyword:

            trips = trips.filter(
                Q(
                    title__icontains=(
                        keyword
                    )
                )
                | Q(
                    locations__country__icontains=(
                        keyword
                    )
                )
                | Q(
                    locations__region__icontains=(
                        keyword
                    )
                )
                | Q(
                    category__name__icontains=(
                        keyword
                    )
                )
                | Q(
                    trip_hashtags__hashtag__name__icontains=(
                        keyword
                    )
                )
                | Q(
                    overview__icontains=(
                        keyword
                    )
                )
            )

        # =====================================
        # カテゴリ絞り込み
        # =====================================

        category_id = (
            self.parse_int_param(
                "category",
                minimum=1,
            )
        )

        if category_id is not None:

            trips = trips.filter(
                category_id=category_id
            )

        # =====================================
        # ハッシュタグ絞り込み
        #
        # 入力された文字を含む
        # ハッシュタグを対象にする
        # =====================================

        hashtag = self.request.GET.get(
            "hashtag",
            "",
        ).strip()

        # 先頭に#が入力されても検索できるようにする
        hashtag = hashtag.lstrip("#")

        if hashtag:

            trips = trips.filter(
                trip_hashtags__hashtag__name__icontains=(
                    hashtag
                )
            )

        # M2M・訪問先検索による重複を除外
        trips = trips.distinct()

        # =====================================
        # 旅行日数条件
        # =====================================

        min_days = self.parse_int_param(
            "min_days",
            minimum=1,
        )

        max_days = self.parse_int_param(
            "max_days",
            minimum=1,
        )

        if (
            min_days is not None
            and max_days is not None
            and min_days > max_days
        ):

            self.filter_errors.append(
                "旅行日数は、最低日数を最高日数以下にしてください。"
            )

        # =====================================
        # 費用条件
        # =====================================

        min_cost = self.parse_int_param(
            "min_cost",
            minimum=0,
        )

        max_cost = self.parse_int_param(
            "max_cost",
            minimum=0,
        )

        if (
            min_cost is not None
            and max_cost is not None
            and min_cost > max_cost
        ):

            self.filter_errors.append(
                "費用は、最低費用を最高費用以下にしてください。"
            )

        # =====================================
        # QuerySetをリスト化して
        # 計算値を各Tripへ設定
        # =====================================

        trip_list = list(trips)

        for trip in trip_list:

            # -------------------------
            # 訪問先を国ごとにまとめる
            # -------------------------

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

            # -------------------------
            # 旅行日数
            #
            # 開始日と終了日を含めるため
            # +1日する
            # -------------------------

            trip.trip_days = (
                trip.end_date
                - trip.start_date
            ).days + 1

            # -------------------------
            # 旅行全体の実際費用
            # -------------------------

            trip.final_actual_total = (
                calculate_trip_actual_total(
                    trip
                )
            )

        # =====================================
        # 入力条件に矛盾がある場合
        # 検索結果を表示しない
        # =====================================

        if self.filter_errors:

            return []

        # =====================================
        # 旅行日数で絞り込み
        #
        # 最低のみ
        # → その日数以上
        #
        # 最高のみ
        # → その日数以下
        # =====================================

        if min_days is not None:

            trip_list = [
                trip
                for trip in trip_list
                if trip.trip_days
                >= min_days
            ]

        if max_days is not None:

            trip_list = [
                trip
                for trip in trip_list
                if trip.trip_days
                <= max_days
            ]

        # =====================================
        # 費用で絞り込み
        #
        # 費用条件が指定されている場合
        # 費用未登録Tripは表示しない
        # =====================================

        if (
            min_cost is not None
            or max_cost is not None
        ):

            trip_list = [
                trip
                for trip in trip_list
                if (
                    trip.final_actual_total
                    is not None
                )
            ]

        if min_cost is not None:

            trip_list = [
                trip
                for trip in trip_list
                if (
                    trip.final_actual_total
                    >= min_cost
                )
            ]

        if max_cost is not None:

            trip_list = [
                trip
                for trip in trip_list
                if (
                    trip.final_actual_total
                    <= max_cost
                )
            ]

        # =====================================
        # 並び順
        # =====================================

        sort = self.request.GET.get(
            "sort",
            "new",
        )

        # -------------------------
        # 古い順
        # -------------------------

        if sort == "old":

            trip_list.sort(
                key=lambda trip: (
                    trip.updated_at
                )
            )

        # -------------------------
        # 費用が安い順
        #
        # 費用未登録は最後
        # -------------------------

        elif sort == "cost_asc":

            trip_list.sort(
                key=lambda trip: (
                    trip.final_actual_total
                    is None,
                    (
                        trip.final_actual_total
                        if trip.final_actual_total
                        is not None
                        else 0
                    ),
                )
            )

        # -------------------------
        # 費用が高い順
        #
        # 費用未登録は最後
        # -------------------------

        elif sort == "cost_desc":

            trip_list.sort(
                key=lambda trip: (
                    trip.final_actual_total
                    is None,
                    -(
                        trip.final_actual_total
                        if trip.final_actual_total
                        is not None
                        else 0
                    ),
                )
            )

        # -------------------------
        # 旅行期間が短い順
        # -------------------------

        elif sort == "days_asc":

            trip_list.sort(
                key=lambda trip: (
                    trip.trip_days
                )
            )

        # -------------------------
        # 旅行期間が長い順
        # -------------------------

        elif sort == "days_desc":

            trip_list.sort(
                key=lambda trip: (
                    trip.trip_days
                ),
                reverse=True,
            )

        # -------------------------
        # 新しい順
        # デフォルト
        # -------------------------

        else:

            trip_list.sort(
                key=lambda trip: (
                    trip.updated_at
                ),
                reverse=True,
            )

        return trip_list

    # =====================================
    # Templateへ渡す追加データ
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

        # カテゴリ選択欄で使用
        context["categories"] = (
            Category.objects.order_by(
                "name"
            )
        )

        # 入力条件のエラー
        context["filter_errors"] = getattr(
            self,
            "filter_errors",
            [],
        )

        # 並び順の選択肢
        context["sort_choices"] = [
            (
                "new",
                "新しい順",
            ),
            (
                "old",
                "古い順",
            ),
            (
                "cost_asc",
                "費用が安い順",
            ),
            (
                "cost_desc",
                "費用が高い順",
            ),
            (
                "days_asc",
                "旅行期間が短い順",
            ),
            (
                "days_desc",
                "旅行期間が長い順",
            ),
        ]

        return context


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

    # =====================================
    # Trip参考URL FormSet
    # =====================================

    def get_reference_url_formset(
        self,
        instance=None,
    ):

        if instance is None:

            instance = Trip()

        if self.request.method == "POST":

            return TripReferenceUrlFormSet(
                self.request.POST,
                instance=instance,
                prefix="reference_urls",
            )

        return TripReferenceUrlFormSet(
            instance=instance,
            prefix="reference_urls",
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

        if (
            "reference_url_formset"
            not in context
        ):

            form = context.get(
                "form"
            )

            instance = (
                form.instance
                if form is not None
                else Trip()
            )

            context[
                "reference_url_formset"
            ] = (
                self.get_reference_url_formset(
                    instance=instance
                )
            )

        return context

    # =====================================
    # 保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        form.instance.user = (
            self.request.user
        )

        form.instance.status = "draft"

        reference_url_formset = (
            self.get_reference_url_formset(
                instance=form.instance
            )
        )

        # Tripフォームが有効でも、
        # 参考URLにエラーがあれば保存しない
        if not (
            reference_url_formset
            .is_valid()
        ):

            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    reference_url_formset=(
                        reference_url_formset
                    ),
                )
            )

        reference_url_items = (
            get_trip_reference_url_items(
                reference_url_formset
            )
        )

        with transaction.atomic():

            response = (
                super().form_valid(
                    form
                )
            )

            sync_trip_hashtags(
                self.object,
                form.cleaned_data.get(
                    "hashtags",
                    [],
                ),
            )

            sync_trip_reference_urls(
                self.object,
                reference_url_items,
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

        return (
            Trip.objects
            .filter(
                Q(user=self.request.user)
                | Q(
                    status="completed",
                    is_public=True,
                )
            )
            .prefetch_related(
                "reference_urls",
                "trip_expenses__reference_urls",
                "days__reference_urls",
                "days__spots__reference_urls",
            )
            .distinct()
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

    def is_owner(self):

        return (
            self.object.user
            == self.request.user
        )

    # =====================================
    # Trip全体編集モードか
    # =====================================

    def is_edit_mode(self):

        return (
            self.is_owner()
            and self.request.GET.get("edit")
            == "1"
        )

    # =====================================
    # Trip全体費用を新しく追加できるか
    #
    # 作成中・出発待ち・旅中
    # → 今までどおり追加可能
    #
    # 旅完了
    # → Trip全体編集時のみ追加可能
    # =====================================

    def can_add_trip_expense(self):

        if not self.is_owner():

            return False

        if self.object.status != "completed":

            return True

        return self.is_edit_mode()

    # =====================================
    # Trip全体費用1件を編集できるか
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

        if not self.is_owner():

            return False

        if self.object.status == "completed":

            return self.is_edit_mode()

        return True

    # =====================================
    # Trip全体費用を並び替えできるか
    #
    # 基本的には編集可否と同じ条件にする
    # =====================================

    def can_move_trip_expense(
        self,
        trip_expense,
    ):

        return self.can_edit_trip_expense(
            trip_expense
        )

    # =====================================
    # Trip全体費用参考URL FormSet
    # =====================================

    def get_new_trip_expense_reference_url_formset(
        self,
        data=None,
    ):

        instance = TripExpense(
            trip=self.object
        )

        return TripExpenseReferenceUrlFormSet(
            data,
            instance=instance,
            prefix=(
                "expense_reference_urls_new"
            ),
        )

    def get_trip_expense_reference_url_formset(
        self,
        trip_expense,
        data=None,
    ):

        return TripExpenseReferenceUrlFormSet(
            data,
            instance=trip_expense,
            prefix=(
                "expense_reference_urls_"
                f"{trip_expense.trip_expense_id}"
            ),
        )

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

        url = get_trip_detail_url(
            self.object,
            edit_mode=self.is_edit_mode(),
        )

        if expense_id is not None:

            url += (
                f"#trip-expense-"
                f"{expense_id}"
            )

        else:

            url += "#trip-expenses"

        return url

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

        context["is_owner"] = (
            self.is_owner()
        )

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

        editing_expense_id = kwargs.get(
            "editing_expense_id"
        )

        editing_reference_url_formset = (
            kwargs.get(
                "editing_reference_url_formset"
            )
        )

        editing_expense_form = kwargs.get(
            "editing_expense_form"
        )

        # -------------------------
        # Trip全体費用1件ごとの
        # 編集可否・参考URL FormSetを設定
        # -------------------------

        for trip_expense in trip_expenses:

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

            # 通常は未バインドFormSet
            trip_expense.reference_url_formset = (
                None
            )

            trip_expense.edit_form = None

            if trip_expense.can_edit:

                if (
                    editing_expense_id
                    == trip_expense.trip_expense_id
                    and editing_reference_url_formset
                    is not None
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
                    and editing_expense_form
                    is not None
                ):

                    trip_expense.edit_form = (
                        editing_expense_form
                    )

                else:

                    trip_expense.edit_form = (
                        TripExpenseForm(
                            instance=trip_expense
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
        # 新規Trip全体費用用
        # 参考URL FormSet
        # -------------------------

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

        # -------------------------
        # Trip参考URL
        # -------------------------

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
        # Trip全体の訪問ルート
        #
        # Dayの日付順
        # ↓
        # そのDay内のlocation_order順
        #
        # 連続して同じ訪問先が続く場合は
        # 1回だけ表示する
        #
        # 例：
        # 東京（9/17）
        # ↓
        # 仁川（9/17）
        # ↓
        # アルマトイ（9/18）
        # =====================================

        trip_route = []

        route_days = (
            self.object.days
            .order_by(
                "day_order"
            )
        )

        previous_location_id = None

        for route_day in route_days:

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

                # -------------------------
                # 前の訪問先と同じ場合は
                # 連続重複として表示しない
                # -------------------------

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
        # 費用計算
        # =====================================

        # -------------------------
        # Trip全体費用
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
        # Trip全体費用
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
            # スケジュールの並び順
            #
            # 開始時間がある場合
            # → start_timeの早い順
            #
            # 開始時間が未設定の場合
            # → 最後に表示
            #
            # 同じ開始時間・時間未定の場合
            # → spot_order順
            # =====================================

            day.spots_sorted = (
                day.spots.order_by(
                    F("start_time").asc(
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
        #
        # 共通関数を使用して、
        # 詳細画面と公開Trip一覧・検索で
        # 同じ計算方法を使う
        # =====================================

        final_actual_total = (
            calculate_trip_actual_total(
                self.object
            )
        )

        has_final_actual_cost = (
            final_actual_total is not None
        )

        context[
            "is_manual_total_cost"
        ] = (
            self.object.total_cost
            is not None
        )

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
    # Trip詳細からTrip全体費用を操作
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

        if not self.is_owner():

            return redirect(
                get_trip_detail_url(
                    self.object
                )
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

        # =================================
        # 並び替え
        # =================================

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
                    ""
                )
            )

            return self.move_trip_expense(
                trip_expense,
                direction,
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
        request
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

        # =================================
        # 新規全体費用の参考URL FormSet
        #
        # HTML側がまだ旧版でも動くように、
        # management_formがPOSTされている時だけ
        # URL FormSetを保存対象にする
        # =================================

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
                reference_url_formset.is_valid()
            )

        else:

            reference_url_formset = (
                self
                .get_new_trip_expense_reference_url_formset()
            )

            reference_urls_valid = True

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

                if max_order is None:

                    max_order = 0

                trip_expense.expense_order = (
                    max_order + 1
                )

                trip_expense.save()

                # -------------------------
                # 参考URL
                # -------------------------

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
                instance=trip_expense,
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

        # =================================
        # 既存全体費用の参考URL FormSet
        #
        # 「実際支払額だけ登録」の簡易フォームは
        # URL FormSetをPOSTしないため、
        # management_formがある場合だけ
        # 参考URLを更新する
        # =================================

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
                reference_url_formset.is_valid()
            )

        else:

            reference_url_formset = (
                self
                .get_trip_expense_reference_url_formset(
                    trip_expense
                )
            )

            reference_urls_valid = True

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

        # ---------------------------------
        # エラー時は詳細画面へ戻し、
        # 該当費用の入力内容とURLエラーを保持
        # ---------------------------------

        context = self.get_context_data(
            editing_expense_id=(
                trip_expense.trip_expense_id
            ),
            editing_expense_form=(
                expense_form
            ),
            editing_reference_url_formset=(
                reference_url_formset
            ),
        )

        return self.render_to_response(
            context
        )

    # =====================================
    # Trip全体費用並び替え
    #
    # expense_orderそのものを入れ替える
    # Dayのように中身を交換する必要はない
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

                current_index = index
                break

        if current_index is None:

            return redirect(
                self.get_trip_expense_return_url()
            )

        if direction == "up":

            target_index = (
                current_index - 1
            )

        else:

            target_index = (
                current_index + 1
            )

        # 一番上でさらに上、
        # 一番下でさらに下へ動かそうとした場合
        if (
            target_index < 0
            or target_index
            >= len(ordered_expenses)
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
            trip_expense.expense_order
        )

        target_order = (
            target_expense.expense_order
        )

        # 万一expense_orderが同値になっていても
        # 並び替え後に順序が確実に変わるようにする
        if current_order == target_order:

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

            # 正規化後にもう一度取得して処理
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

            if direction == "up":

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
                >= len(ordered_expenses)
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
                trip_expense.expense_order
            )

            target_order = (
                target_expense.expense_order
            )

        # unique制約が将来付いても安全に交換できるよう、
        # 一時的に未使用の最大値+1へ退避してから入れ替える
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

    # =====================================
    # Trip参考URL FormSet
    # =====================================

    def get_reference_url_formset(self):

        if self.request.method == "POST":

            return TripReferenceUrlFormSet(
                self.request.POST,
                instance=self.object,
                prefix="reference_urls",
            )

        return TripReferenceUrlFormSet(
            instance=self.object,
            prefix="reference_urls",
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

        if (
            "reference_url_formset"
            not in context
        ):

            context[
                "reference_url_formset"
            ] = (
                self.get_reference_url_formset()
            )

        return context

    # =====================================
    # 保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        reference_url_formset = (
            self.get_reference_url_formset()
        )

        # Tripフォームが有効でも、
        # 参考URLにエラーがあれば保存しない
        if not (
            reference_url_formset
            .is_valid()
        ):

            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    reference_url_formset=(
                        reference_url_formset
                    ),
                )
            )

        reference_url_items = (
            get_trip_reference_url_items(
                reference_url_formset
            )
        )

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

        # =====================================
        # 期間短縮で記入済みDayが削除対象になる場合
        #
        # Trip本体だけでなく、
        # ハッシュタグ・参考URLも
        # セッションへ一時保存する
        # =====================================

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

                "reference_urls": (
                    reference_url_items
                ),
            }

            return redirect(
                "trip_period_confirm",
                pk=self.object.trip_id,
            )

        with transaction.atomic():

            response = (
                super().form_valid(
                    form
                )
            )

            sync_trip_hashtags(
                self.object,
                hashtag_names,
            )

            sync_trip_reference_urls(
                self.object,
                reference_url_items,
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

                sync_trip_reference_urls(
                    trip,
                    pending_data.get(
                        "reference_urls",
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