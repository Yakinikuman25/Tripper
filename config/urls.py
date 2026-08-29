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

from base.views.trip_views import (
    TripListView,
    PublicTripListView,
    TripCreateView,
    TripDetailView,
    TripUpdateView,
    TripDeleteView,
    TripPeriodConfirmView,
    TripStatusUpdateView,
    TripCompleteView,
    TripPublicUpdateView,
)

from base.views.day_views import (
    DayUpdateView,
    DayRecordUpdateView,
    DayMoveView,
    DayResetView,
)

from base.views.schedule_views import (
    ScheduleCreateView,
    ScheduleUpdateView,
    ScheduleDeleteView,
)

from base.views.expense_views import (
    TripExpenseCreateView,
    DayExpenseCreateView,
)


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

    # Trip一覧
    path(
        "trips/",
        TripListView.as_view(),
        name="trip_list"
    ),

    # 公開Trip一覧
    path(
        "public/",
        PublicTripListView.as_view(),
        name="public_trip",
    ),

    # Trip作成
    path(
        "trips/create/",
        TripCreateView.as_view(),
        name="trip_create"
    ),

    # Trip詳細
    path(
        "trips/<int:pk>/",
        TripDetailView.as_view(),
        name="trip_detail"
    ),

    # Trip編集
    path(
        "trips/<int:pk>/edit/",
        TripUpdateView.as_view(),
        name="trip_edit",
    ),

    # Trip削除
    path(
        "trips/<int:pk>/delete/",
        TripDeleteView.as_view(),
        name="trip_delete",
    ),

    # 旅行期間短縮時の確認
    path(
        "trips/<int:pk>/period-confirm/",
        TripPeriodConfirmView.as_view(),
        name="trip_period_confirm",
    ),

    # Tripステータス変更
    path(
        "trips/<int:pk>/status/",
        TripStatusUpdateView.as_view(),
        name="trip_status_update",
    ),

    # Trip完了
    path(
        "trips/<int:pk>/complete/",
        TripCompleteView.as_view(),
        name="trip_complete",
    ),

    # 公開・非公開設定
    path(
        "trips/<int:pk>/public/",
        TripPublicUpdateView.as_view(),
        name="trip_public_update",
    ),

    # Trip共通費用作成
    path(
        "trips/<int:trip_id>/expenses/create/",
        TripExpenseCreateView.as_view(),
        name="trip_expense_create",
    ),

    # Day編集
    path(
        "days/<int:pk>/edit/",
        DayUpdateView.as_view(),
        name="day_edit",
    ),

    # Dayリセット
    path(
        "days/<int:pk>/reset/",
        DayResetView.as_view(),
        name="day_reset",
    ),

    # Day入れ替え
    path(
        "days/<int:pk>/move/",
        DayMoveView.as_view(),
        name="day_move",
    ),

    # Day旅の記録編集
    path(
        "days/<int:pk>/record/",
        DayRecordUpdateView.as_view(),
        name="day_record_edit",
    ),

    # Day費用作成
    path(
        "days/<int:day_id>/expenses/create/",
        DayExpenseCreateView.as_view(),
        name="day_expense_create",
    ),

    # スケジュール作成
    path(
        "days/<int:day_pk>/schedules/create/",
        ScheduleCreateView.as_view(),
        name="schedule_create",
    ),

    # スケジュール編集
    path(
        "schedules/<int:pk>/edit/",
        ScheduleUpdateView.as_view(),
        name="schedule_edit",
    ),

    # スケジュール削除
    path(
        "schedules/<int:pk>/delete/",
        ScheduleDeleteView.as_view(),
        name="schedule_delete",
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