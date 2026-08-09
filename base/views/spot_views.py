from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
)

from base.models import Day, Spot
from base.forms import SpotForm


# Spot作成
class SpotCreateView(LoginRequiredMixin, CreateView):

    model = Spot
    form_class = SpotForm
    template_name = "pages/spot_create.html"

    def dispatch(self, request, *args, **kwargs):

        self.day = get_object_or_404(
            Day,
            pk=self.kwargs["day_pk"],
            trip__user=request.user,
        )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def form_valid(self, form):

        # 対象Dayを自動設定
        form.instance.day = self.day

        # spot_orderを自動採番
        last_spot = self.day.spots.order_by(
            "-spot_order"
        ).first()

        if last_spot:

            form.instance.spot_order = (
                last_spot.spot_order + 1
            )

        else:

            form.instance.spot_order = 1

        return super().form_valid(
            form
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["day"] = self.day
        context["trip"] = self.day.trip

        return context

    def get_success_url(self):

        return reverse_lazy(
            "trip_detail",
            kwargs={
                "pk": self.day.trip.trip_id,
            },
        )


# Spot編集
class SpotUpdateView(LoginRequiredMixin, UpdateView):

    model = Spot
    form_class = SpotForm
    template_name = "pages/spot_edit.html"

    def get_queryset(self):

        return Spot.objects.filter(
            day__trip__user=self.request.user
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["day"] = self.object.day
        context["trip"] = self.object.day.trip

        return context

    def get_success_url(self):

        return reverse_lazy(
            "trip_detail",
            kwargs={
                "pk": self.object.day.trip.trip_id,
            },
        )


# Spot削除
class SpotDeleteView(LoginRequiredMixin, DeleteView):

    model = Spot
    template_name = "pages/spot_delete.html"

    def get_queryset(self):

        return Spot.objects.filter(
            day__trip__user=self.request.user
        )

    def get_success_url(self):

        return reverse_lazy(
            "trip_detail",
            kwargs={
                "pk": self.object.day.trip.trip_id,
            },
        )
    