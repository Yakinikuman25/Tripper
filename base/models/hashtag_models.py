from django.db import models


class Hashtag(models.Model):
    hashtag_id = models.AutoField(
        primary_key=True
    )

    name = models.CharField(
        max_length=50,
        verbose_name="タグ名",
    )

    class Meta:
        db_table = "hashtags"
        verbose_name = "ハッシュタグ"
        verbose_name_plural = "ハッシュタグ"

    def __str__(self):
        return self.name