from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.views.generic import CreateView

from base.models import Trip

from base.forms import (
    TripForm,
    TripReferenceUrlFormSet,
)

from .trip_services import (
    sync_trip_days,
    sync_trip_hashtags,
    get_trip_reference_url_items,
    sync_trip_reference_urls,
)


# =========================================
# Trip作成
# =========================================

class TripCreateView(
    LoginRequiredMixin,
    CreateView,
):

    model = Trip

    template_name = (
        "pages/trip_create.html"
    )

    form_class = TripForm

    success_url = "/trips/"

    # =====================================
    # Trip参考URL FormSet
    # =====================================

    def get_reference_url_formset(
        self,
        instance=None,
    ):

        if instance is None:

            instance = Trip()

        # =====================================
        # POST時
        # =====================================

        if (
            self.request.method
            == "POST"
        ):

            return TripReferenceUrlFormSet(
                self.request.POST,
                instance=instance,
                prefix="reference_urls",
            )

        # =====================================
        # GET時
        # =====================================

        return TripReferenceUrlFormSet(
            instance=instance,
            prefix="reference_urls",
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

        # =====================================
        # Trip参考URL FormSet
        # =====================================

        if (
            "reference_url_formset"
            not in context
        ):

            form = context.get(
                "form"
            )

            instance = (
                form.instance
                if form is not None
                else Trip()
            )

            context[
                "reference_url_formset"
            ] = (
                self.get_reference_url_formset(
                    instance=instance
                )
            )

        return context

    # =====================================
    # Trip保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        # =====================================
        # 作成ユーザー
        # =====================================

        form.instance.user = (
            self.request.user
        )

        # =====================================
        # 新規Tripは
        # 必ず作成中から開始
        # =====================================

        form.instance.status = (
            "draft"
        )

        # =====================================
        # Trip参考URL FormSet
        # =====================================

        reference_url_formset = (
            self.get_reference_url_formset(
                instance=form.instance
            )
        )

        # =====================================
        # Tripフォームが有効でも、
        # 参考URLにエラーがあれば
        # Tripを保存しない
        # =====================================

        if not (
            reference_url_formset
            .is_valid()
        ):

            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    reference_url_formset=(
                        reference_url_formset
                    ),
                )
            )

        # =====================================
        # 保存対象の参考URLを取得
        # =====================================

        reference_url_items = (
            get_trip_reference_url_items(
                reference_url_formset
            )
        )

        # =====================================
        # Trip本体・関連データを
        # まとめて保存
        # =====================================

        with transaction.atomic():

            # =====================================
            # Trip本体
            # =====================================

            response = (
                super().form_valid(
                    form
                )
            )

            # =====================================
            # ハッシュタグ
            # =====================================

            sync_trip_hashtags(
                self.object,
                form.cleaned_data.get(
                    "hashtags",
                    [],
                ),
            )

            # =====================================
            # Trip参考URL
            # =====================================

            sync_trip_reference_urls(
                self.object,
                reference_url_items,
            )

            # =====================================
            # 旅行期間に合わせて
            # Dayを自動作成
            # =====================================

            sync_trip_days(
                self.object
            )

        return response