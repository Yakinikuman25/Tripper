from django.db import models

from .day_models import Day


class Schedule(models.Model):

    schedule_id = models.AutoField(
        primary_key=True
    )

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name="Day",
    )

    # =====================================
    # 開始時間
    # =====================================

    start_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="開始時間",
    )

    # =====================================
    # 終了時間
    # =====================================

    end_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="終了時間",
    )

    # =====================================
    # スケジュール名
    # =====================================

    name = models.CharField(
        max_length=100,
        verbose_name="スケジュール名",
    )

    # =====================================
    # メモ
    # =====================================

    memo = models.TextField(
        blank=True,
        verbose_name="メモ",
    )

    # =====================================
    # 表示順
    # =====================================

    schedule_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "schedules"

        verbose_name = "スケジュール"

        verbose_name_plural = "スケジュール"

        ordering = [
            "schedule_order",
        ]

    def __str__(self):

        return (
            f"{self.day} - "
            f"{self.name}"
        )