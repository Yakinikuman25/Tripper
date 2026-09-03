from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.urls import reverse
from django.views import View

from base.models import Day


# =========================================
# Dayリセット
#
# Day編集画面で扱う「計画情報」だけを
# 初期状態へ戻す
#
# リセットするもの
# ・タイトル
# ・訪問先
# ・メモ
# ・自由費予算
# ・Day予定金額
# ・Day参考URL
#
# リセットしないもの
# ・日付
# ・Day番号
# ・Schedule
# ・旅の記録
# ・写真
# ・自由費実績
# ・Day実際支払額
# ・Day費用明細
# =========================================

class DayResetView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # Trip詳細へ戻るURL
    # =====================================

    def get_return_url(
        self,
        trip,
        day,
        request,
    ):

        url = reverse(
            "trip_detail",
            kwargs={
                "pk": trip.trip_id,
            },
        )

        # =====================================
        # Trip全体編集モードを維持
        # =====================================

        if (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        ):

            url += "?edit=1"

        # =====================================
        # リセットしたDay位置まで移動
        # =====================================

        url += (
            f"#day-{day.day_id}"
        )

        return url

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        day = get_object_or_404(
            Day,
            pk=self.kwargs["pk"],
            trip__user=request.user,
        )

        trip = day.trip

        # =====================================
        # リセット可能か確認
        #
        # 作成中
        # → リセット可能
        #
        # 作成完了後
        # → Trip全体編集モードのみ可能
        # =====================================

        is_edit_mode = (
            request.POST.get(
                "edit_mode"
            )
            == "1"
        )

        if (
            trip.status != "draft"
            and not is_edit_mode
        ):

            return redirect(
                self.get_return_url(
                    trip,
                    day,
                    request,
                )
            )

        # =====================================
        # Day計画情報をリセット
        # =====================================

        with transaction.atomic():

            # =====================================
            # Day本体
            #
            # actual_cost
            # actual_amount
            # は実績なのでリセットしない
            # =====================================

            day.title = ""
            day.memo = ""
            day.budget = None
            day.planned_amount = None

            day.save(
                update_fields=[
                    "title",
                    "memo",
                    "budget",
                    "planned_amount",
                ]
            )

            # =====================================
            # このDayの訪問先を削除
            # =====================================

            day.day_locations.all().delete()

            # =====================================
            # このDayの参考URLを削除
            # =====================================

            day.reference_urls.all().delete()

            # =====================================
            # どのDayLocationからも
            # 使われなくなったLocationを削除
            # =====================================

            trip.locations.filter(
                day_locations__isnull=True
            ).delete()

        # =====================================
        # リセットしたDay位置へ戻る
        # =====================================

        return redirect(
            self.get_return_url(
                trip,
                day,
                request,
            )
        )