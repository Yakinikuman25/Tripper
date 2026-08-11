from django.core.validators import MinValueValidator
from django.db import models

from .trip_models import Trip


class TripExpense(models.Model):

    trip_expense_id = models.AutoField(
        primary_key=True
    )

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="trip_expenses",
        verbose_name="Trip",
    )

    name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="費用名",
    )

    planned_amount = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="予定金額",
    )

    actual_amount = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="実際支払額",
    )

    memo = models.TextField(
        blank=True,
        verbose_name="メモ",
    )

    expense_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "trip_expenses"

        verbose_name = "Trip共通費用"
        verbose_name_plural = "Trip共通費用"

        ordering = [
            "expense_order"
        ]

    def __str__(self):

        if self.name:
            return f"{self.trip.title} - {self.name}"

        return f"{self.trip.title} - Trip共通費用"