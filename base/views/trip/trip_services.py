from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from base.models import (
    Day,
    Hashtag,
    TripReferenceUrl,
    TripHashtag,
    TripExpenseReferenceUrl,
)


# =========================================
# Trip期間に合わせてDayを作成・整理する関数
# =========================================

def sync_trip_days(
    trip,
):

    current_date = (
        trip.start_date
    )

    day_order = 1

    while (
        current_date
        <= trip.end_date
    ):

        day, created = (
            Day.objects.get_or_create(
                trip=trip,
                date=current_date,
                defaults={
                    "day_order": day_order,
                },
            )
        )

        # =====================================
        # 既存Dayの場合も
        # Day番号を更新
        # =====================================

        if (
            day.day_order
            != day_order
        ):

            day.day_order = (
                day_order
            )

            day.save(
                update_fields=[
                    "day_order",
                ]
            )

        current_date += timedelta(
            days=1
        )

        day_order += 1

    # =====================================
    # Trip期間外のDayを取得
    # =====================================

    outside_days = (
        trip.days.exclude(
            date__range=(
                trip.start_date,
                trip.end_date,
            )
        )
    )

    # =====================================
    # ここまで来る時点では
    # 削除してよいDayなので削除
    # =====================================

    outside_days.delete()

    # =====================================
    # DayLocationから使われなくなった
    # Locationを削除
    # =====================================

    trip.locations.filter(
        day_locations__isnull=True
    ).delete()


# =========================================
# Tripのハッシュタグを保存・整理する関数
# =========================================

def sync_trip_hashtags(
    trip,
    hashtag_names,
):

    # =====================================
    # 現在のTripとの紐付けを
    # 一度すべて削除
    # =====================================

    trip.trip_hashtags.all().delete()

    # =====================================
    # 入力されたハッシュタグを登録
    # =====================================

    for hashtag_name in (
        hashtag_names
    ):

        hashtag, created = (
            Hashtag.objects.get_or_create(
                name=hashtag_name
            )
        )

        TripHashtag.objects.get_or_create(
            trip=trip,
            hashtag=hashtag,
        )


# =========================================
# Trip参考URL FormSetから
# 保存対象データを取り出す関数
# =========================================

def get_trip_reference_url_items(
    formset,
):

    reference_url_items = []

    for url_form in (
        formset.forms
    ):

        cleaned_data = getattr(
            url_form,
            "cleaned_data",
            None,
        )

        if not cleaned_data:

            continue

        if cleaned_data.get(
            "DELETE"
        ):

            continue

        url = (
            cleaned_data.get(
                "url",
                "",
            )
            or ""
        ).strip()

        title = (
            cleaned_data.get(
                "title",
                "",
            )
            or ""
        ).strip()

        # =====================================
        # URLが空欄の追加フォームは
        # 保存しない
        # =====================================

        if not url:

            continue

        reference_url_items.append(
            {
                "title": title,
                "url": url,
            }
        )

    return reference_url_items


# =========================================
# Trip参考URLを保存・整理する関数
#
# 編集時は現在の参考URLを一度削除して、
# フォーム上に残っているURLを
# 表示順どおりに作り直す
# =========================================

def sync_trip_reference_urls(
    trip,
    reference_url_items,
):

    trip.reference_urls.all().delete()

    for url_order, item in enumerate(
        reference_url_items,
        start=1,
    ):

        TripReferenceUrl.objects.create(
            trip=trip,
            title=item.get(
                "title",
                "",
            ),
            url=item["url"],
            url_order=url_order,
        )


# =========================================
# Trip全体費用参考URL FormSetから
# 保存対象データを取り出す関数
# =========================================

def get_trip_expense_reference_url_items(
    formset,
):

    reference_url_items = []

    for url_form in (
        formset.forms
    ):

        cleaned_data = getattr(
            url_form,
            "cleaned_data",
            None,
        )

        if not cleaned_data:

            continue

        if cleaned_data.get(
            "DELETE"
        ):

            continue

        title = (
            cleaned_data.get(
                "title",
                "",
            )
            or ""
        ).strip()

        url = (
            cleaned_data.get(
                "url",
                "",
            )
            or ""
        ).strip()

        # =====================================
        # URLが空欄の追加フォームは
        # 保存しない
        # =====================================

        if not url:

            continue

        reference_url_items.append(
            {
                "title": title,
                "url": url,
            }
        )

    return reference_url_items


# =========================================
# Trip全体費用参考URLを保存・整理する関数
#
# 現在の参考URLを一度削除して、
# フォーム上に残っているURLを
# 表示順どおりに作り直す
# =========================================

def sync_trip_expense_reference_urls(
    trip_expense,
    reference_url_items,
):

    trip_expense.reference_urls.all().delete()

    for url_order, item in enumerate(
        reference_url_items,
        start=1,
    ):

        TripExpenseReferenceUrl.objects.create(
            trip_expense=trip_expense,
            title=item.get(
                "title",
                "",
            ),
            url=item["url"],
            url_order=url_order,
        )


# =========================================
# Dayに何か記入されているか確認する関数
# =========================================

def day_has_data(
    day,
):

    return (
        bool(day.title)
        or bool(day.memo)
        or bool(day.content)
        or bool(day.media)
        or day.budget is not None
        or day.actual_cost is not None
        or day.locations.exists()
        or day.reference_urls.exists()
        or day.schedules.exists()
        or day.day_expenses.exists()
    )


# =========================================
# Tripの日付に合わせて
# ステータスを更新する関数
# =========================================

def sync_trip_status(
    trip,
):

    today = (
        timezone.localdate()
    )

    # =====================================
    # 作成中
    #
    # 「コース作成完了」を押すまで
    # 自動変更しない
    # =====================================

    if (
        trip.status
        == "draft"
    ):

        return

    # =====================================
    # 旅完了は自動変更しない
    # =====================================

    if (
        trip.status
        == "completed"
    ):

        return

    # =====================================
    # 旅行開始日前
    # =====================================

    if (
        today
        < trip.start_date
    ):

        new_status = (
            "planned"
        )

    # =====================================
    # 旅行開始日以降
    # =====================================

    else:

        new_status = (
            "traveling"
        )

    # =====================================
    # 現在のステータスと違う場合だけ更新
    # =====================================

    if (
        trip.status
        != new_status
    ):

        trip.status = (
            new_status
        )

        trip.save(
            update_fields=[
                "status",
            ]
        )


# =========================================
# 旅行全体の実際費用を計算する関数
#
# 1. Trip.total_cost が手入力されている場合
#    → その金額を最優先
#
# 2. Trip.total_cost が未入力の場合
#    → Trip全体費用の実績合計
#      ＋ 各Dayの採用実績
#
# Dayの採用実績
# ・day.actual_cost がある場合
#   → day.actual_cost
#
# ・day.actual_cost がなく
#   DayExpenseがある場合
#   → DayExpenseの合計
#
# 3. 実績が1件もない場合
#    → None
# =========================================

def calculate_trip_actual_total(
    trip,
):

    # =====================================
    # 手入力されたTrip全体費用を最優先
    # =====================================

    if (
        trip.total_cost
        is not None
    ):

        return (
            trip.total_cost
        )

    actual_total = 0

    has_actual_cost = False

    # =====================================
    # Trip全体費用の実績
    # =====================================

    for expense in (
        trip.trip_expenses.all()
    ):

        if (
            expense.actual_amount
            is not None
        ):

            actual_total += (
                expense.actual_amount
            )

            has_actual_cost = True

    # =====================================
    # Day実績
    # =====================================

    for day in (
        trip.days.all()
    ):

        # =====================================
        # Day全体の実際費用がある場合
        # =====================================

        if (
            day.actual_cost
            is not None
        ):

            actual_total += (
                day.actual_cost
            )

            has_actual_cost = True

        # =====================================
        # Day全体の実際費用がない場合
        #
        # → DayExpenseを合計
        # =====================================

        else:

            day_expense_total = 0

            has_day_expense = False

            for expense in (
                day.day_expenses.all()
            ):

                if (
                    expense.amount
                    is not None
                ):

                    day_expense_total += (
                        expense.amount
                    )

                    has_day_expense = True

            if has_day_expense:

                actual_total += (
                    day_expense_total
                )

                has_actual_cost = True

    # =====================================
    # 実績が1件もない場合
    # =====================================

    if not has_actual_cost:

        return None

    return actual_total


# =========================================
# Trip詳細画面のURLを作る関数
# =========================================

def get_trip_detail_url(
    trip,
    edit_mode=False,
):

    url = reverse(
        "trip_detail",
        kwargs={
            "pk": trip.trip_id,
        },
    )

    if edit_mode:

        url += "?edit=1"

    return url