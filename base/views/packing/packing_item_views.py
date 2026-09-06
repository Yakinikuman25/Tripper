from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Max
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.views import View

from base.forms import PackingItemForm
from base.models import (
    PackingItem,
    Trip,
)

from base.views.trip.trip_services import (
    get_trip_detail_url,
)


# =========================================
# 持ち物リスト共通処理
# =========================================

class PackingItemBaseView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # Trip所有者か
    # =====================================

    def is_owner(
        self,
        trip,
    ):

        return (
            trip.user
            == self.request.user
        )


    # =====================================
    # Trip全体編集モードか
    #
    # traveling・completedでは
    # Trip全体編集時の操作判定に使用
    # =====================================

    def is_edit_mode(
        self,
        trip,
    ):

        if not self.is_owner(
            trip
        ):

            return False

        return (
            self.request.POST.get(
                "edit_mode"
            )
            == "1"
            or self.request.GET.get(
                "edit"
            )
            == "1"
        )


    # =====================================
    # 持ち物を
    # 追加・編集・削除できるか
    #
    # 作成中・出発待ち
    # → 所有者なら可能
    #
    # 旅中・旅完了
    # → Trip全体編集時のみ可能
    # =====================================

    def can_edit_packing_item(
        self,
        trip,
    ):

        if not self.is_owner(
            trip
        ):

            return False


        # =================================
        # 作成中・出発待ち
        # =================================

        if trip.status in (
            "draft",
            "planned",
        ):

            return True


        # =================================
        # 旅中・旅完了
        #
        # Trip全体編集時のみ
        # =================================

        if trip.status in (
            "traveling",
            "completed",
        ):

            return (
                self.is_edit_mode(
                    trip
                )
            )


        return False


    # =====================================
    # 準備済みチェックを
    # 変更できるか
    #
    # 作成中・出発待ち・旅中
    # → 所有者なら可能
    #
    # 旅完了
    # → Trip全体編集時のみ可能
    # =====================================

    def can_toggle_packing_item(
        self,
        trip,
    ):

        if not self.is_owner(
            trip
        ):

            return False


        # =================================
        # 作成中・出発待ち・旅中
        # =================================

        if trip.status in (
            "draft",
            "planned",
            "traveling",
        ):

            return True


        # =================================
        # 旅完了
        # =================================

        if (
            trip.status
            == "completed"
        ):

            return (
                self.is_edit_mode(
                    trip
                )
            )


        return False


    # =====================================
    # 持ち物操作後の戻り先
    # =====================================

    def get_return_url(
        self,
        trip,
    ):

        url = (
            get_trip_detail_url(
                trip,
                edit_mode=(
                    self.is_edit_mode(
                        trip
                    )
                ),
            )
        )

        return (
            url
            + "#trip-packing-list"
        )


    # =====================================
    # バッグ内の表示順を振り直す
    # =====================================

    def normalize_item_order(
        self,
        trip,
        bag_type,
    ):

        packing_items = (
            PackingItem.objects
            .filter(
                trip=trip,
                bag_type=bag_type,
            )
            .order_by(
                "item_order",
                "packing_item_id",
            )
        )

        for item_order, item in enumerate(
            packing_items,
            start=1,
        ):

            if (
                item.item_order
                != item_order
            ):

                item.item_order = (
                    item_order
                )

                item.save(
                    update_fields=[
                        "item_order",
                    ]
                )


# =========================================
# 持ち物追加
# =========================================

class PackingItemCreateView(
    PackingItemBaseView,
):

    def post(
        self,
        request,
        trip_id,
        *args,
        **kwargs,
    ):

        trip = (
            get_object_or_404(
                Trip,
                trip_id=trip_id,
                user=request.user,
            )
        )


        # =====================================
        # 編集権限確認
        # =====================================

        if not (
            self.can_edit_packing_item(
                trip
            )
        ):

            return redirect(
                self.get_return_url(
                    trip
                )
            )


        # =====================================
        # フォーム
        # =====================================

        form = (
            PackingItemForm(
                request.POST
            )
        )


        if form.is_valid():

            with transaction.atomic():

                packing_item = (
                    form.save(
                        commit=False
                    )
                )

                packing_item.trip = (
                    trip
                )

                packing_item.is_packed = (
                    False
                )


                # =================================
                # 同じバッグ内の
                # 最後の表示順を取得
                # =================================

                max_order = (
                    PackingItem.objects
                    .filter(
                        trip=trip,
                        bag_type=(
                            packing_item.bag_type
                        ),
                    )
                    .aggregate(
                        Max(
                            "item_order"
                        )
                    )[
                        "item_order__max"
                    ]
                )

                if (
                    max_order
                    is None
                ):

                    max_order = 0


                packing_item.item_order = (
                    max_order + 1
                )

                packing_item.save()


            return redirect(
                self.get_return_url(
                    trip
                )
            )


        # =====================================
        # 入力エラー
        # =====================================

        messages.error(
            request,
            "持ち物を登録できませんでした。入力内容を確認してください。",
        )

        return redirect(
            self.get_return_url(
                trip
            )
        )


# =========================================
# 持ち物編集
# =========================================

class PackingItemUpdateView(
    PackingItemBaseView,
):

    def post(
        self,
        request,
        packing_item_id,
        *args,
        **kwargs,
    ):

        packing_item = (
            get_object_or_404(
                PackingItem,
                packing_item_id=(
                    packing_item_id
                ),
            )
        )

        trip = (
            packing_item.trip
        )


        # =====================================
        # 編集権限確認
        # =====================================

        if not (
            self.can_edit_packing_item(
                trip
            )
        ):

            return redirect(
                self.get_return_url(
                    trip
                )
            )


        # =====================================
        # 変更前のバッグ
        # =====================================

        old_bag_type = (
            packing_item.bag_type
        )


        # =====================================
        # フォーム
        # =====================================

        form = (
            PackingItemForm(
                request.POST,
                instance=(
                    packing_item
                ),
            )
        )


        if form.is_valid():

            new_bag_type = (
                form.cleaned_data[
                    "bag_type"
                ]
            )


            with transaction.atomic():

                updated_item = (
                    form.save(
                        commit=False
                    )
                )


                # =================================
                # バッグを変更した場合
                #
                # 新しいバッグの一番最後へ移動
                # =================================

                if (
                    old_bag_type
                    != new_bag_type
                ):

                    max_order = (
                        PackingItem.objects
                        .filter(
                            trip=trip,
                            bag_type=(
                                new_bag_type
                            ),
                        )
                        .exclude(
                            packing_item_id=(
                                packing_item
                                .packing_item_id
                            ),
                        )
                        .aggregate(
                            Max(
                                "item_order"
                            )
                        )[
                            "item_order__max"
                        ]
                    )

                    if (
                        max_order
                        is None
                    ):

                        max_order = 0

                    updated_item.item_order = (
                        max_order + 1
                    )


                updated_item.save()


                # =================================
                # 元バッグの表示順を振り直す
                # =================================

                if (
                    old_bag_type
                    != new_bag_type
                ):

                    self.normalize_item_order(
                        trip,
                        old_bag_type,
                    )


            return redirect(
                self.get_return_url(
                    trip
                )
            )


        # =====================================
        # 入力エラー
        # =====================================

        messages.error(
            request,
            "持ち物を更新できませんでした。入力内容を確認してください。",
        )

        return redirect(
            self.get_return_url(
                trip
            )
        )


# =========================================
# 持ち物削除
# =========================================

class PackingItemDeleteView(
    PackingItemBaseView,
):

    def post(
        self,
        request,
        packing_item_id,
        *args,
        **kwargs,
    ):

        packing_item = (
            get_object_or_404(
                PackingItem,
                packing_item_id=(
                    packing_item_id
                ),
            )
        )

        trip = (
            packing_item.trip
        )


        # =====================================
        # 編集権限確認
        # =====================================

        if not (
            self.can_edit_packing_item(
                trip
            )
        ):

            return redirect(
                self.get_return_url(
                    trip
                )
            )


        bag_type = (
            packing_item.bag_type
        )


        # =====================================
        # 削除
        # =====================================

        with transaction.atomic():

            packing_item.delete()


            # =================================
            # 削除後の表示順を振り直す
            # =================================

            self.normalize_item_order(
                trip,
                bag_type,
            )


        return redirect(
            self.get_return_url(
                trip
            )
        )


# =========================================
# 準備済みチェック
#
# □ → ☑
# ☑ → □
# =========================================

class PackingItemToggleView(
    PackingItemBaseView,
):

    def post(
        self,
        request,
        packing_item_id,
        *args,
        **kwargs,
    ):

        packing_item = (
            get_object_or_404(
                PackingItem,
                packing_item_id=(
                    packing_item_id
                ),
            )
        )

        trip = (
            packing_item.trip
        )


        # =====================================
        # チェック変更権限確認
        # =====================================

        if not (
            self.can_toggle_packing_item(
                trip
            )
        ):

            return redirect(
                self.get_return_url(
                    trip
                )
            )


        # =====================================
        # チェック状態を反転
        #
        # False → True
        # True → False
        # =====================================

        packing_item.is_packed = (
            not packing_item.is_packed
        )

        packing_item.save(
            update_fields=[
                "is_packed",
                "updated_at",
            ]
        )


        return redirect(
            self.get_return_url(
                trip
            )
        )