from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.urls import reverse
from django.views.generic import UpdateView

from django_countries import countries
from django_countries.fields import Country

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
# 国コード → 国旗画像URL
#
# 例：
# JP → /static/flags/jp.gif
# KG → /static/flags/kg.gif
# KZ → /static/flags/kz.gif
# =========================================

def get_country_flag_url(
    country_code,
):

    country_code = (
        country_code
        or ""
    ).strip().upper()

    if (
        len(country_code) != 2
        or not country_code.isalpha()
    ):

        return ""

    return Country(
        country_code
    ).flag


# =========================================
# django-countriesの国一覧
#
# code
# → JP
#
# name
# → 日本
#
# flag
# → 国旗画像URL
# =========================================

def get_country_options():

    return [
        {
            "code": country_code,
            "name": str(country_name),
            "flag": get_country_flag_url(
                country_code
            ),
        }
        for country_code, country_name
        in countries
    ]


# =========================================
# 国コードと国名の対応表
# =========================================

def get_country_maps():

    country_code_to_name = {}

    country_name_to_code = {}

    for country_code, country_name in (
        countries
    ):

        country_name = str(
            country_name
        )

        country_code_to_name[
            country_code
        ] = country_name

        country_name_to_code[
            country_name
        ] = country_code

    return (
        country_code_to_name,
        country_name_to_code,
    )


# =========================================
# POSTされた国を
# ISO国コードへ変換する
#
# 国名
# 日本 → JP
#
# 国コード
# JP → JP
#
# 両方に対応する
# =========================================

def normalize_country_code(
    country_value,
):

    country_value = (
        country_value
        or ""
    ).strip()

    if not country_value:

        return None

    (
        country_code_to_name,
        country_name_to_code,
    ) = get_country_maps()

    # =====================================
    # 国コードで送信された場合
    #
    # 例：
    # KG
    # JP
    # =====================================

    country_code = (
        country_value.upper()
    )

    if (
        country_code
        in country_code_to_name
    ):

        return country_code

    # =====================================
    # 国名で送信された場合
    #
    # 例：
    # キルギス → KG
    # 日本     → JP
    # =====================================

    if (
        country_value
        in country_name_to_code
    ):

        return country_name_to_code[
            country_value
        ]

    # =====================================
    # 実在しない国
    # =====================================

    return None


# =========================================
# 国コードから表示用国名を取得
# =========================================

def get_country_name(
    country_code,
):

    (
        country_code_to_name,
        country_name_to_code,
    ) = get_country_maps()

    return (
        country_code_to_name.get(
            country_code,
            country_code,
        )
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

        self.object = (
            self.get_object()
        )

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

        return (
            Day.objects
            .filter(
                trip__user=(
                    self.request.user
                )
            )
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
        # 実在する国一覧
        #
        # 例：
        #
        # {
        #     "code": "KG",
        #     "name": "キルギス",
        #     "flag": "/static/flags/kg.gif",
        # }
        # =====================================

        context[
            "country_options"
        ] = (
            get_country_options()
        )

        # =====================================
        # 現在のDayに登録されている
        # 訪問先を国ごとにまとめる
        #
        # 表示用国名をキーにする
        #
        # 例：
        #
        # {
        #     "キルギス": [
        #         "カラコル",
        #         "ビシュケク",
        #     ]
        # }
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

        for day_location in (
            day_locations
        ):

            location = (
                day_location.location
            )

            country_code = (
                location.country.code
            )

            country_name = (
                get_country_name(
                    country_code
                )
            )

            if (
                country_name
                not in location_groups
            ):

                location_groups[
                    country_name
                ] = []

            if (
                location.region
                and location.region
                not in location_groups[
                    country_name
                ]
            ):

                location_groups[
                    country_name
                ].append(
                    location.region
                )

        context[
            "location_groups"
        ] = location_groups

        # =====================================
        # 前日の最後の訪問先
        #
        # 現在のDayに訪問先がまだない場合のみ
        # 初期値として使用する
        # =====================================

        context[
            "previous_day_last_location"
        ] = None

        context[
            "previous_day_last_location_data"
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

                    location = (
                        previous_day_location.location
                    )

                    context[
                        "previous_day_last_location"
                    ] = location

                    country_code = (
                        location.country.code
                    )

                    context[
                        "previous_day_last_location_data"
                    ] = {
                        "country_code": (
                            country_code
                        ),
                        "country_name": (
                            get_country_name(
                                country_code
                            )
                        ),
                        "country_flag": (
                            get_country_flag_url(
                                country_code
                            )
                        ),
                        "region": (
                            location.region
                        ),
                    }

        # =====================================
        # Trip全体で登録済みの
        # 訪問先候補
        #
        # 国名をキーにしたものと
        # ISO国コードをキーにしたものを
        # 両方作成する
        # =====================================

        trip_location_groups = {}

        trip_location_regions_by_code = {}

        for location in (
            self.trip.locations.all()
        ):

            country_code = (
                location.country.code
            )

            country_name = (
                get_country_name(
                    country_code
                )
            )

            # =====================================
            # 国名をキーにした候補
            # =====================================

            if (
                country_name
                not in trip_location_groups
            ):

                trip_location_groups[
                    country_name
                ] = []

            if (
                location.region
                and location.region
                not in trip_location_groups[
                    country_name
                ]
            ):

                trip_location_groups[
                    country_name
                ].append(
                    location.region
                )

            # =====================================
            # ISO国コードをキーにした候補
            #
            # 例：
            #
            # KG: [
            #     "カラコル",
            #     "ビシュケク",
            # ]
            # =====================================

            if (
                country_code
                not in trip_location_regions_by_code
            ):

                trip_location_regions_by_code[
                    country_code
                ] = []

            if (
                location.region
                and location.region
                not in trip_location_regions_by_code[
                    country_code
                ]
            ):

                trip_location_regions_by_code[
                    country_code
                ].append(
                    location.region
                )

        context[
            "trip_location_groups"
        ] = trip_location_groups

        context[
            "trip_location_regions_by_code"
        ] = (
            trip_location_regions_by_code
        )

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
        #
        # hiddenのcountriesには
        # 基本的にISO国コードが送られる
        #
        # 例：
        # JP
        # KG
        # =====================================

        posted_countries = (
            self.request.POST.getlist(
                "countries"
            )
        )

        location_data = []

        registered_locations = set()

        for index, country_value in enumerate(
            posted_countries
        ):

            country_value = (
                country_value
                or ""
            ).strip()

            regions = (
                self.request.POST.getlist(
                    f"regions_{index}"
                )
            )

            cleaned_regions = [
                (
                    region
                    or ""
                ).strip()
                for region
                in regions
                if (
                    region
                    and region.strip()
                )
            ]

            # =====================================
            # 国も地域も空欄
            # → 何も登録しない
            # =====================================

            if (
                not country_value
                and not cleaned_regions
            ):

                continue

            # =====================================
            # 地域が入力されているのに
            # 国が未選択
            # =====================================

            if (
                not country_value
                and cleaned_regions
            ):

                form.add_error(
                    None,
                    (
                        "地域を登録する場合は、"
                        "国を選択してください。"
                    ),
                )

                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        reference_url_formset=(
                            reference_url_formset
                        ),
                    )
                )

            # =====================================
            # 実在する国か確認
            #
            # 日本 → JP
            # KG   → KG
            #
            # 実在しない場合
            # → None
            # =====================================

            country_code = (
                normalize_country_code(
                    country_value
                )
            )

            if (
                country_code
                is None
            ):

                form.add_error(
                    None,
                    (
                        f"「{country_value}」は"
                        "登録できない国です。"
                        "候補から実在する国を"
                        "選択してください。"
                    ),
                )

                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        reference_url_formset=(
                            reference_url_formset
                        ),
                    )
                )

            country_name = (
                get_country_name(
                    country_code
                )
            )

            for region in (
                cleaned_regions
            ):

                location_key = (
                    country_code,
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
                            f"「{country_name} / "
                            f"{region}」"
                            "はすでにこのDayに"
                            "登録されています。"
                        ),
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
            # countryにはISO国コードを保存
            #
            # 日本
            # → JP
            #
            # キルギス
            # → KG
            # =====================================

            for location_order, (
                country_code,
                region,
            ) in enumerate(
                location_data,
                start=1,
            ):

                location, created = (
                    Location.objects.get_or_create(
                        trip=self.trip,
                        country=country_code,
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