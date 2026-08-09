from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views import View
from django.views.generic import UpdateView

from base.models import Day, Location
from base.forms import (
    DayForm,
    DayRecordForm,
)


# Day基本情報編集
class DayUpdateView(LoginRequiredMixin, UpdateView):

    model = Day
    form_class = DayForm
    template_name = "pages/day_edit.html"

    def dispatch(self, request, *args, **kwargs):

        self.day = get_object_or_404(
            Day,
            pk=self.kwargs["pk"],
            trip__user=request.user,
        )

        self.trip = self.day.trip

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def form_valid(self, form):

        # 国を複数取得
        countries = self.request.POST.getlist(
            "countries"
        )

        # 保存予定の国・地域
        location_data = []

        # 同じDay内の重複確認用
        registered_locations = set()

        for index, country in enumerate(countries):

            country = country.strip()

            # その国に対応する地域を取得
            regions = self.request.POST.getlist(
                f"regions_{index}"
            )

            for region in regions:

                region = region.strip()

                if country and region:

                    location_key = (
                        country,
                        region,
                    )

                    # -------------------------
                    # 同じDay内に
                    # 同一の国・地域があるか確認
                    # -------------------------
                    if location_key in registered_locations:

                        form.add_error(
                            None,
                            (
                                f"「{country} / {region}」は"
                                "すでにこのDayに登録されています。"
                            )
                        )

                        return self.form_invalid(
                            form
                        )

                    registered_locations.add(
                        location_key
                    )

                    location_data.append(
                        location_key
                    )

        # -------------------------
        # 重複がなければDayを保存
        # -------------------------

        response = super().form_valid(
            form
        )

        # 現在のLocationとの関連をいったん外す
        self.object.locations.clear()

        # 国・地域を登録
        for country, region in location_data:

            location, created = (
                Location.objects.get_or_create(
                    trip=self.trip,
                    country=country,
                    region=region,
                )
            )

            self.object.locations.add(
                location
            )

        # どのDayからも使用されなくなったLocationを削除
        self.trip.locations.filter(
            days__isnull=True
        ).delete()

        return response

    def get_success_url(self):

        return reverse_lazy(
            "trip_detail",
            kwargs={
                "pk": self.trip.trip_id,
            },
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["trip"] = self.trip
        context["day"] = self.day

        # --------------------------------
        # 現在のDayに登録されている国・地域
        # --------------------------------

        location_groups = {}

        for location in self.day.locations.all():

            if location.country not in location_groups:

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

        # --------------------------------
        # このTripですでに登録されている
        # 国・地域を候補として取得
        # --------------------------------

        trip_location_groups = {}

        for location in self.trip.locations.all():

            if location.country not in trip_location_groups:

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


# Trip詳細画面からDayの写真・感想を保存
class DayRecordUpdateView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):

        day = get_object_or_404(
            Day,
            pk=self.kwargs["pk"],
            trip__user=request.user,
        )

        trip = day.trip

        today = timezone.localdate()

        # 作成中・出発待ちは記録不可
        if trip.status in (
            "draft",
            "planned",
        ):

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        # 旅中で未来のDayは記録不可
        if (
            trip.status == "traveling"
            and day.date > today
        ):

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        # traveling / completed 以外は記録不可
        if trip.status not in (
            "traveling",
            "completed",
        ):

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        form = DayRecordForm(
            request.POST,
            request.FILES,
            instance=day,
            prefix=f"day_{day.day_id}",
        )

        if form.is_valid():

            form.save()

        return redirect(
            "trip_detail",
            pk=trip.trip_id,
        )