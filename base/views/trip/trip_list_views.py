from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from base.models import (
    Trip,
    Category,
)

from .trip_services import (
    sync_trip_status,
    prepare_trip_card_data,
)


# =========================================
# Trip一覧
# =========================================

class TripListView(
    LoginRequiredMixin,
    ListView,
):

    model = Trip

    template_name = (
        "pages/trip/trip_list.html"
    )

    context_object_name = "trips"


    # =====================================
    # ログインユーザー本人の
    # Trip一覧を取得
    # =====================================

    def get_queryset(
        self,
    ):

        trips = (
            Trip.objects
            .filter(
                user=self.request.user
            )
            .select_related(
                "category",
            )
            .prefetch_related(
                "locations",
                "trip_hashtags__hashtag",
            )
            .order_by(
                "-created_at"
            )
        )


        for trip in trips:


            # =====================================
            # 現在の日付に合わせて
            # Tripステータスを更新
            # =====================================

            sync_trip_status(
                trip
            )


            # =====================================
            # 共通Tripカード用データ
            #
            # ・旅行日数
            # ・国ごとにまとめた訪問先
            # =====================================

            prepare_trip_card_data(
                trip
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
        "pages/trip/public_trip.html"
    )

    context_object_name = (
        "public_trips"
    )


    # =====================================
    # 1ページに表示する公開Trip数
    # =====================================

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

        value = (
            self.request.GET.get(
                name,
                "",
            )
            .strip()
        )


        if not value:

            return None


        try:

            number = int(
                value
            )

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

    def get_queryset(
        self,
    ):

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
                "days__schedules",
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

        keyword = (
            self.request.GET.get(
                "q",
                "",
            )
            .strip()
        )


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


        if (
            category_id
            is not None
        ):

            trips = trips.filter(
                category_id=category_id
            )



        # =====================================
        # ハッシュタグ絞り込み
        #
        # 入力された文字を含む
        # ハッシュタグを対象にする
        # =====================================

        hashtag = (
            self.request.GET.get(
                "hashtag",
                "",
            )
            .strip()
        )


        # =====================================
        # 先頭に#が入力されても
        # 検索できるようにする
        # =====================================

        hashtag = (
            hashtag.lstrip("#")
        )


        if hashtag:

            trips = trips.filter(
                trip_hashtags__hashtag__name__icontains=(
                    hashtag
                )
            )



        # =====================================
        # M2M・訪問先検索による
        # 重複を除外
        # =====================================

        trips = (
            trips.distinct()
        )



        # =====================================
        # 旅行日数条件
        # =====================================

        min_days = (
            self.parse_int_param(
                "min_days",
                minimum=1,
            )
        )

        max_days = (
            self.parse_int_param(
                "max_days",
                minimum=1,
            )
        )


        if (
            min_days is not None
            and max_days is not None
            and min_days > max_days
        ):

            self.filter_errors.append(
                (
                    "旅行日数は、最低日数を"
                    "最高日数以下にしてください。"
                )
            )



        # =====================================
        # 費用条件
        # =====================================

        min_cost = (
            self.parse_int_param(
                "min_cost",
                minimum=0,
            )
        )

        max_cost = (
            self.parse_int_param(
                "max_cost",
                minimum=0,
            )
        )


        if (
            min_cost is not None
            and max_cost is not None
            and min_cost > max_cost
        ):

            self.filter_errors.append(
                (
                    "費用は、最低費用を"
                    "最高費用以下にしてください。"
                )
            )



        # =====================================
        # QuerySetをリスト化
        # =====================================

        trip_list = list(
            trips
        )



        # =====================================
        # 共通Tripカード用データを設定
        #
        # ・旅行日数
        # ・国ごとにまとめた訪問先
        # ・実費合計
        # =====================================

        for trip in trip_list:

            prepare_trip_card_data(
                trip,
                include_actual_total=True,
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

        if (
            min_days
            is not None
        ):

            trip_list = [
                trip
                for trip in trip_list
                if (
                    trip.trip_days
                    >= min_days
                )
            ]


        if (
            max_days
            is not None
        ):

            trip_list = [
                trip
                for trip in trip_list
                if (
                    trip.trip_days
                    <= max_days
                )
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


        if (
            min_cost
            is not None
        ):

            trip_list = [
                trip
                for trip in trip_list
                if (
                    trip.final_actual_total
                    >= min_cost
                )
            ]


        if (
            max_cost
            is not None
        ):

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

        sort = (
            self.request.GET.get(
                "sort",
                "new",
            )
        )



        # =====================================
        # 古い順
        # =====================================

        if sort == "old":

            trip_list.sort(
                key=lambda trip: (
                    trip.updated_at
                )
            )



        # =====================================
        # 費用が安い順
        #
        # 費用未登録は最後
        # =====================================

        elif sort == "cost_asc":

            trip_list.sort(
                key=lambda trip: (
                    (
                        trip.final_actual_total
                        is None
                    ),
                    (
                        trip.final_actual_total
                        if (
                            trip.final_actual_total
                            is not None
                        )
                        else 0
                    ),
                )
            )



        # =====================================
        # 費用が高い順
        #
        # 費用未登録は最後
        # =====================================

        elif sort == "cost_desc":

            trip_list.sort(
                key=lambda trip: (
                    (
                        trip.final_actual_total
                        is None
                    ),
                    -(
                        trip.final_actual_total
                        if (
                            trip.final_actual_total
                            is not None
                        )
                        else 0
                    ),
                )
            )



        # =====================================
        # 旅行期間が短い順
        # =====================================

        elif sort == "days_asc":

            trip_list.sort(
                key=lambda trip: (
                    trip.trip_days
                )
            )



        # =====================================
        # 旅行期間が長い順
        # =====================================

        elif sort == "days_desc":

            trip_list.sort(
                key=lambda trip: (
                    trip.trip_days
                ),
                reverse=True,
            )



        # =====================================
        # 新しい順
        # デフォルト
        # =====================================

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



        # =====================================
        # カテゴリ選択欄で使用
        # =====================================

        context[
            "categories"
        ] = (
            Category.objects
            .order_by(
                "name"
            )
        )



        # =====================================
        # 入力条件のエラー
        # =====================================

        context[
            "filter_errors"
        ] = getattr(
            self,
            "filter_errors",
            [],
        )



        # =====================================
        # 並び順の選択肢
        # =====================================

        context[
            "sort_choices"
        ] = [
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