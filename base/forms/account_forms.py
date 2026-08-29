from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


# =========================================
# ユーザー作成フォーム
# =========================================

class UserCreationForm(forms.ModelForm):

    password = forms.CharField(
        label="パスワード",
        widget=forms.PasswordInput
    )

    class Meta:

        model = User

        fields = (
            "username",
            "email",
            "password",
        )

    def save(
        self,
        commit=True,
    ):

        user = super().save(
            commit=False
        )

        # =====================================
        # パスワードを暗号化して保存
        # =====================================

        user.set_password(
            self.cleaned_data[
                "password"
            ]
        )

        if commit:

            user.save()

        return user


# =========================================
# メールアドレス変更フォーム
# =========================================

class EmailUpdateForm(forms.ModelForm):

    class Meta:

        model = User

        fields = (
            "email",
        )

        labels = {
            "email": "メールアドレス",
        }

        widgets = {

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "メールアドレスを入力してください"
                    ),
                }
            ),
        }