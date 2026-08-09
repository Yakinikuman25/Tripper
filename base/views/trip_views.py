from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import F
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
    UpdateView,
    DeleteView,
)

from base.models import Trip, Day
from base.forms import (
    TripForm,
    TripCompleteForm,
    DayRecordForm,
)


# Trip期間に合わせてDayを作成・整理する関数
def sync_trip_days(trip):

    current_date = trip.start_date
    day_order = 1

    while current_date <= trip.end_date:

        day, created = Day.objects.get_or_create(
            trip=trip,
            date=current_date,
            defaults={
                "day_order": day_order,
            },
        )

        # 既存Dayの場合もDay番号を更新
        if day.day_order != day_order:

            day.day_order = day_order

            day.save(
                update_fields=[
                    "day_order"
                ]
            )

        current_date += timedelta(
            days=1
        )

        day_order += 1

    # Trip期間外のDayを取得
    outside_days = trip.days.exclude(
        date__range=(
            trip.start_date,
            trip.end_date,
        )
    )

    # ここまで来る時点では削除してよいDayなので削除
    outside_days.delete()

    # Dayから使われなくなったLocationを削除
    trip.locations.filter(
        days__isnull=True
    ).delete()


# Dayに何か記入されているか確認する関数
def day_has_data(day):

    return (
        bool(day.title)
        or bool(day.content)
        or bool(day.media)
        or day.locations.exists()
        or day.spots.exists()
    )


# Tripの日付に合わせてステータスを更新する関数
def sync_trip_status(trip):

    today = timezone.localdate()

    # 作成中は
    # 「コース作成完了」を押すまで変更しない
    if trip.status == "draft":

        return

    # 旅完了は自動変更しない
    if trip.status == "completed":

        return

    # 旅行開始日前
    if today < trip.start_date:

        new_status = "planned"

    # 旅行開始日以降
    else:

        new_status = "traveling"

    # 現在のステータスと違う場合だけ更新
    if trip.status != new_status:

        trip.status = new_status

        trip.save(
            update_fields=[
                "status"
            ]
        )


# Trip一覧
class TripListView(LoginRequiredMixin, ListView):

    model = Trip
    template_name = "pages/trip_list.html"
    context_object_name = "trips"

    def get_queryset(self):

        trips = Trip.objects.filter(
            user=self.request.user
        ).order_by("-created_at")

        # 一覧を表示する前に
        # 各Tripのステータスを最新状態にする
        for trip in trips:

            sync_trip_status(
                trip
            )

        return trips


# Trip作成
class TripCreateView(LoginRequiredMixin, CreateView):

    model = Trip
    template_name = "pages/trip_create.html"
    form_class = TripForm

    success_url = "/trips/"

    def form_valid(self, form):

        form.instance.user = self.request.user

        # Trip作成時は必ず「作成中」
        form.instance.status = "draft"

        # Tripを保存
        response = super().form_valid(form)

        # Trip期間分のDayを自動生成
        sync_trip_days(
            self.object
        )

        return response


# Trip詳細
class TripDetailView(LoginRequiredMixin, DetailView):

    model = Trip
    template_name = "pages/trip_detail.html"
    context_object_name = "trip"

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def get_object(self, queryset=None):

        trip = super().get_object(
            queryset
        )

        # 今日の日付に合わせて
        # ステータスを更新
        sync_trip_status(
            trip
        )

        return trip

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # 今日の日付
        today = timezone.localdate()

        context["today"] = today

        # 旅を完了できるか
        context["can_complete_trip"] = (
            self.object.status == "traveling"
            and today >= self.object.end_date
        )

        # Trip全体の訪問先
        locations_by_country = {}

        for location in self.object.locations.all():

            if location.country not in locations_by_country:

                locations_by_country[
                    location.country
                ] = []

            if (
                location.region
                not in locations_by_country[
                    location.country
                ]
            ):

                locations_by_country[
                    location.country
                ].append(
                    location.region
                )

        context["locations_by_country"] = (
            locations_by_country
        )

        # Dayごとの訪問先・Spot・旅の記録フォーム
        days = self.object.days.all()

        for day in days:

            # -------------------------
            # Dayごとの訪問先
            # -------------------------

            day_locations = {}

            for location in day.locations.all():

                if location.country not in day_locations:

                    day_locations[
                        location.country
                    ] = []

                if (
                    location.region
                    not in day_locations[
                        location.country
                    ]
                ):

                    day_locations[
                        location.country
                    ].append(
                        location.region
                    )

            day.location_groups = (
                day_locations
            )

            # -------------------------
            # Spotの並び順
            # -------------------------

            # 1. 時間あり → 時刻順
            # 2. 時間未定 → 最後
            # 3. 同じ時間ならspot_order順
            day.spots_sorted = (
                day.spots.order_by(
                    F("time").asc(
                        nulls_last=True
                    ),
                    "spot_order",
                )
            )

            # -------------------------
            # Dayの写真・感想を
            # 登録できるか判定
            # -------------------------

            day.can_edit_record = False

            # 旅中の場合
            if self.object.status == "traveling":

                # 今日以前のDayだけ登録可能
                if day.date <= today:

                    day.can_edit_record = True

            # 旅完了の場合
            elif self.object.status == "completed":

                # 全Day登録可能
                day.can_edit_record = True

            # -------------------------
            # 登録可能なDayだけ
            # 写真・感想フォームを作成
            # -------------------------

            if day.can_edit_record:

                day.record_form = DayRecordForm(
                    instance=day,
                    prefix=f"day_{day.day_id}",
                )

        context["days"] = days

        return context


# Trip編集
class TripUpdateView(LoginRequiredMixin, UpdateView):

    model = Trip
    form_class = TripForm
    template_name = "pages/trip_create.html"

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def form_valid(self, form):

        new_start_date = form.cleaned_data[
            "start_date"
        ]

        new_end_date = form.cleaned_data[
            "end_date"
        ]

        # 新しい期間から外れるDay
        outside_days = self.object.days.exclude(
            date__range=(
                new_start_date,
                new_end_date,
            )
        )

        # 記入済みの範囲外Day
        filled_outside_days = []

        for day in outside_days:

            if day_has_data(day):

                filled_outside_days.append(
                    day
                )

        # 記入済みDayがある場合は、
        # まだTripを更新せず確認画面へ
        if filled_outside_days:

            category = form.cleaned_data.get(
                "category"
            )

            self.request.session[
                "pending_trip_update"
            ] = {
                "trip_id": self.object.trip_id,
                "title": form.cleaned_data[
                    "title"
                ],
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
            }

            return redirect(
                "trip_period_confirm",
                pk=self.object.trip_id,
            )

        # 記入済みDayがなければそのまま保存
        response = super().form_valid(
            form
        )

        # 新しい期間に合わせてDayを整理
        sync_trip_days(
            self.object
        )

        # 新しい期間に合わせて
        # ステータスも更新
        sync_trip_status(
            self.object
        )

        return response

    def get_success_url(self):

        return reverse_lazy(
            "trip_detail",
            kwargs={
                "pk": self.object.trip_id,
            },
        )


# Trip期間短縮確認
class TripPeriodConfirmView(LoginRequiredMixin, View):

    template_name = "pages/trip_period_confirm.html"

    def get_trip(self):

        return get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=self.request.user,
        )

    def get_pending_data(self):

        pending_data = self.request.session.get(
            "pending_trip_update"
        )

        if not pending_data:

            return None

        if (
            pending_data.get("trip_id")
            != self.kwargs["pk"]
        ):

            return None

        return pending_data

    def get(self, request, *args, **kwargs):

        trip = self.get_trip()

        pending_data = self.get_pending_data()

        if not pending_data:

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        new_start_date = date.fromisoformat(
            pending_data["start_date"]
        )

        new_end_date = date.fromisoformat(
            pending_data["end_date"]
        )

        outside_days = trip.days.exclude(
            date__range=(
                new_start_date,
                new_end_date,
            )
        )

        return render(
            request,
            self.template_name,
            {
                "trip": trip,
                "outside_days": outside_days,
                "new_start_date": new_start_date,
                "new_end_date": new_end_date,
            },
        )

    def post(self, request, *args, **kwargs):

        trip = self.get_trip()

        pending_data = self.get_pending_data()

        if not pending_data:

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        action = request.POST.get(
            "action"
        )

        # 期間を変更しない
        if action == "cancel":

            del request.session[
                "pending_trip_update"
            ]

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        # 範囲外Dayを削除して期間変更
        if action == "confirm":

            new_start_date = date.fromisoformat(
                pending_data[
                    "start_date"
                ]
            )

            new_end_date = date.fromisoformat(
                pending_data[
                    "end_date"
                ]
            )

            with transaction.atomic():

                # 新しい期間から外れるDayを削除
                outside_days = trip.days.exclude(
                    date__range=(
                        new_start_date,
                        new_end_date,
                    )
                )

                outside_days.delete()

                # Tripの内容を更新
                trip.title = pending_data[
                    "title"
                ]

                trip.category_id = pending_data[
                    "category_id"
                ]

                trip.start_date = (
                    new_start_date
                )

                trip.end_date = (
                    new_end_date
                )

                trip.save()

                # Day番号の整理と不足Dayの生成
                sync_trip_days(
                    trip
                )

                # 新しい期間に合わせて
                # ステータスも更新
                sync_trip_status(
                    trip
                )

            del request.session[
                "pending_trip_update"
            ]

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        return redirect(
            "trip_period_confirm",
            pk=trip.trip_id,
        )


# コース作成完了
class TripStatusUpdateView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):

        trip = get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=request.user,
        )

        # 作成中のTripだけ処理する
        if trip.status != "draft":

            return redirect(
                "trip_detail",
                pk=trip.trip_id,
            )

        action = request.POST.get(
            "action"
        )

        if action == "complete_plan":

            today = timezone.localdate()

            # 旅行開始日前なら出発待ち
            if today < trip.start_date:

                trip.status = "planned"

            # 旅行開始日以降なら旅中
            else:

                trip.status = "traveling"

            trip.save(
                update_fields=[
                    "status"
                ]
            )

        return redirect(
            "trip_detail",
            pk=trip.trip_id,
        )


# Trip完了
class TripCompleteView(LoginRequiredMixin, UpdateView):

    model = Trip
    form_class = TripCompleteForm
    template_name = "pages/trip_complete.html"

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def dispatch(self, request, *args, **kwargs):

        self.trip = get_object_or_404(
            Trip,
            pk=self.kwargs["pk"],
            user=request.user,
        )

        # 現在の日付に合わせて
        # ステータスを更新
        sync_trip_status(
            self.trip
        )

        today = timezone.localdate()

        # 旅中以外は完了画面を開けない
        if self.trip.status != "traveling":

            return redirect(
                "trip_detail",
                pk=self.trip.trip_id,
            )

        # 旅行最終日前は完了画面を開けない
        if today < self.trip.end_date:

            return redirect(
                "trip_detail",
                pk=self.trip.trip_id,
            )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["trip"] = self.object

        return context

    def form_valid(self, form):

        # 「旅を完了する」を押した場合だけ
        # completedへ変更
        form.instance.status = "completed"

        return super().form_valid(
            form
        )

    def get_success_url(self):

        return reverse_lazy(
            "trip_detail",
            kwargs={
                "pk": self.object.trip_id,
            },
        )


# Trip削除
class TripDeleteView(LoginRequiredMixin, DeleteView):

    model = Trip
    template_name = "pages/trip_delete.html"

    def get_queryset(self):

        return Trip.objects.filter(
            user=self.request.user
        )

    def get_success_url(self):

        return reverse_lazy(
            "trip_list"
        )