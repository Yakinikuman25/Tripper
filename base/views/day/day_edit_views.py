from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse
from django.views.generic import UpdateView

from base.models import (
    Day,
    Location,
    DayReferenceUrl,
)

from base.models.day_models import DayLocation

from base.forms import (
    DayForm,
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

        # =====================================
        # URLが空欄の追加フォームは
        # 保存しない
        # =====================================

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

    template_name = (
        "pages/day/day_edit.html"
    )

    # =====================================
    # 初期処理
    # =====================================

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        self.object = self.get_object()

        self.trip = (
            self.object.trip
        )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    # =====================================
    # ログインユーザー本人の
    # Dayだけ取得可能にする
    # =====================================

    def get_queryset(
        self,
    ):

        return Day.objects.filter(
            trip__user=self.request.user
        )

    # =====================================
    # Day参考URL FormSet
    # =====================================

    def get_reference_url_formset(
        self,
    ):

        if (
            self.request.method
            == "POST"
        ):

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

        context = (
            super().get_context_data(
                **kwargs
            )
        )

        context[
            "trip"
        ] = self.trip

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

        context[
            "location_groups"
        ] = location_groups

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

            if (
                previous_day
                is not None
            ):

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

        for location in (
            self.trip.locations.all()
        ):

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

        context[
            "trip_location_groups"
        ] = trip_location_groups

        return context

    # =====================================
    # Day編集保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        # =====================================
        # Day参考URL FormSet
        # =====================================

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

        # =====================================
        # 訪問先
        # =====================================

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

            country = (
                country.strip()
            )

            regions = (
                self.request.POST.getlist(
                    f"regions_{index}"
                )
            )

            for region in regions:

                region = (
                    region.strip()
                )

                if (
                    country
                    and region
                ):

                    location_key = (
                        country,
                        region,
                    )

                    # =====================================
                    # 同じDayに
                    # 同じ国・地域を重複登録しない
                    # =====================================

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

                        return (
                            self.render_to_response(
                                self.get_context_data(
                                    form=form,
                                    reference_url_formset=(
                                        reference_url_formset
                                    ),
                                )
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

            response = (
                super().form_valid(
                    form
                )
            )

            # =====================================
            # 現在のDayLocationを
            # 一度すべて削除
            # =====================================

            self.object.day_locations.all().delete()

            # =====================================
            # 入力された順番で
            # DayLocationを登録
            #
            # 1件目
            # → location_order = 1
            #
            # 2件目
            # → location_order = 2
            # =====================================

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

            # =====================================
            # どのDayLocationからも
            # 使われなくなったLocationを削除
            # =====================================

            self.trip.locations.filter(
                day_locations__isnull=True
            ).delete()

            # =====================================
            # Day参考URLを保存
            # =====================================

            sync_day_reference_urls(
                self.object,
                reference_url_items,
            )

        return response

    # =====================================
    # Day編集保存後
    # =====================================

    def get_success_url(
        self,
    ):

        # =====================================
        # 作成中
        # → 通常Trip詳細へ戻る
        # =====================================

        if (
            self.trip.status
            == "draft"
        ):

            return (
                reverse(
                    "trip_detail",
                    kwargs={
                        "pk": (
                            self.trip.trip_id
                        ),
                    },
                )
                + (
                    f"#day-"
                    f"{self.object.day_id}"
                )
            )

        # =====================================
        # 出発待ち・旅中・旅完了
        #
        # → Trip全体編集モードへ戻る
        # → 編集したDay位置まで移動する
        # =====================================

        return (
            reverse(
                "trip_detail",
                kwargs={
                    "pk": (
                        self.trip.trip_id
                    ),
                },
            )
            + (
                f"?edit=1"
                f"#day-"
                f"{self.object.day_id}"
            )
        )