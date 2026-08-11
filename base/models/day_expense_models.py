from django.core.validators import MinValueValidator
from django.db import models

from .day_models import Day


class DayExpense(models.Model):

    day_expense_id = models.AutoField(
        primary_key=True
    )

    day = models.ForeignKey(
        Day,
        on_delete=models.CASCADE,
        related_name="day_expenses",
        verbose_name="Day",
    )

    name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="何に使ったか",
    )

    amount = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1)
        ],
        verbose_name="金額",
    )

    expense_order = models.IntegerField(
        default=0,
        verbose_name="表示順",
    )

    class Meta:

        db_table = "day_expenses"

        verbose_name = "Day費用"
        verbose_name_plural = "Day費用"

        ordering = [
            "expense_order"
        ]

    def __str__(self):

        if self.name:
            return f"{self.day} - {self.name}"

        return f"{self.day} - Day費用"