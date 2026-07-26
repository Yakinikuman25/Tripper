from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        verbose_name="メールアドレス"
    )

    class Meta:
        db_table = "users"
        verbose_name = "ユーザー"
        verbose_name_plural = "ユーザー"

    def __str__(self):
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="ユーザー",
    )

    profile_image = models.ImageField(
    upload_to="profile_images/",
    default="profile_images/default.png",
    blank=True,
    verbose_name="プロフィール画像",
    )

    introduction = models.TextField(
        blank=True,
        verbose_name="自己紹介",
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
        db_table = "profiles"
        verbose_name = "プロフィール"
        verbose_name_plural = "プロフィール"

    def __str__(self):
        return self.user.username