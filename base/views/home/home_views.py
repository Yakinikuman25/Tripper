from django.views.generic import TemplateView

from base.models import Trip

from base.views.trip.trip_services import (
    prepare_trip_card_data,
    sync_trip_status,
)


class HomeView(TemplateView):

    template_name = "pages/home.html"


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
        # My Trip
        # =====================================

        if self.request.user.is_authenticated:

            my_trip_queryset = (
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


            my_trip_count = (
                my_trip_queryset.count()
            )


            my_trips = (
                my_trip_queryset[:3]
            )


        else:

            my_trips = []

            my_trip_count = 0



        # =====================================
        # 公開されている旅完了Trip
        # =====================================

        public_trip_queryset = (
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
            .order_by(
                "-created_at"
            )
        )


        public_trip_count = (
            public_trip_queryset.count()
        )


        public_trips = (
            public_trip_queryset[:6]
        )



        # =====================================
        # My Tripのカード表示用データを設定
        # =====================================

        for trip in my_trips:


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



        # =====================================
        # 公開Tripのカード表示用データを設定
        # =====================================

        for trip in public_trips:


            # =====================================
            # 共通Tripカード用データ
            #
            # ・旅行日数
            # ・国ごとにまとめた訪問先
            # ・実費合計
            # =====================================

            prepare_trip_card_data(
                trip,
                include_actual_total=True,
            )



        # =====================================
        # Context
        # =====================================

        context["my_trips"] = (
            my_trips
        )

        context["my_trip_count"] = (
            my_trip_count
        )

        context["public_trips"] = (
            public_trips
        )

        context["public_trip_count"] = (
            public_trip_count
        )


        return context