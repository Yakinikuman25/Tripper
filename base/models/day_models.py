from django.core.validators import MinValueValidator
from django.db import models

from .trip_models import Trip
from .location_models import Location


# =========================================
# Day
# =========================================

class Day(models.Model):

    day_id = models.AutoField(
        primary_key=True
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="days",
        verbose_name="Trip",
    )

    # =====================================
    # 訪問先
    #
    # DayLocationを中間モデルとして使用し、
    # Day内での訪問順も管理する
    # =====================================

    locations = models.ManyToManyField(
        Location,
        through="DayLocation",
        through_fields=(
            "day",
            "location",
        ),
        related_name="days",
        verbose_name="ロケーション",
        blank=True,
    )

    date = models.DateField(
        verbose_name="日付",
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Dayタイトル",
    )

    # =====================================
    # 旅行計画用のメモ
    # =====================================

    memo = models.TextField(
        blank=True,
        verbose_name="メモ",
    )

    # =====================================
    # 旅中・旅完了後の記録
    # =====================================

    content = models.TextField(
        blank=True,
        verbose_name="内容",
    )

    media = models.ImageField(
        upload_to="day_media/",
        blank=True,
        verbose_name="写真",
    )

    # =====================================
    # 自由費
    #
    # 食事・コンビニ・細かな交通費など
    #
    # budget
    # → その日に使う予定の自由費
    #
    # actual_cost
    # → DayExpenseなどを基にした
    #   自由費の実績
    # =====================================

    budget = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="自由費予算",
    )

    actual_cost = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="自由費実績",
    )

    # =====================================
    # Day単位の費用
    #
    # 例：
    # ・1日ツアー
    # ・1日レンタカー
    # ・そのDay全体にかかる費用
    #
    # Schedule単位ではなく
    # Dayそのものに属する費用を管理する
    # =====================================

    planned_amount = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="Day予定金額",
    )

    actual_amount = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="Day実際支払額",
    )

    day_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "days"

        verbose_name = "Day"
        verbose_name_plural = "Day"

        ordering = [
            "day_order"
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "trip",
                    "date",
                ],
                name="unique_trip_day_date",
            )
        ]

    def __str__(self):

        return (
            f"{self.trip.title} "
            f"- Day {self.day_order}"
        )


# =========================================
# DayLocation
#
# DayとLocationの中間モデル
#
# Day内での訪問順を管理する
#
# 例：
#
# Day1
# 1. 東京
# 2. 仁川
#
# Day2
# 1. 仁川
# 2. アルマトイ
# =========================================

class DayLocation(models.Model):

    day_location_id = models.AutoField(
        primary_key=True
    )

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="day_locations",
        verbose_name="Day",
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="day_locations",
        verbose_name="訪問先",
    )

    # =====================================
    # そのDay内での訪問順
    #
    # 1 = 最初
    # 2 = 2番目
    # 3 = 3番目...
    # =====================================

    location_order = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="訪問順",
    )

    class Meta:

        db_table = "day_locations"

        verbose_name = "Day訪問先"
        verbose_name_plural = "Day訪問先"

        ordering = [
            "location_order"
        ]

        constraints = [

            # -------------------------
            # 同じDayに
            # 同じLocationを重複登録しない
            # -------------------------

            models.UniqueConstraint(
                fields=[
                    "day",
                    "location",
                ],
                name="unique_day_location",
            ),

            # -------------------------
            # 同じDayの中で
            # 同じ訪問順を重複させない
            # -------------------------

            models.UniqueConstraint(
                fields=[
                    "day",
                    "location_order",
                ],
                name="unique_day_location_order",
            ),
        ]

    def __str__(self):

        return (
            f"{self.day} "
            f"- {self.location_order}. "
            f"{self.location}"
        )