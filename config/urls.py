"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path

from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth.views import LogoutView


# =========================================
# Views
# =========================================

from base.views import (
    # =====================================
    # Account
    # =====================================
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

    # =====================================
    # Home
    # =====================================
    HomeView,

    # =====================================
    # Trip
    # =====================================
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

    # =====================================
    # Save
    # =====================================
    TripSaveToggleView,
    SavedTripListView,

    # =====================================
    # Day
    # =====================================
    DayUpdateView,
    DayRecordUpdateView,
    DayMoveView,
    DayResetView,

    # =====================================
    # Schedule
    # =====================================
    ScheduleCreateView,
    ScheduleUpdateView,
    ScheduleDeleteView,

    # =====================================
    # Expense
    # =====================================
    TripExpenseCreateView,
    DayExpenseCreateView,
)


urlpatterns = [

    # =========================================
    # 管理画面
    # =========================================

    path(
        "admin/",
        admin.site.urls,
    ),

    # =========================================
    # アカウント
    # =========================================

    # ログイン
    path(
        "login/",
        Login.as_view(),
        name="login",
    ),

    # ログアウト
    path(
        "logout/",
        LogoutView.as_view(
            next_page="/"
        ),
        name="logout",
    ),

    # アカウント作成
    path(
        "signup/",
        SignUpView.as_view(),
        name="signup",
    ),

    # プロフィール編集
    path(
        "profile/",
        ProfileUpdateView.as_view(),
        name="profile",
    ),

    # =========================================
    # メールアドレス変更
    # =========================================

    path(
        "email/change/",
        EmailUpdateView.as_view(),
        name="email_change",
    ),

    # =========================================
    # パスワード変更
    # =========================================

    path(
        "password/change/",
        PasswordChange.as_view(),
        name="password_change",
    ),

    # =========================================
    # パスワードリセット
    # =========================================

    path(
        "password/reset/",
        PasswordReset.as_view(),
        name="password_reset",
    ),

    path(
        "password/reset/done/",
        PasswordResetDone.as_view(),
        name="password_reset_done",
    ),

    path(
        "password/reset/confirm/<uidb64>/<token>/",
        PasswordResetConfirm.as_view(),
        name="password_reset_confirm",
    ),

    path(
        "password/reset/complete/",
        PasswordResetComplete.as_view(),
        name="password_reset_complete",
    ),

    # =========================================
    # アカウント削除
    # =========================================

    path(
        "account/delete/",
        AccountDeleteView.as_view(),
        name="account_delete",
    ),

    # =========================================
    # Trip
    # =========================================

    # Trip一覧
    path(
        "trips/",
        TripListView.as_view(),
        name="trip_list",
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
        name="trip_create",
    ),

    # =========================================
    # Save
    # =========================================

    # 保存Trip一覧
    path(
        "trips/saved/",
        SavedTripListView.as_view(),
        name="saved_trip_list",
    ),

    # =========================================
    # Trip詳細・編集
    # =========================================

    # Trip詳細
    path(
        "trips/<int:pk>/",
        TripDetailView.as_view(),
        name="trip_detail",
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

    # =========================================
    # Save
    # =========================================

    # 公開Tripの保存・保存解除
    path(
        "trips/<int:pk>/save/",
        TripSaveToggleView.as_view(),
        name="trip_save_toggle",
    ),

    # =========================================
    # Trip共通費用
    # =========================================

    path(
        "trips/<int:trip_id>/expenses/create/",
        TripExpenseCreateView.as_view(),
        name="trip_expense_create",
    ),

    # =========================================
    # Day
    # =========================================

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

    # =========================================
    # Day費用
    # =========================================

    path(
        "days/<int:day_id>/expenses/create/",
        DayExpenseCreateView.as_view(),
        name="day_expense_create",
    ),

    # =========================================
    # Schedule
    # =========================================

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

    # =========================================
    # Home
    # =========================================

    path(
        "",
        HomeView.as_view(),
        name="home",
    ),
]


# =========================================
# 開発環境でメディアファイルを表示する設定
# =========================================

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT,
)