from django.db import models

from .trip_models import Trip


class Location(models.Model):
    location_id = models.AutoField(
        primary_key=True
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="locations",
        verbose_name="Trip",
    )

    country = models.CharField(
        max_length=50,
        verbose_name="国",
    )

    region = models.CharField(
        max_length=50,
        verbose_name="地域",
    )

    class Meta:
        db_table = "locations"
        verbose_name = "訪問先"
        verbose_name_plural = "訪問先"

        constraints = [
            models.UniqueConstraint(
                fields=["trip", "country", "region"],
                name="unique_trip_location",
            )
        ]

    def __str__(self):
        return f"{self.country} / {self.region}"