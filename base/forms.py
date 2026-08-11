from django import forms
from django.contrib.auth import get_user_model

from base.models import (
    Trip,
    Day,
    Spot,
    TripExpense,
    DayExpense,
)


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

    hashtags = forms.CharField(
        required=False,
        label="ハッシュタグ",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "#一人旅 #海外旅行 #バックパッカー",
            }
        ),
        help_text="複数入力する場合はスペースで区切ってください。",
    )

    class Meta:

        model = Trip

        fields = (
            "category",
            "title",
            "start_date",
            "end_date",
            "memo",
        )

        labels = {
            "category": "カテゴリ",
            "title": "Tripタイトル",
            "start_date": "旅行開始日",
            "end_date": "旅行終了日",
            "memo": "メモ",
        }

        widgets = {

            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tripタイトルを入力してください",
                }
            ),

            "start_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "end_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),

            "memo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "旅行全体のメモを入力してください",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:

            hashtag_names = []

            for trip_hashtag in self.instance.trip_hashtags.select_related(
                "hashtag"
            ).all():

                hashtag_names.append(
                    f"#{trip_hashtag.hashtag.name}"
                )

            self.fields["hashtags"].initial = " ".join(
                hashtag_names
            )

    def clean_hashtags(self):

        hashtags = self.cleaned_data.get(
            "hashtags",
            ""
        )

        hashtags = hashtags.strip()

        if not hashtags:

            return ""

        hashtag_list = hashtags.split()

        cleaned_hashtags = []

        for hashtag in hashtag_list:

            hashtag = hashtag.lstrip("#")
            hashtag = hashtag.strip()

            if not hashtag:

                continue

            if len(hashtag) > 50:

                raise forms.ValidationError(
                    "ハッシュタグは1つ50文字以内で入力してください。"
                )

            if hashtag not in cleaned_hashtags:

                cleaned_hashtags.append(
                    hashtag
                )

        return cleaned_hashtags

    def clean(self):

        cleaned_data = super().clean()

        start_date = cleaned_data.get(
            "start_date"
        )

        end_date = cleaned_data.get(
            "end_date"
        )

        if not start_date or not end_date:

            return cleaned_data

        if end_date < start_date:

            self.add_error(
                "end_date",
                "旅行終了日は旅行開始日以降にしてください。"
            )

        return cleaned_data


# Day編集フォーム
# 旅行前の計画を編集するフォーム

class DayForm(forms.ModelForm):

    class Meta:

        model = Day

        fields = (
            "title",
            "budget",
            "memo",
        )

        labels = {
            "title": "Dayタイトル",
            "budget": "1日の予算",
            "memo": "メモ",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Dayタイトルを入力してください",
                }
            ),

            "budget": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：5000",
                }
            ),

            "memo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "この日の計画メモを入力してください",
                }
            ),
        }


# Day旅の記録フォーム
# 旅行中・旅行後の実績を記録するフォーム

class DayRecordForm(forms.ModelForm):

    class Meta:

        model = Day

        fields = (
            "media",
            "content",
            "actual_cost",
        )

        labels = {
            "media": "写真",
            "content": "感想",
            "actual_cost": "実際の合計費用",
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

            "actual_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：4800",
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


# Trip共通費用作成・編集フォーム

class TripExpenseForm(forms.ModelForm):

    class Meta:

        model = TripExpense

        fields = (
            "name",
            "planned_amount",
            "actual_amount",
            "memo",
        )

        labels = {
            "name": "費用名",
            "planned_amount": "予定金額",
            "actual_amount": "実際支払額",
            "memo": "メモ",
        }

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：航空券、ホテル、ツアー",
                }
            ),

            "planned_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：80000",
                }
            ),

            "actual_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：82000",
                }
            ),

            "memo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "例：予約内容や補足を入力してください",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        planned_amount = cleaned_data.get(
            "planned_amount"
        )

        actual_amount = cleaned_data.get(
            "actual_amount"
        )

        # -------------------------
        # 予定金額が未入力で、
        # 実際支払額だけ入力された場合
        #
        # 実際支払額を予定金額にも
        # 自動で設定する
        # -------------------------
        if (
            planned_amount is None
            and actual_amount is not None
        ):

            cleaned_data[
                "planned_amount"
            ] = actual_amount

        return cleaned_data


# Day費用作成・編集フォーム

class DayExpenseForm(forms.ModelForm):

    class Meta:

        model = DayExpense

        fields = (
            "name",
            "amount",
        )

        labels = {
            "name": "何に使ったか",
            "amount": "金額",
        }

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：昼食、電車、入場料",
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：1200",
                }
            ),
        }