from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.generic import CreateView

from base.forms import UserCreationForm


# =========================================
# 新規アカウント登録
# =========================================

class SignUpView(
    CreateView,
):

    form_class = UserCreationForm

    template_name = (
        "pages/signup.html"
    )

    success_url = "/"

    # =====================================
    # アカウント作成成功時
    #
    # 登録したユーザーを
    # そのままログイン状態にする
    # =====================================

    def form_valid(
        self,
        form,
    ):

        response = (
            super().form_valid(
                form
            )
        )

        login(
            self.request,
            self.object,
        )

        return response


# =========================================
# ログイン
# =========================================

class Login(
    LoginView,
):

    template_name = (
        "pages/login.html"
    )