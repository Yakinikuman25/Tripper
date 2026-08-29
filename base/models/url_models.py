from django.db import models

from .trip_models import Trip
from .day_models import Day
from .spot_models import Spot
from .trip_expense_models import TripExpense


# =========================================
# Trip参考URL
# =========================================

class TripReferenceUrl(models.Model):

    trip_reference_url_id = models.AutoField(
        primary_key=True
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="reference_urls",
        verbose_name="Trip",
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="参考URL名",
    )

    url = models.URLField(
        max_length=500,
        verbose_name="参考URL",
    )

    url_order = models.PositiveIntegerField(
        default=1,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "trip_reference_urls"

        verbose_name = "Trip参考URL"

        verbose_name_plural = "Trip参考URL"

        ordering = [
            "url_order",
        ]

    def __str__(self):

        return (
            f"{self.trip} - "
            f"{self.title or self.url}"
        )


# =========================================
# Day参考URL
# =========================================

class DayReferenceUrl(models.Model):

    day_reference_url_id = models.AutoField(
        primary_key=True
    )

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="reference_urls",
        verbose_name="Day",
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="参考URL名",
    )

    url = models.URLField(
        max_length=500,
        verbose_name="参考URL",
    )

    url_order = models.PositiveIntegerField(
        default=1,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "day_reference_urls"

        verbose_name = "Day参考URL"

        verbose_name_plural = "Day参考URL"

        ordering = [
            "url_order",
        ]

    def __str__(self):

        return (
            f"{self.day} - "
            f"{self.title or self.url}"
        )


# =========================================
# スケジュール参考URL
#
# 現在はモデル名がSpotのため
# SpotReferenceUrlとして作成
# =========================================

class SpotReferenceUrl(models.Model):

    spot_reference_url_id = models.AutoField(
        primary_key=True
    )

    spot = models.ForeignKey(
        Spot,
        on_delete=models.CASCADE,
        related_name="reference_urls",
        verbose_name="スケジュール",
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="参考URL名",
    )

    url = models.URLField(
        max_length=500,
        verbose_name="参考URL",
    )

    url_order = models.PositiveIntegerField(
        default=1,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "spot_reference_urls"

        verbose_name = "スケジュール参考URL"

        verbose_name_plural = "スケジュール参考URL"

        ordering = [
            "url_order",
        ]

    def __str__(self):

        return (
            f"{self.spot} - "
            f"{self.title or self.url}"
        )


# =========================================
# 全体費用参考URL
# =========================================

class TripExpenseReferenceUrl(models.Model):

    trip_expense_reference_url_id = (
        models.AutoField(
            primary_key=True
        )
    )

    trip_expense = models.ForeignKey(
        TripExpense,
        on_delete=models.CASCADE,
        related_name="reference_urls",
        verbose_name="全体費用",
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="参考URL名",
    )

    url = models.URLField(
        max_length=500,
        verbose_name="参考URL",
    )

    url_order = models.PositiveIntegerField(
        default=1,
        verbose_name="表示順",
    )

    class Meta:

        db_table = (
            "trip_expense_reference_urls"
        )

        verbose_name = (
            "全体費用参考URL"
        )

        verbose_name_plural = (
            "全体費用参考URL"
        )

        ordering = [
            "url_order",
        ]

    def __str__(self):

        return (
            f"{self.trip_expense} - "
            f"{self.title or self.url}"
        )