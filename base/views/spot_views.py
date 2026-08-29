from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
)

from base.models import (
    Day,
    Spot,
)

from base.forms import (
    SpotForm,
    SpotReferenceUrlFormSet,
)


# =========================================
# スケジュール参考URLを保存する共通関数
# =========================================

def save_spot_reference_urls(
    formset,
    spot,
):

    url_order = 1

    for url_form in formset.forms:

        # -------------------------
        # FormSetの空フォームは無視
        # -------------------------

        if not url_form.cleaned_data:

            continue

        # -------------------------
        # 削除対象
        # -------------------------

        if url_form.cleaned_data.get(
            "DELETE"
        ):

            if url_form.instance.pk:

                url_form.instance.delete()

            continue

        # -------------------------
        # URLが空欄なら登録しない
        #
        # extraで表示される空フォームを
        # 保存しないための処理
        # -------------------------

        url = url_form.cleaned_data.get(
            "url"
        )

        if not url:

            continue

        # -------------------------
        # 参考URLを保存
        # -------------------------

        reference_url = (
            url_form.save(
                commit=False
            )
        )

        reference_url.spot = spot

        reference_url.url_order = (
            url_order
        )

        reference_url.save()

        url_order += 1


# =========================================
# スケジュール作成
#
# 現在はモデル名がSpotのままなので
# View名もSpotCreateViewを維持する
# =========================================

class SpotCreateView(
    LoginRequiredMixin,
    CreateView,
):

    model = Spot

    form_class = SpotForm

    template_name = (
        "pages/spot_create.html"
    )

    # =====================================
    # 対象Dayを取得
    # =====================================

    def dispatch(
        self,
        request,
        *args,
        **kwargs
    ):

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

    # =====================================
    # 参考URL FormSetを作成
    # =====================================

    def get_reference_url_formset(
        self,
        instance=None,
    ):

        if instance is None:

            instance = Spot(
                day=self.day
            )

        if self.request.method == "POST":

            return (
                SpotReferenceUrlFormSet(
                    self.request.POST,
                    instance=instance,
                    prefix="reference_urls",
                )
            )

        return (
            SpotReferenceUrlFormSet(
                instance=instance,
                prefix="reference_urls",
            )
        )

    # =====================================
    # Templateへ渡すデータ
    # =====================================

    def get_context_data(
        self,
        **kwargs
    ):

        context = (
            super()
            .get_context_data(
                **kwargs
            )
        )

        context["day"] = (
            self.day
        )

        context["trip"] = (
            self.day.trip
        )

        # -------------------------
        # form_valid / form_invalidから
        # すでにFormSetを渡している場合は
        # 作り直さない
        # -------------------------

        if (
            "reference_url_formset"
            not in context
        ):

            context[
                "reference_url_formset"
            ] = (
                self.get_reference_url_formset()
            )

        return context

    # =====================================
    # スケジュール保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        # -------------------------
        # 対象Dayを自動設定
        # -------------------------

        form.instance.day = (
            self.day
        )

        # -------------------------
        # 表示順を自動採番
        #
        # 現在はDB上のフィールド名が
        # spot_orderのためそのまま使用
        # -------------------------

        last_spot = (
            self.day
            .spots
            .order_by(
                "-spot_order"
            )
            .first()
        )

        if last_spot:

            form.instance.spot_order = (
                last_spot.spot_order
                + 1
            )

        else:

            form.instance.spot_order = 1

        # -------------------------
        # 参考URL FormSet
        # -------------------------

        reference_url_formset = (
            self.get_reference_url_formset(
                instance=form.instance
            )
        )

        # -------------------------
        # URL側にエラーがある場合
        # スケジュール本体も保存しない
        # -------------------------

        if not (
            reference_url_formset
            .is_valid()
        ):

            return (
                self.render_to_response(
                    self.get_context_data(
                        form=form,
                        reference_url_formset=(
                            reference_url_formset
                        ),
                    )
                )
            )

        # =====================================
        # スケジュールと参考URLを
        # まとめて保存
        #
        # 途中でエラーになった場合は
        # どちらも保存しない
        # =====================================

        with transaction.atomic():

            response = (
                super().form_valid(
                    form
                )
            )

            reference_url_formset.instance = (
                self.object
            )

            save_spot_reference_urls(
                reference_url_formset,
                self.object,
            )

        return response

    # =====================================
    # 保存後の戻り先
    #
    # 作成中
    # → 通常のTrip詳細
    #
    # 作成完了後
    # → Trip全体編集モード
    #
    # どちらも操作したDayまで戻る
    # =====================================

    def get_success_url(self):

        trip = (
            self.day.trip
        )

        url = reverse(
            "trip_detail",
            kwargs={
                "pk": trip.trip_id,
            },
        )

        # -------------------------
        # 作成中以外は
        # Trip全体編集モードを維持
        # -------------------------

        if trip.status != "draft":

            url += "?edit=1"

        # -------------------------
        # スケジュールを追加した
        # Day位置まで戻る
        # -------------------------

        url += (
            f"#day-{self.day.day_id}"
        )

        return url


# =========================================
# スケジュール編集
#
# 現在はモデル名がSpotのままなので
# View名もSpotUpdateViewを維持する
# =========================================

class SpotUpdateView(
    LoginRequiredMixin,
    UpdateView,
):

    model = Spot

    form_class = SpotForm

    template_name = (
        "pages/spot_edit.html"
    )

    # =====================================
    # 自分のTripのスケジュールだけ取得
    # =====================================

    def get_queryset(self):

        return (
            Spot.objects
            .filter(
                day__trip__user=(
                    self.request.user
                )
            )
        )

    # =====================================
    # 参考URL FormSetを作成
    # =====================================

    def get_reference_url_formset(
        self,
    ):

        if self.request.method == "POST":

            return (
                SpotReferenceUrlFormSet(
                    self.request.POST,
                    instance=self.object,
                    prefix="reference_urls",
                )
            )

        return (
            SpotReferenceUrlFormSet(
                instance=self.object,
                prefix="reference_urls",
            )
        )

    # =====================================
    # Templateへ渡すデータ
    # =====================================

    def get_context_data(
        self,
        **kwargs
    ):

        context = (
            super()
            .get_context_data(
                **kwargs
            )
        )

        context["day"] = (
            self.object.day
        )

        context["trip"] = (
            self.object.day.trip
        )

        if (
            "reference_url_formset"
            not in context
        ):

            context[
                "reference_url_formset"
            ] = (
                self.get_reference_url_formset()
            )

        return context

    # =====================================
    # スケジュール編集保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        reference_url_formset = (
            SpotReferenceUrlFormSet(
                self.request.POST,
                instance=self.object,
                prefix="reference_urls",
            )
        )

        # -------------------------
        # URL側にエラーがある場合
        # スケジュール本体も更新しない
        # -------------------------

        if not (
            reference_url_formset
            .is_valid()
        ):

            return (
                self.render_to_response(
                    self.get_context_data(
                        form=form,
                        reference_url_formset=(
                            reference_url_formset
                        ),
                    )
                )
            )

        # =====================================
        # スケジュール本体と参考URLを
        # まとめて更新
        # =====================================

        with transaction.atomic():

            response = (
                super().form_valid(
                    form
                )
            )

            reference_url_formset.instance = (
                self.object
            )

            save_spot_reference_urls(
                reference_url_formset,
                self.object,
            )

        return response

    # =====================================
    # 編集後の戻り先
    # =====================================

    def get_success_url(self):

        day = (
            self.object.day
        )

        trip = (
            day.trip
        )

        url = reverse(
            "trip_detail",
            kwargs={
                "pk": trip.trip_id,
            },
        )

        # -------------------------
        # 作成中以外は
        # Trip全体編集モードを維持
        # -------------------------

        if trip.status != "draft":

            url += "?edit=1"

        # -------------------------
        # 編集したスケジュールの
        # Day位置まで戻る
        # -------------------------

        url += (
            f"#day-{day.day_id}"
        )

        return url


# =========================================
# スケジュール削除
#
# 現在はモデル名がSpotのままなので
# View名もSpotDeleteViewを維持する
#
# Spotを削除すると、
# ForeignKeyのon_delete=models.CASCADEにより
# SpotReferenceUrlも自動削除される
# =========================================

class SpotDeleteView(
    LoginRequiredMixin,
    DeleteView,
):

    model = Spot

    template_name = (
        "pages/spot_delete.html"
    )

    # =====================================
    # 自分のTripのスケジュールだけ取得
    # =====================================

    def get_queryset(self):

        return (
            Spot.objects
            .filter(
                day__trip__user=(
                    self.request.user
                )
            )
        )

    # =====================================
    # Templateへ渡すデータ
    # =====================================

    def get_context_data(
        self,
        **kwargs
    ):

        context = (
            super()
            .get_context_data(
                **kwargs
            )
        )

        context["day"] = (
            self.object.day
        )

        context["trip"] = (
            self.object.day.trip
        )

        return context

    # =====================================
    # 削除後の戻り先
    #
    # DeleteViewでは削除後に
    # self.objectを参照することになるため、
    # 必要なIDをここで取得してURLを作る
    # =====================================

    def get_success_url(self):

        day = (
            self.object.day
        )

        trip = (
            day.trip
        )

        day_id = (
            day.day_id
        )

        trip_id = (
            trip.trip_id
        )

        url = reverse(
            "trip_detail",
            kwargs={
                "pk": trip_id,
            },
        )

        # -------------------------
        # 作成中以外は
        # Trip全体編集モードを維持
        # -------------------------

        if trip.status != "draft":

            url += "?edit=1"

        # -------------------------
        # 削除したスケジュールが
        # あったDay位置まで戻る
        # -------------------------

        url += (
            f"#day-{day_id}"
        )

        return url