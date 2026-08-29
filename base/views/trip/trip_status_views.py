from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.utils import timezone
from django.views import View
from django.views.generic import UpdateView

from base.models import Trip

from base.forms import TripCompleteForm

from .trip_services import (
    sync_trip_status,
    get_trip_detail_url,
)


# =========================================
# Tripステータス変更
#
# ・作成中 → コース作成完了
# ・旅完了 → 旅中へ戻す
# =========================================

class TripStatusUpdateView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=request.user,
        )

        action = (
            request.POST.get(
                "action"
            )
        )

        # =====================================
        # コース作成完了
        # =====================================

        if (
            action
            == "complete_plan"
        ):

            # =====================================
            # 作成中Tripのみ
            # =====================================

            if (
                trip.status
                != "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            today = (
                timezone.localdate()
            )

            # =====================================
            # 旅行開始日前
            # → 出発待ち
            # =====================================

            if (
                today
                < trip.start_date
            ):

                trip.status = (
                    "planned"
                )

            # =====================================
            # 旅行開始日以降
            # → 旅中
            # =====================================

            else:

                trip.status = (
                    "traveling"
                )

            trip.save(
                update_fields=[
                    "status",
                ]
            )

            return redirect(
                get_trip_detail_url(
                    trip
                )
            )

        # =====================================
        # 旅完了から旅中へ戻す
        # =====================================

        if (
            action
            == "reopen_trip"
        ):

            # =====================================
            # 旅完了Tripのみ
            # =====================================

            if (
                trip.status
                != "completed"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            # =====================================
            # ステータスを旅中へ戻す
            # =====================================

            trip.status = (
                "traveling"
            )

            # =====================================
            # 旅中は非公開固定
            #
            # 代表写真・感想は削除しない
            # =====================================

            trip.is_public = False

            trip.save(
                update_fields=[
                    "status",
                    "is_public",
                ]
            )

            return redirect(
                get_trip_detail_url(
                    trip
                )
            )

        # =====================================
        # 想定外のactionの場合
        # Trip詳細へ戻る
        # =====================================

        return redirect(
            get_trip_detail_url(
                trip
            )
        )


# =========================================
# Trip完了・旅完了情報編集
# =========================================

class TripCompleteView(
    LoginRequiredMixin,
    UpdateView,
):

    model = Trip

    form_class = (
        TripCompleteForm
    )

    template_name = (
        "pages/trip/trip_complete.html"
    )

    # =====================================
    # ログインユーザー本人の
    # Tripのみ取得可能
    # =====================================

    def get_queryset(
        self,
    ):

        return Trip.objects.filter(
            user=self.request.user
        )

    # =====================================
    # 初期処理
    #
    # Tripを完了できる状態か確認する
    # =====================================

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

        self.trip = (
            get_object_or_404(
                Trip,
                pk=self.kwargs["pk"],
                user=request.user,
            )
        )

        # =====================================
        # この画面を開いた時点で
        # すでに旅完了だったか
        #
        # 保存後の戻り先で使用する
        # =====================================

        self.was_completed = (
            self.trip.status
            == "completed"
        )

        # =====================================
        # 日付に合わせて
        # Tripステータスを更新
        # =====================================

        sync_trip_status(
            self.trip
        )

        today = (
            timezone.localdate()
        )

        # =====================================
        # 旅中の場合
        #
        # 旅行終了日前なら
        # まだ旅完了にはできない
        # =====================================

        if (
            self.trip.status
            == "traveling"
        ):

            if (
                today
                < self.trip.end_date
            ):

                return redirect(
                    get_trip_detail_url(
                        self.trip
                    )
                )

        # =====================================
        # 旅完了の場合
        #
        # 完了情報の編集として
        # そのまま画面を表示する
        # =====================================

        elif (
            self.trip.status
            == "completed"
        ):

            pass

        # =====================================
        # 作成中・出発待ちなど
        #
        # 旅完了画面へは進ませない
        # =====================================

        else:

            return redirect(
                get_trip_detail_url(
                    self.trip
                )
            )

        return super().dispatch(
            request,
            *args,
            **kwargs
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
        ] = self.object

        # =====================================
        # すでに旅完了済みのTripを
        # 編集しているか
        # =====================================

        context[
            "is_completed_edit"
        ] = (
            self.object.status
            == "completed"
        )

        return context

    # =====================================
    # 保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        # =====================================
        # 保存時に必ず
        # 旅完了へ変更する
        # =====================================

        form.instance.status = (
            "completed"
        )

        return (
            super().form_valid(
                form
            )
        )

    # =====================================
    # 保存後
    # =====================================

    def get_success_url(
        self,
    ):

        # =====================================
        # もともと旅完了済みだった場合
        #
        # → Trip全体編集モードへ戻る
        # =====================================

        if self.was_completed:

            return (
                get_trip_detail_url(
                    self.object,
                    edit_mode=True,
                )
            )

        # =====================================
        # 今回初めて旅完了にした場合
        #
        # → 通常Trip詳細へ戻る
        # =====================================

        return get_trip_detail_url(
            self.object
        )


# =========================================
# Trip公開設定変更
# =========================================

class TripPublicUpdateView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=request.user,
        )

        # =====================================
        # 旅完了以外では
        # 公開設定を変更しない
        # =====================================

        if (
            trip.status
            != "completed"
        ):

            return redirect(
                get_trip_detail_url(
                    trip
                )
            )

        action = (
            request.POST.get(
                "action"
            )
        )

        # =====================================
        # 公開
        # =====================================

        if (
            action
            == "public"
        ):

            # =====================================
            # 公開には
            #
            # ・代表写真
            # ・感想
            #
            # が必要
            # =====================================

            if (
                not trip.main_media
                or not trip.overview
            ):

                return redirect(
                    get_trip_detail_url(
                        trip,
                        edit_mode=True,
                    )
                )

            trip.is_public = (
                True
            )

            trip.save(
                update_fields=[
                    "is_public",
                ]
            )

        # =====================================
        # 非公開
        # =====================================

        elif (
            action
            == "private"
        ):

            trip.is_public = (
                False
            )

            trip.save(
                update_fields=[
                    "is_public",
                ]
            )

        # =====================================
        # Trip全体編集モードへ戻る
        # =====================================

        return redirect(
            get_trip_detail_url(
                trip,
                edit_mode=True,
            )
        )