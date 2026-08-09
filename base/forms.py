from django import forms
from django.contrib.auth import get_user_model

from base.models import Trip, Day, Spot


User = get_user_model()


# ユーザー作成フォーム
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

    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        # パスワードを暗号化して保存
        user.set_password(
            self.cleaned_data["password"]
        )

        if commit:
            user.save()

        return user


# メールアドレス変更フォーム
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
                    "placeholder": "メールアドレスを入力してください",
                }
            )
        }


# Trip作成・編集フォーム
class TripForm(forms.ModelForm):

    class Meta:

        model = Trip

        fields = (
            "category",
            "title",
            "start_date",
            "end_date",
        )

        widgets = {

            "start_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),

            "end_date": forms.DateInput(
                attrs={
                    "type": "date",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        start_date = cleaned_data.get(
            "start_date"
        )

        end_date = cleaned_data.get(
            "end_date"
        )

        # 日付が入力されていない場合はここでは判定しない
        if not start_date or not end_date:

            return cleaned_data

        # 終了日が開始日より前になっていないか
        if end_date < start_date:

            self.add_error(
                "end_date",
                "旅行終了日は旅行開始日以降にしてください。"
            )

        return cleaned_data


# Day編集フォーム
class DayForm(forms.ModelForm):

    class Meta:

        model = Day

        fields = (
            "title",
        )

        labels = {
            "title": "Dayタイトル",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Dayタイトルを入力してください",
                }
            ),
        }


# Day旅の記録フォーム
class DayRecordForm(forms.ModelForm):

    class Meta:

        model = Day

        fields = (
            "media",
            "content",
        )

        labels = {
            "media": "写真",
            "content": "感想",
        }

        widgets = {

            "media": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "この日の感想を入力してください",
                }
            ),
        }


# Trip完了フォーム
class TripCompleteForm(forms.ModelForm):

    class Meta:

        model = Trip

        fields = (
            "main_media",
            "overview",
            "is_public",
        )

        labels = {
            "main_media": "代表写真",
            "overview": "感想",
            "is_public": "公開設定",
        }

        widgets = {

            "main_media": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "overview": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "今回の旅の感想を入力してください",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        main_media = cleaned_data.get(
            "main_media"
        )

        overview = cleaned_data.get(
            "overview"
        )

        is_public = cleaned_data.get(
            "is_public"
        )

        # 公開する場合だけ
        # 代表写真と感想を必須にする
        if is_public:

            if not main_media:

                self.add_error(
                    "main_media",
                    "公開する場合は代表写真を登録してください。"
                )

            if not overview:

                self.add_error(
                    "overview",
                    "公開する場合は感想を入力してください。"
                )

        return cleaned_data


# Spot作成・編集フォーム
class SpotForm(forms.ModelForm):

    class Meta:

        model = Spot

        fields = (
            "time",
            "name",
            "url",
            "memo",
        )

        labels = {
            "time": "時間",
            "name": "場所名",
            "url": "URL",
            "memo": "メモ",
        }

        widgets = {

            "time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "場所名を入力してください",
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),

            "memo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "メモを入力してください",
                }
            ),
        }