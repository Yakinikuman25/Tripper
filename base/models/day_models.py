from django.db import models

from .trip_models import Trip
from .location_models import Location


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

    locations = models.ManyToManyField(
        Location,
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

    content = models.TextField(
        blank=True,
        verbose_name="内容",
    )

    media = models.ImageField(
        upload_to="day_media/",
        blank=True,
        verbose_name="写真",
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

        return f"{self.trip.title} - Day {self.day_order}"