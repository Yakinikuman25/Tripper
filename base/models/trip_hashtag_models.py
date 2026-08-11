from django.db import models

from .trip_models import Trip
from .hashtag_models import Hashtag


class TripHashtag(models.Model):

    trip_hashtag_id = models.AutoField(
        primary_key=True
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="trip_hashtags",
        verbose_name="Trip",
    )

    hashtag = models.ForeignKey(
        Hashtag,
        on_delete=models.CASCADE,
        related_name="trip_hashtags",
        verbose_name="ハッシュタグ",
    )

    class Meta:
        db_table = "trip_hashtags"
        verbose_name = "Tripハッシュタグ"
        verbose_name_plural = "Tripハッシュタグ"

        constraints = [
            models.UniqueConstraint(
                fields=["trip", "hashtag"],
                name="unique_trip_hashtag",
            )
        ]

    def __str__(self):
        return f"{self.trip.title} - #{self.hashtag.name}"