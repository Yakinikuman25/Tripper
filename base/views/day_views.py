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
from django.views.generic import UpdateView

from base.models import (
    Day,
    Location,
    Spot,
    DayExpense,
    DayReferenceUrl,
)

from base.models.day_models import DayLocation

from base.forms import (
    DayForm,
    DayRecordForm,
    DayExpenseFormSet,
    DayReferenceUrlFormSet,
)


# =========================================
# Day参考URL FormSetから
# 保存対象データを取り出す関数
# =========================================

def get_day_reference_url_items(
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
# Day参考URLを保存・整理する関数
#
# 現在の参考URLを一度削除して、
# 画面に残っているURLを
# 表示順どおりに作り直す
# =========================================

def sync_day_reference_urls(
    day,
    reference_url_items,
):

    day.reference_urls.all().delete()

    for url_order, item in enumerate(
        reference_url_items,
        start=1,
    ):

        DayReferenceUrl.objects.create(
            day=day,
            title=item.get(
                "title",
                "",
            ),
            url=item["url"],
            url_order=url_order,
        )


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
# ・Spot
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

        # Trip全体編集モードを維持
        if (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        ):

            url += "?edit=1"

        # 入れ替え後に移動した内容のDay位置へ戻る
        url += f"#day-{day.day_id}"

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

        direction = request.POST.get(
            "direction"
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

        # 最初のDayで↑、
        # 最後のDayで↓を押した場合
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

            # -------------------------
            # Day本体の値を退避
            # -------------------------

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
                "title": target_day.title,
                "memo": target_day.memo,
                "content": (
                    target_day.content
                ),
                "media": (
                    target_day.media.name
                    if target_day.media
                    else ""
                ),
                "budget": target_day.budget,
                "actual_cost": (
                    target_day.actual_cost
                ),
            }

            # -------------------------
            # DayLocationを退避
            #
            # Locationだけでなく
            # 訪問順も一緒に保持する
            # -------------------------

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

            # -------------------------
            # Day参考URLを退避
            # -------------------------

            day_reference_url_ids = list(
                day.reference_urls.values_list(
                    "pk",
                    flat=True,
                )
            )

            target_reference_url_ids = list(
                target_day.reference_urls.values_list(
                    "pk",
                    flat=True,
                )
            )

            # -------------------------
            # Spotを退避
            # -------------------------

            day_spot_ids = list(
                day.spots.values_list(
                    "pk",
                    flat=True,
                )
            )

            target_spot_ids = list(
                target_day.spots.values_list(
                    "pk",
                    flat=True,
                )
            )

            # -------------------------
            # Day費用明細を退避
            # -------------------------

            day_expense_ids = list(
                day.day_expenses.values_list(
                    "pk",
                    flat=True,
                )
            )

            target_expense_ids = list(
                target_day.day_expenses.values_list(
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
                target_day_data["title"]
            )

            day.memo = (
                target_day_data["memo"]
            )

            day.content = (
                target_day_data["content"]
            )

            day.media = (
                target_day_data["media"]
            )

            day.budget = (
                target_day_data["budget"]
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
                day_data["title"]
            )

            target_day.memo = (
                day_data["memo"]
            )

            target_day.content = (
                day_data["content"]
            )

            target_day.media = (
                day_data["media"]
            )

            target_day.budget = (
                day_data["budget"]
            )

            target_day.actual_cost = (
                day_data["actual_cost"]
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
                    pk__in=day_reference_url_ids
                ).update(
                    day=target_day
                )

            if target_reference_url_ids:

                DayReferenceUrl.objects.filter(
                    pk__in=target_reference_url_ids
                ).update(
                    day=day
                )

            # =====================================
            # Spotを交換
            # =====================================

            if day_spot_ids:

                Spot.objects.filter(
                    pk__in=day_spot_ids
                ).update(
                    day=target_day
                )

            if target_spot_ids:

                Spot.objects.filter(
                    pk__in=target_spot_ids
                ).update(
                    day=day
                )

            # =====================================
            # Day費用明細を交換
            # =====================================

            if day_expense_ids:

                DayExpense.objects.filter(
                    pk__in=day_expense_ids
                ).update(
                    day=target_day
                )

            if target_expense_ids:

                DayExpense.objects.filter(
                    pk__in=target_expense_ids
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


# =========================================
# Day編集
#
# 旅行の「計画」を編集する
#
# ・Dayタイトル
# ・1日の予算
# ・訪問先
# ・メモ
# ・参考URL
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

    # =====================================
    # Day参考URL FormSet
    # =====================================

    def get_reference_url_formset(self):

        if self.request.method == "POST":

            return DayReferenceUrlFormSet(
                self.request.POST,
                instance=self.object,
                prefix="reference_urls",
            )

        return DayReferenceUrlFormSet(
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

        context = super().get_context_data(
            **kwargs
        )

        context["trip"] = self.trip

        # =====================================
        # Day参考URL
        # =====================================

        if (
            "reference_url_formset"
            not in context
        ):

            context[
                "reference_url_formset"
            ] = (
                self.get_reference_url_formset()
            )

        # =====================================
        # 現在のDayに登録されている
        # 訪問先を国ごとにまとめる
        # =====================================

        location_groups = {}

        day_locations = (
            self.object
            .day_locations
            .select_related(
                "location"
            )
            .order_by(
                "location_order"
            )
        )

        for day_location in day_locations:

            location = (
                day_location.location
            )

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
        # 前日の最後の訪問先
        #
        # 現在のDayに訪問先がまだない場合のみ、
        # day_edit.html側で初期値として使用する
        # =====================================

        context[
            "previous_day_last_location"
        ] = None

        if not day_locations.exists():

            previous_day = (
                Day.objects
                .filter(
                    trip=self.trip,
                    day_order__lt=(
                        self.object.day_order
                    ),
                )
                .order_by(
                    "-day_order"
                )
                .first()
            )

            if previous_day is not None:

                previous_day_location = (
                    previous_day
                    .day_locations
                    .select_related(
                        "location"
                    )
                    .order_by(
                        "-location_order"
                    )
                    .first()
                )

                if (
                    previous_day_location
                    is not None
                ):

                    context[
                        "previous_day_last_location"
                    ] = (
                        previous_day_location.location
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

    def form_valid(
        self,
        form
    ):

        # ---------------------------------
        # Day参考URL FormSet
        # ---------------------------------

        reference_url_formset = (
            self.get_reference_url_formset()
        )

        if not (
            reference_url_formset.is_valid()
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
            get_day_reference_url_items(
                reference_url_formset
            )
        )

        # ---------------------------------
        # 訪問先
        # ---------------------------------

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

                        return self.render_to_response(
                            self.get_context_data(
                                form=form,
                                reference_url_formset=(
                                    reference_url_formset
                                ),
                            )
                        )

                    registered_locations.add(
                        location_key
                    )

                    location_data.append(
                        location_key
                    )

        # =====================================
        # Day本体・訪問先・参考URLを
        # まとめて保存
        # =====================================

        with transaction.atomic():

            response = super().form_valid(
                form
            )

            # -------------------------
            # 現在のDayLocationを
            # 一度すべて削除
            # -------------------------

            self.object.day_locations.all().delete()

            # -------------------------
            # 入力された順番で
            # DayLocationを登録
            #
            # 1件目 → location_order = 1
            # 2件目 → location_order = 2
            # -------------------------

            for location_order, (
                country,
                region,
            ) in enumerate(
                location_data,
                start=1,
            ):

                location, created = (
                    Location.objects.get_or_create(
                        trip=self.trip,
                        country=country,
                        region=region,
                    )
                )

                DayLocation.objects.create(
                    day=self.object,
                    location=location,
                    location_order=(
                        location_order
                    ),
                )

            # -------------------------
            # どのDayLocationからも
            # 使われなくなったLocationを削除
            # -------------------------

            self.trip.locations.filter(
                day_locations__isnull=True
            ).delete()

            # -------------------------
            # Day参考URLを保存
            # -------------------------

            sync_day_reference_urls(
                self.object,
                reference_url_items,
            )

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

            return (
                reverse(
                    "trip_detail",
                    kwargs={
                        "pk": self.trip.trip_id,
                    },
                )
                + f"#day-{self.object.day_id}"
            )

        # -------------------------
        # 出発待ち・旅中・旅完了
        # → Trip全体編集モードへ戻る
        # → 編集したDay位置まで移動する
        # -------------------------

        return (
            reverse(
                "trip_detail",
                kwargs={
                    "pk": self.trip.trip_id,
                },
            )
            + f"?edit=1#day-{self.object.day_id}"
        )


# =========================================
# Dayリセット
#
# Day編集画面で扱う「計画情報」だけを
# 初期状態へ戻す
#
# リセットするもの
# ・タイトル
# ・訪問先
# ・メモ
# ・1日の予算
# ・Day参考URL
#
# リセットしないもの
# ・日付
# ・Day番号
# ・Spot
# ・旅の記録
# ・写真
# ・実際の合計費用
# ・Day費用明細
# =========================================

class DayResetView(
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

        # -------------------------
        # Trip全体編集モードを維持
        # -------------------------

        if (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        ):

            url += "?edit=1"

        # -------------------------
        # リセットしたDay位置まで移動
        # -------------------------

        url += f"#day-{day.day_id}"

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
        # リセット可能か確認
        #
        # 作成中
        # → リセット可能
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
        # Day計画情報をリセット
        # =====================================

        with transaction.atomic():

            # -------------------------
            # Day本体
            # -------------------------

            day.title = ""
            day.memo = ""
            day.budget = None

            day.save(
                update_fields=[
                    "title",
                    "memo",
                    "budget",
                ]
            )

            # -------------------------
            # このDayの訪問先を削除
            # -------------------------

            day.day_locations.all().delete()

            # -------------------------
            # このDayの参考URLを削除
            # -------------------------

            day.reference_urls.all().delete()

            # -------------------------
            # どのDayLocationからも
            # 使われなくなったLocationを削除
            # -------------------------

            trip.locations.filter(
                day_locations__isnull=True
            ).delete()

        # =====================================
        # リセットしたDay位置へ戻る
        # =====================================

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
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

        # -------------------------
        # 操作したDay位置まで移動する
        # -------------------------
        url += f"#day-{day.day_id}"

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

        action = request.POST.get(
            "action"
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

            if not self.can_delete_record_item(
                request,
                day,
                trip,
            ):

                return redirect(
                    self.get_return_url(
                        trip,
                        day,
                        request,
                    )
                )

            if action == "delete_day_media":

                return self.delete_media(
                    request,
                    day,
                    trip,
                )

            if action == "delete_day_content":

                return self.delete_content(
                    request,
                    day,
                    trip,
                )

            if action == "delete_day_actual_cost":

                return self.delete_actual_cost(
                    request,
                    day,
                    trip,
                )

            if action == "delete_day_expense":

                return self.delete_expense(
                    request,
                    day,
                    trip,
                )

        # =====================================
        # 未登録になっている旅の記録項目を
        # 個別に再登録
        #
        # completedでは edit_mode=1 のときだけ可能
        # 登録済みの項目は上書きしない
        # =====================================

        save_item_actions = (
            "save_day_media",
            "save_day_content",
            "save_day_actual_cost",
            "save_day_expenses",
        )

        if action in save_item_actions:

            if not self.can_save_record_item(
                request,
                day,
                trip,
            ):

                return redirect(
                    self.get_return_url(
                        trip,
                        day,
                        request,
                    )
                )

            if action == "save_day_media":

                return self.save_media(
                    request,
                    day,
                    trip,
                )

            if action == "save_day_content":

                return self.save_content(
                    request,
                    day,
                    trip,
                )

            if action == "save_day_actual_cost":

                return self.save_actual_cost(
                    request,
                    day,
                    trip,
                )

            if action == "save_day_expenses":

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

        # -------------------------
        # 旅の記録を保存
        #
        # 新HTMLではDay費用明細も
        # この保存処理でまとめて保存する
        # -------------------------
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

        if day.actual_cost is not None:

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

        if uploaded_media is None:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # DayRecordFormのmediaフィールドを使って
        # ファイル形式・モデル側の検証を行う
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

            day.media = cleaned_media

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

        if day.actual_cost is not None:

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        actual_cost = request.POST.get(
            "actual_cost"
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

        if cleaned_actual_cost is None:

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

        # -------------------------
        # 削除指定された既存費用を削除
        # -------------------------

        for deleted_form in (
            expense_formset.deleted_forms
        ):

            if (
                deleted_form.instance
                and deleted_form.instance.pk
            ):

                deleted_form.instance.delete()

        # -------------------------
        # 画面に残っている順番で保存
        # -------------------------

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

            # 完全に空欄の追加フォームは保存しない
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
    # そのため、写真や感想が登録済みでも
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

        if expense_formset.is_valid():

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
            prefix=f"day_{day.day_id}",
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

                # -------------------------
                # 写真・感想・実際の合計費用
                # -------------------------

                record_form.save()

                # -------------------------
                # Day費用明細
                # -------------------------

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