from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    redirect,
    render,
)
from django.views import View
from django.views.generic import UpdateView

from base.models import Profile
from base.forms import EmailUpdateForm


# =========================================
# プロフィール編集
# =========================================

class ProfileUpdateView(
    LoginRequiredMixin,
    UpdateView,
):

    model = Profile

    template_name = (
        "pages/account/profile.html"
    )

    fields = (
        "profile_image",
        "introduction",
    )

    success_url = (
        "/profile/"
    )

    # =====================================
    # ログインユーザーの
    # Profileを取得
    #
    # Profileが存在しない場合は作成
    # =====================================

    def get_object(
        self,
        queryset=None,
    ):

        profile, created = (
            Profile.objects
            .get_or_create(
                user=self.request.user
            )
        )

        return profile

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
        # ログインユーザー情報を渡す
        # =====================================

        context[
            "user_info"
        ] = (
            self.request.user
        )

        return context

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        profile = (
            self.get_object()
        )

        # =====================================
        # プロフィール画像削除
        # =====================================

        if (
            "delete_image"
            in request.POST
        ):

            if (
                profile.profile_image
            ):

                # =====================================
                # デフォルト画像以外の場合だけ
                # 保存されている画像を削除
                # =====================================

                if (
                    profile
                    .profile_image
                    .name
                    != (
                        "profile_images/"
                        "default.png"
                    )
                ):

                    profile.profile_image.delete(
                        save=False
                    )

            # =====================================
            # デフォルト画像へ戻す
            # =====================================

            profile.profile_image = (
                "profile_images/default.png"
            )

            profile.save()

            return redirect(
                "profile"
            )

        return super().post(
            request,
            *args,
            **kwargs
        )


# =========================================
# メールアドレス変更
# =========================================

class EmailUpdateView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # GET
    # =====================================

    def get(
        self,
        request,
    ):

        form = (
            EmailUpdateForm(
                instance=request.user
            )
        )

        return render(
            request,
            "pages/account/email_change.html",
            {
                "form": form,
            },
        )

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
    ):

        form = (
            EmailUpdateForm(
                request.POST,
                instance=request.user,
            )
        )

        if form.is_valid():

            form.save()

            return redirect(
                "profile"
            )

        return render(
            request,
            "pages/account/email_change.html",
            {
                "form": form,
            },
        )