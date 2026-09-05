from django.db import models
from django_countries.fields import CountryField

from .trip_models import Trip


# =========================================
# Location
#
# Trip全体で使用する訪問先を管理する
#
# 例：
# ・日本 / 東京
# ・韓国 / 仁川
# ・カザフスタン / アルマトイ
#
# Dayごとの訪問順は
# DayLocationで管理する
# =========================================

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

    # =====================================
    # 国
    #
    # 実在する国のみ登録可能
    # DBにはISO国コードを保存
    #
    # 例：
    # 日本         → JP
    # キルギス     → KG
    # カザフスタン → KZ
    # =====================================

    country = CountryField(
        verbose_name="国",
    )

    # =====================================
    # 地域・都市
    #
    # 今まで通り自由入力
    #
    # 例：
    # 東京
    # カラコル
    # アルマトイ
    # =====================================

    region = models.CharField(
        max_length=50,
        verbose_name="地域",
    )


    class Meta:

        db_table = "locations"

        verbose_name = "訪問先"
        verbose_name_plural = "訪問先"

        constraints = [

            # -------------------------
            # 同じTripの中で
            # 同じ国・地域を重複登録しない
            # -------------------------

            models.UniqueConstraint(
                fields=[
                    "trip",
                    "country",
                    "region",
                ],
                name="unique_trip_location",
            )
        ]


    def __str__(self):

        return (
            f"{self.get_country_display()} / "
            f"{self.region}"
        )