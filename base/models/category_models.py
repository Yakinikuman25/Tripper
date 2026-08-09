from django.db import models


class Category(models.Model):
    category_id = models.AutoField(
        primary_key=True
    )

    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="カテゴリ名"
    )

    class Meta:
        db_table = "categories"
        verbose_name = "カテゴリ"
        verbose_name_plural = "カテゴリ"

    def __str__(self):
        return self.name