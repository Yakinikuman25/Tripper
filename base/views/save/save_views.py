from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.views import View
from django.views.generic import ListView

from base.models import (
    Trip,
    TripSave,
)


# =========================================
# Trip保存・保存解除
# =========================================

class TripSaveToggleView(
    LoginRequiredMixin,
    View,
):

    def post(
        self,
        request,
        pk,
    ):

        trip = get_object_or_404(
            Trip,
            pk=pk,
            status="completed",
            is_public=True,
        )

        # =====================================
        # 自分自身のTripは保存不可
        # =====================================

        if (
            trip.user
            == request.user
        ):

            return redirect(
                "trip_detail",
                pk=trip.pk,
            )

        trip_save = (
            TripSave.objects
            .filter(
                user=request.user,
                trip=trip,
            )
            .first()
        )

        # =====================================
        # 保存済み
        # → 保存解除
        # =====================================

        if trip_save:

            trip_save.delete()

        # =====================================
        # 未保存
        # → 保存
        # =====================================

        else:

            TripSave.objects.create(
                user=request.user,
                trip=trip,
            )

        return redirect(
            "trip_detail",
            pk=trip.pk,
        )


# =========================================
# 保存Trip一覧
# =========================================

class SavedTripListView(
    LoginRequiredMixin,
    ListView,
):

    model = Trip

    template_name = (
        "pages/trip/saved_trip_list.html"
    )

    context_object_name = "trips"

    paginate_by = 30

    # =====================================
    # ログインユーザーが保存した
    # 公開Tripのみ取得
    # =====================================

    def get_queryset(
        self,
    ):

        return (
            Trip.objects
            .filter(
                saves__user=(
                    self.request.user
                ),
                status="completed",
                is_public=True,
            )
            .select_related(
                "user",
                "category",
            )
            .prefetch_related(
                "locations",
                "trip_hashtags__hashtag",
            )
            .order_by(
                "-saves__created_at"
            )
        )