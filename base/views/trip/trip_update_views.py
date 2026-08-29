from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views import View
from django.views.generic import UpdateView

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
    day_has_data,
    sync_trip_status,
    get_trip_detail_url,
)


# =========================================
# Trip編集
# =========================================

class TripUpdateView(
    LoginRequiredMixin,
    UpdateView,
):

    model = Trip

    form_class = TripForm

    template_name = (
        "pages/trip/trip_create.html"
    )

    # =====================================
    # ログインユーザー本人の
    # Tripのみ編集可能
    # =====================================

    def get_queryset(
        self,
    ):

        return Trip.objects.filter(
            user=self.request.user
        )

    # =====================================
    # Trip参考URL FormSet
    # =====================================

    def get_reference_url_formset(
        self,
    ):

        # =====================================
        # POST時
        # =====================================

        if (
            self.request.method
            == "POST"
        ):

            return TripReferenceUrlFormSet(
                self.request.POST,
                instance=self.object,
                prefix="reference_urls",
            )

        # =====================================
        # GET時
        # =====================================

        return TripReferenceUrlFormSet(
            instance=self.object,
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

            context[
                "reference_url_formset"
            ] = (
                self.get_reference_url_formset()
            )

        return context

    # =====================================
    # Trip編集保存
    # =====================================

    def form_valid(
        self,
        form
    ):

        # =====================================
        # Trip参考URL FormSet
        # =====================================

        reference_url_formset = (
            self.get_reference_url_formset()
        )

        # =====================================
        # Tripフォームが有効でも、
        # 参考URLにエラーがあれば
        # 保存しない
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
        # 新しい旅行期間
        # =====================================

        new_start_date = (
            form.cleaned_data[
                "start_date"
            ]
        )

        new_end_date = (
            form.cleaned_data[
                "end_date"
            ]
        )

        # =====================================
        # ハッシュタグ
        # =====================================

        hashtag_names = (
            form.cleaned_data.get(
                "hashtags",
                [],
            )
        )

        # =====================================
        # 新しい旅行期間の外に出るDay
        # =====================================

        outside_days = (
            self.object
            .days
            .exclude(
                date__range=(
                    new_start_date,
                    new_end_date,
                )
            )
        )

        # =====================================
        # 期間外Dayのうち
        # 何か記録されているDayを取得
        # =====================================

        filled_outside_days = []

        for day in outside_days:

            if day_has_data(
                day
            ):

                filled_outside_days.append(
                    day
                )

        # =====================================
        # 期間短縮で
        # 記入済みDayが削除対象になる場合
        #
        # Trip本体だけでなく、
        # ハッシュタグ・参考URLも
        # Sessionへ一時保存する
        # =====================================

        if filled_outside_days:

            category = (
                form.cleaned_data.get(
                    "category"
                )
            )

            self.request.session[
                "pending_trip_update"
            ] = {

                "trip_id": (
                    self.object.trip_id
                ),

                "title": (
                    form.cleaned_data[
                        "title"
                    ]
                ),

                "category_id": (
                    category.category_id
                    if category
                    else None
                ),

                "start_date": (
                    new_start_date.isoformat()
                ),

                "end_date": (
                    new_end_date.isoformat()
                ),

                "memo": (
                    form.cleaned_data.get(
                        "memo",
                        "",
                    )
                ),

                "hashtags": (
                    hashtag_names
                ),

                "reference_urls": (
                    reference_url_items
                ),
            }

            return redirect(
                "trip_period_confirm",
                pk=self.object.trip_id,
            )

        # =====================================
        # 削除対象に記入済みDayがない場合
        #
        # そのまま保存
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
                hashtag_names,
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
            # Dayを作成・整理
            # =====================================

            sync_trip_days(
                self.object
            )

            # =====================================
            # Tripステータス更新
            # =====================================

            sync_trip_status(
                self.object
            )

        return response

    # =====================================
    # Trip編集保存後
    # =====================================

    def get_success_url(
        self,
    ):

        # =====================================
        # 作成中
        # → 通常Trip詳細
        # =====================================

        if (
            self.object.status
            == "draft"
        ):

            return (
                get_trip_detail_url(
                    self.object
                )
            )

        # =====================================
        # 出発待ち・旅中・旅完了
        # → Trip全体編集モード
        # =====================================

        return get_trip_detail_url(
            self.object,
            edit_mode=True,
        )


# =========================================
# Trip期間短縮確認
#
# 旅行期間を短縮したことで
# 記入済みDayが削除対象になる場合に
# 確認画面を表示する
# =========================================

class TripPeriodConfirmView(
    LoginRequiredMixin,
    View,
):

    template_name = (
        "pages/trip/trip_period_confirm.html"
    )

    # =====================================
    # ログインユーザー本人の
    # Tripを取得
    # =====================================

    def get_trip(
        self,
    ):

        return get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=self.request.user,
        )

    # =====================================
    # Sessionから
    # Trip編集途中データを取得
    # =====================================

    def get_pending_data(
        self,
    ):

        pending_data = (
            self.request.session.get(
                "pending_trip_update"
            )
        )

        # =====================================
        # Sessionデータがない場合
        # =====================================

        if not pending_data:

            return None

        # =====================================
        # 別TripのSessionデータの場合
        # =====================================

        if (
            pending_data.get(
                "trip_id"
            )
            != self.kwargs["pk"]
        ):

            return None

        return pending_data

    # =====================================
    # GET
    # =====================================

    def get(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = (
            self.get_trip()
        )

        pending_data = (
            self.get_pending_data()
        )

        # =====================================
        # Sessionデータがない場合
        # Trip詳細へ戻る
        # =====================================

        if not pending_data:

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        # =====================================
        # Sessionの日付文字列を
        # dateへ戻す
        # =====================================

        new_start_date = (
            date.fromisoformat(
                pending_data[
                    "start_date"
                ]
            )
        )

        new_end_date = (
            date.fromisoformat(
                pending_data[
                    "end_date"
                ]
            )
        )

        # =====================================
        # 削除対象になるDay
        # =====================================

        outside_days = (
            trip.days.exclude(
                date__range=(
                    new_start_date,
                    new_end_date,
                )
            )
        )

        # =====================================
        # 確認画面表示
        # =====================================

        return render(
            request,
            self.template_name,
            {
                "trip": trip,

                "outside_days": (
                    outside_days
                ),

                "new_start_date": (
                    new_start_date
                ),

                "new_end_date": (
                    new_end_date
                ),
            },
        )

    # =====================================
    # POST
    # =====================================

    def post(
        self,
        request,
        *args,
        **kwargs
    ):

        trip = (
            self.get_trip()
        )

        pending_data = (
            self.get_pending_data()
        )

        # =====================================
        # Sessionデータがない場合
        # Trip詳細へ戻る
        # =====================================

        if not pending_data:

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        action = (
            request.POST.get(
                "action"
            )
        )

        # =====================================
        # キャンセル
        # =====================================

        if (
            action
            == "cancel"
        ):

            del request.session[
                "pending_trip_update"
            ]

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        # =====================================
        # 変更確定
        # =====================================

        if (
            action
            == "confirm"
        ):

            # =====================================
            # Sessionの日付文字列を
            # dateへ戻す
            # =====================================

            new_start_date = (
                date.fromisoformat(
                    pending_data[
                        "start_date"
                    ]
                )
            )

            new_end_date = (
                date.fromisoformat(
                    pending_data[
                        "end_date"
                    ]
                )
            )

            # =====================================
            # Trip更新をまとめて実行
            # =====================================

            with transaction.atomic():

                # =====================================
                # 新しい期間外のDayを削除
                # =====================================

                outside_days = (
                    trip.days.exclude(
                        date__range=(
                            new_start_date,
                            new_end_date,
                        )
                    )
                )

                outside_days.delete()

                # =====================================
                # Trip本体
                # =====================================

                trip.title = (
                    pending_data[
                        "title"
                    ]
                )

                trip.category_id = (
                    pending_data[
                        "category_id"
                    ]
                )

                trip.start_date = (
                    new_start_date
                )

                trip.end_date = (
                    new_end_date
                )

                trip.memo = (
                    pending_data.get(
                        "memo",
                        "",
                    )
                )

                trip.save()

                # =====================================
                # ハッシュタグ
                # =====================================

                sync_trip_hashtags(
                    trip,
                    pending_data.get(
                        "hashtags",
                        [],
                    ),
                )

                # =====================================
                # Trip参考URL
                # =====================================

                sync_trip_reference_urls(
                    trip,
                    pending_data.get(
                        "reference_urls",
                        [],
                    ),
                )

                # =====================================
                # Dayを旅行期間に合わせて整理
                # =====================================

                sync_trip_days(
                    trip
                )

                # =====================================
                # Tripステータス更新
                # =====================================

                sync_trip_status(
                    trip
                )

            # =====================================
            # Sessionの編集途中データを削除
            # =====================================

            del request.session[
                "pending_trip_update"
            ]

            # =====================================
            # Trip詳細へ戻る
            # =====================================

            if (
                trip.status
                == "draft"
            ):

                return redirect(
                    get_trip_detail_url(
                        trip
                    )
                )

            return redirect(
                get_trip_detail_url(
                    trip,
                    edit_mode=True,
                )
            )

        # =====================================
        # 想定外のactionの場合
        # 確認画面へ戻る
        # =====================================

        return redirect(
            "trip_period_confirm",
            pk=trip.trip_id,
        )