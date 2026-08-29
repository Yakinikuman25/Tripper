from django.conf import settings
from django.db import models

from .trip_models import Trip


class TripSave(models.Model):

    trip_save_id = models.AutoField(
        primary_key=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trip_saves",
        verbose_name="保存したユーザー",
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="saves",
        verbose_name="保存したTrip",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="保存日時",
    )

    class Meta:
        db_table = "trip_saves"
        verbose_name = "Trip保存"
        verbose_name_plural = "Trip保存"
        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "trip",
                ],
                name="unique_user_trip_save",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.trip}"