from django.conf import settings
from django.db import models

from .category_models import Category


class Trip(models.Model):

    STATUS_CHOICES = [
        ("draft", "作成中"),
        ("planned", "出発待ち"),
        ("traveling", "旅中"),
        ("completed", "旅完了"),
    ]

    trip_id = models.AutoField(
        primary_key=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trips",
        verbose_name="ユーザー",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trips",
        verbose_name="カテゴリ",
    )

    title = models.CharField(
        max_length=100,
        verbose_name="タイトル",
    )

    main_media = models.ImageField(
        upload_to="trip_media/",
        blank=True,
        verbose_name="代表写真",
    )

    start_date = models.DateField(
        verbose_name="旅行開始日",
    )

    end_date = models.DateField(
        verbose_name="旅行終了日",
    )

    total_cost = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="実際の合計費用",
    )

    # =====================================
    # 旅行計画用のメモ
    # =====================================

    memo = models.TextField(
        blank=True,
        verbose_name="メモ",
    )

    # =====================================
    # 旅完了後の概要・感想
    # =====================================

    overview = models.TextField(
        blank=True,
        verbose_name="概要・感想",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="ステータス",
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name="公開設定",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時",
    )

    class Meta:
        db_table = "trips"
        verbose_name = "Trip"
        verbose_name_plural = "Trip"

    def __str__(self):
        return self.title