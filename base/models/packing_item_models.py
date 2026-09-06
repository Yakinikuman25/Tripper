from django.db import models

from .trip_models import Trip


class PackingItem(models.Model):

    # =====================================
    # バッグ区分
    # =====================================

    BAG_TYPE_CHOICES = [
        ("large", "大きなバッグ"),
        ("small", "小さなバッグ"),
        ("other", "その他"),
    ]


    packing_item_id = models.AutoField(
        primary_key=True
    )


    # =====================================
    # 対象Trip
    #
    # Tripが削除された場合は
    # 持ち物も削除する
    # =====================================

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name="packing_items",
        verbose_name="Trip",
    )


    # =====================================
    # バッグ区分
    #
    # large
    # → 大きなバッグ
    #
    # small
    # → 小さなバッグ
    #
    # other
    # → その他
    # =====================================

    bag_type = models.CharField(
        max_length=20,
        choices=BAG_TYPE_CHOICES,
        default="large",
        verbose_name="バッグ区分",
    )


    # =====================================
    # 持ち物名
    #
    # 例：
    # アウター
    # パスポート
    # モバイルバッテリー
    # =====================================

    name = models.CharField(
        max_length=100,
        verbose_name="持ち物名",
    )


    # =====================================
    # 個数
    #
    # 個数を管理したいものだけ入力する
    #
    # 例：
    # Tシャツ 3個
    #
    # パスポートのように
    # 個数表示が不要なものは未入力でよい
    # =====================================

    quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="個数",
    )


    # =====================================
    # 準備済み
    #
    # False
    # → 未準備
    #
    # True
    # → 準備済み
    # =====================================

    is_packed = models.BooleanField(
        default=False,
        verbose_name="準備済み",
    )


    # =====================================
    # 表示順
    #
    # 同じバッグ区分の中で
    # 持ち物を並べるために使用する
    # =====================================

    item_order = models.PositiveIntegerField(
        default=0,
        verbose_name="表示順",
    )


    # =====================================
    # 作成日時・更新日時
    # =====================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="作成日時",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新日時",
    )


    class Meta:
        db_table = "packing_items"
        verbose_name = "持ち物"
        verbose_name_plural = "持ち物"

        ordering = [
            "bag_type",
            "item_order",
            "packing_item_id",
        ]


    def __str__(self):
        return self.name