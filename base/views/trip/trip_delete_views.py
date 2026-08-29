from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from base.models import Trip


# =========================================
# Trip削除
# =========================================

class TripDeleteView(
    LoginRequiredMixin,
    DeleteView,
):

    model = Trip

    template_name = (
        "pages/trip_delete.html"
    )

    # =====================================
    # ログインユーザー本人の
    # Tripのみ削除可能
    # =====================================

    def get_queryset(
        self,
    ):

        return Trip.objects.filter(
            user=self.request.user
        )

    # =====================================
    # 削除後
    #
    # My Trip一覧へ戻る
    # =====================================

    def get_success_url(
        self,
    ):

        return reverse_lazy(
            "trip_list"
        )