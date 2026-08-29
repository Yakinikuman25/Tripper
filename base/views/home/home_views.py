from django.views.generic import TemplateView

from base.models import Trip


class HomeView(TemplateView):

    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # -------------------------
        # My Trip
        # -------------------------

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


        # -------------------------
        # 公開されている旅完了Trip
        # -------------------------

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


        # -------------------------
        # My Tripごとの訪問先を
        # 国ごとにまとめる
        # -------------------------

        for trip in my_trips:

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
        # 公開Tripごとの訪問先を
        # 国ごとにまとめる
        # -------------------------

        for trip in public_trips:

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
        # Context
        # -------------------------

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