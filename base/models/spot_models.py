from django.db import models

from .day_models import Day


class Spot(models.Model):

    spot_id = models.AutoField(
        primary_key=True
    )

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="spots",
        verbose_name="Day",
    )

    time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="時間",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="場所名",
    )

    url = models.URLField(
        max_length=255,
        blank=True,
        verbose_name="URL",
    )

    memo = models.TextField(
        blank=True,
        verbose_name="メモ",
    )

    spot_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "spots"

        verbose_name = "Spot"

        verbose_name_plural = "Spot"

        ordering = [
            "spot_order",
        ]

    def __str__(self):

        return f"{self.day} - {self.name}"