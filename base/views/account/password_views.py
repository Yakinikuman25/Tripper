from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.urls import reverse_lazy


# =========================================
# パスワード変更
# =========================================

class PasswordChange(
    PasswordChangeView,
):

    template_name = (
        "pages/password_change.html"
    )

    success_url = reverse_lazy(
        "profile"
    )


# =========================================
# パスワードリセット
# =========================================

class PasswordReset(
    PasswordResetView,
):

    template_name = (
        "pages/password_reset/"
        "password_reset.html"
    )

    email_template_name = (
        "pages/password_reset/"
        "password_reset_email.html"
    )

    # =====================================
    # メール件名テンプレート
    # =====================================

    subject_template_name = (
        "pages/password_reset/"
        "password_reset_subject.txt"
    )

    success_url = reverse_lazy(
        "password_reset_done"
    )


# =========================================
# パスワードリセット
# メール送信完了
# =========================================

class PasswordResetDone(
    PasswordResetDoneView,
):

    template_name = (
        "pages/password_reset/"
        "password_reset_done.html"
    )


# =========================================
# パスワードリセット
# 新しいパスワード入力
# =========================================

class PasswordResetConfirm(
    PasswordResetConfirmView,
):

    template_name = (
        "pages/password_reset/"
        "password_reset_confirm.html"
    )

    success_url = reverse_lazy(
        "password_reset_complete"
    )


# =========================================
# パスワードリセット完了
# =========================================

class PasswordResetComplete(
    PasswordResetCompleteView,
):

    template_name = (
        "pages/password_reset/"
        "password_reset_complete.html"
    )