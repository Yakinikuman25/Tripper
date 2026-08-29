from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import View

from base.models import Profile


# =========================================
# アカウント削除
# =========================================

class AccountDeleteView(
    LoginRequiredMixin,
    View,
):

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
    ):

        user = request.user

        # =====================================
        # プロフィール画像削除
        #
        # デフォルト画像は削除しない
        # =====================================

        try:

            profile = user.profile

            if profile.profile_image:

                if (
                    profile.profile_image.name
                    != "profile_images/default.png"
                ):

                    profile.profile_image.delete(
                        save=False
                    )

        except Profile.DoesNotExist:

            pass

        # =====================================
        # ログアウト
        # =====================================

        logout(
            request
        )

        # =====================================
        # ユーザー削除
        # =====================================

        user.delete()

        # =====================================
        # Homeへ戻る
        # =====================================

        return redirect(
            "home"
        )