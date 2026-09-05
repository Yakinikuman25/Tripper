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
#
# 計画情報・旅の記録・費用情報など、
# 何か1つでも登録されていればTrue
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
        or day.planned_amount is not None
        or day.actual_cost is not None
        or day.actual_amount is not None
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
# 旅行全体の実費を計算する関数
#
# 1. Trip.total_cost が
# 手入力されている場合
# → その金額を最優先
#
# 2. Trip.total_cost が未入力の場合
#
# Trip全体費用の実際支払額
#
# ＋
#
# 各Dayの
# ・自由実費
# ・Day実際支払額
# ・Schedule実際支払額
#
# を合計する
#
# -----------------------------------------
# 自由実費の採用ルール
#
# day.actual_cost がある
# → 手入力された自由実費を使用
#
# day.actual_cost がなく
# DayExpenseがある
# → DayExpense合計を使用
#
# actual_cost と DayExpense は
# 同時に加算しない
# -----------------------------------------
#
# 3. 実費が1件もない場合
# → None
# =========================================

def calculate_trip_actual_total(
    trip,
):

    # =====================================
    # Trip全体の手入力金額を最優先
    # =====================================

    if (
        trip.total_cost
        is not None
    ):

        return (
            trip.total_cost
        )


    actual_total = 0

    has_actual_cost = (
        False
    )


    # =====================================
    # Trip全体費用
    #
    # TripExpense.actual_amount
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

            has_actual_cost = (
                True
            )


    # =====================================
    # Dayごとの実費
    # =====================================

    for day in (
        trip.days.all()
    ):


        # =====================================
        # 自由実費
        #
        # actual_costがある場合は
        # 手入力値を採用
        #
        # DayExpenseとは二重加算しない
        # =====================================

        if (
            day.actual_cost
            is not None
        ):

            actual_total += (
                day.actual_cost
            )

            has_actual_cost = (
                True
            )


        # =====================================
        # 自由実費が未入力の場合
        #
        # DayExpense合計を
        # 自由実費として採用
        # =====================================

        else:

            day_expense_total = 0

            has_day_expense = (
                False
            )


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

                    has_day_expense = (
                        True
                    )


            if has_day_expense:

                actual_total += (
                    day_expense_total
                )

                has_actual_cost = (
                    True
                )


        # =====================================
        # Day実際支払額
        #
        # 例：
        # ・1日ツアー
        # ・1日レンタカー
        # =====================================

        if (
            day.actual_amount
            is not None
        ):

            actual_total += (
                day.actual_amount
            )

            has_actual_cost = (
                True
            )


        # =====================================
        # Schedule実際支払額
        #
        # 例：
        # ・ホテル
        # ・乗馬
        # ・バス
        # ・アクティビティ
        # =====================================

        for schedule in (
            day.schedules.all()
        ):

            if (
                schedule.actual_amount
                is not None
            ):

                actual_total += (
                    schedule.actual_amount
                )

                has_actual_cost = (
                    True
                )


    # =====================================
    # 実費が1件もない場合
    # =====================================

    if not has_actual_cost:

        return None


    return actual_total



# =========================================
# Tripカード表示用データを設定する関数
#
# 共通Tripカードで使用する
# ・旅行日数
# ・国ごとにまとめた訪問先
#
# 必要な場合は
# ・実費合計
#
# も設定する
# =========================================

def prepare_trip_card_data(
    trip,
    include_actual_total=False,
):

    # =====================================
    # 旅行日数
    #
    # 開始日と終了日を含めるため
    # +1日する
    # =====================================

    trip.trip_days = (
        trip.end_date
        - trip.start_date
    ).days + 1


    # =====================================
    # 訪問先を国ごとにまとめる
    # =====================================

    locations_by_country = {}


    for location in (
        trip.locations.all()
    ):

        if (
            location.country
            not in locations_by_country
        ):

            locations_by_country[
                location.country
            ] = []


        if (
            location.region
            and location.region
            not in locations_by_country[
                location.country
            ]
        ):

            locations_by_country[
                location.country
            ].append(
                location.region
            )


    trip.locations_by_country = (
        locations_by_country
    )


    # =====================================
    # 実費合計
    #
    # みんなのTrip・保存Tripなど、
    # 必要な場合だけ計算する
    # =====================================

    if include_actual_total:

        trip.final_actual_total = (
            calculate_trip_actual_total(
                trip
            )
        )


    return trip



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