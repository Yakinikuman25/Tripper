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

            my_trips = (
                Trip.objects.filter(
                    user=self.request.user
                )
                .order_by("-created_at")[:5]
            )

        else:

            my_trips = []


        # -------------------------
        # 公開されている旅完了Trip
        # -------------------------

        public_trips = (
            Trip.objects.filter(
                status="completed",
                is_public=True,
            )
            .order_by("-created_at")[:5]
        )


        # -------------------------
        # Tripごとの訪問先を
        # 国ごとにまとめる
        # -------------------------

        for trip in my_trips:

            locations_by_country = {}

            for location in trip.locations.all():

                if location.country not in locations_by_country:

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


        for trip in public_trips:

            locations_by_country = {}

            for location in trip.locations.all():

                if location.country not in locations_by_country:

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


        context["my_trips"] = my_trips
        context["public_trips"] = public_trips

        return context