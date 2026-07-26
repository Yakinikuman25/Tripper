"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path

from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth.views import LogoutView


from base.views.account_views import (
    Login,
    SignUpView,
    ProfileUpdateView,
    EmailUpdateView,
    PasswordChange,
    PasswordReset,
    PasswordResetDone,
    PasswordResetConfirm,
    PasswordResetComplete,
    AccountDeleteView,
)


from base.views.home_views import HomeView




urlpatterns = [


    # 管理画面

    path(
        "admin/",
        admin.site.urls
    ),






    # アカウント



    path(
        "login/",
        Login.as_view(),
        name="login"
    ),




    path(
        "logout/",
        LogoutView.as_view(
            next_page="/"
        ),
        name="logout"
    ),




    path(
        "signup/",
        SignUpView.as_view(),
        name="signup"
    ),




    path(
        "profile/",
        ProfileUpdateView.as_view(),
        name="profile"
    ),








    # メールアドレス変更


    path(
        "email/change/",
        EmailUpdateView.as_view(),
        name="email_change"
    ),







    # パスワード変更


    path(
        "password/change/",
        PasswordChange.as_view(),
        name="password_change"
    ),








    # パスワードリセット


    path(
        "password/reset/",
        PasswordReset.as_view(),
        name="password_reset"
    ),



    path(
        "password/reset/done/",
        PasswordResetDone.as_view(),
        name="password_reset_done"
    ),



    path(
        "password/reset/confirm/<uidb64>/<token>/",
        PasswordResetConfirm.as_view(),
        name="password_reset_confirm"
    ),



    path(
        "password/reset/complete/",
        PasswordResetComplete.as_view(),
        name="password_reset_complete"
    ),







    # アカウント削除


    path(
        "account/delete/",
        AccountDeleteView.as_view(),
        name="account_delete"
    ),








    # トップページ


    path(
        "",
        HomeView.as_view(),
        name="home"
    ),

]





# 開発環境でメディアファイルを表示する設定

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)