from django import forms
from django.contrib.auth import get_user_model

from base.models import (
    Trip,
    Day,
    Schedule,
    TripExpense,
    DayExpense,
    TripReferenceUrl,
    DayReferenceUrl,
    ScheduleReferenceUrl,
    TripExpenseReferenceUrl,
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

    # =========================================
    # ハッシュタグ
    #
    # 4つの入力欄を最初から表示する
    # すべて任意入力
    # 「#」はテンプレート側で表示する
    # =========================================

    hashtag_1 = forms.CharField(
        required=False,
        label="ハッシュタグ1",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例：一人旅",
            }
        ),
    )

    hashtag_2 = forms.CharField(
        required=False,
        label="ハッシュタグ2",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例：海外旅行",
            }
        ),
    )

    hashtag_3 = forms.CharField(
        required=False,
        label="ハッシュタグ3",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例：バックパッカー",
            }
        ),
    )

    hashtag_4 = forms.CharField(
        required=False,
        label="ハッシュタグ4",
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例：自然",
            }
        ),
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
                    "onkeydown": "return false;",
                    "onpaste": "return false;",
                    "ondrop": "return false;",
                },
                format="%Y-%m-%d",
            ),

            "end_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                    "onkeydown": "return false;",
                    "onpaste": "return false;",
                    "ondrop": "return false;",
                },
                format="%Y-%m-%d",
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

        self.fields["start_date"].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields["end_date"].input_formats = [
            "%Y-%m-%d",
        ]

        if self.instance and self.instance.pk:

            hashtag_names = []

            for trip_hashtag in (
                self.instance
                .trip_hashtags
                .select_related("hashtag")
                .all()
            ):

                hashtag_names.append(
                    trip_hashtag.hashtag.name
                )

            hashtag_field_names = (
                "hashtag_1",
                "hashtag_2",
                "hashtag_3",
                "hashtag_4",
            )

            for index, field_name in enumerate(
                hashtag_field_names
            ):

                if index < len(hashtag_names):

                    self.fields[
                        field_name
                    ].initial = hashtag_names[index]

    def clean(self):

        cleaned_data = super().clean()

        # =================================
        # ハッシュタグ
        # =================================

        hashtag_field_names = (
            "hashtag_1",
            "hashtag_2",
            "hashtag_3",
            "hashtag_4",
        )

        cleaned_hashtags = []

        for field_name in hashtag_field_names:

            hashtag = (
                cleaned_data.get(
                    field_name,
                    ""
                )
                or ""
            ).strip()

            # 「#」を入力してしまっても
            # DBには#を付けずに保存する
            hashtag = hashtag.lstrip("#").strip()

            if not hashtag:

                cleaned_data[field_name] = ""
                continue

            if any(
                character.isspace()
                for character in hashtag
            ):

                self.add_error(
                    field_name,
                    "1つの入力欄にはハッシュタグを1つだけ入力してください。"
                )

                continue

            if len(hashtag) > 50:

                self.add_error(
                    field_name,
                    "ハッシュタグは1つ50文字以内で入力してください。"
                )

                continue

            if hashtag not in cleaned_hashtags:

                cleaned_hashtags.append(
                    hashtag
                )

            cleaned_data[field_name] = hashtag

        # 既存のTrip保存処理との互換性を保つ
        cleaned_data[
            "hashtags"
        ] = cleaned_hashtags

        # =================================
        # 旅行期間
        # =================================

        start_date = cleaned_data.get(
            "start_date"
        )

        end_date = cleaned_data.get(
            "end_date"
        )

        if (
            start_date
            and end_date
            and end_date < start_date
        ):

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


# =========================================
# 参考URL共通フォームMixin
# =========================================

class ReferenceUrlFormMixin:

    def clean(self):

        cleaned_data = super().clean()

        title = (
            cleaned_data.get(
                "title",
                ""
            )
            or ""
        ).strip()

        url = (
            cleaned_data.get(
                "url",
                ""
            )
            or ""
        ).strip()

        cleaned_data["title"] = title
        cleaned_data["url"] = url

        # URL名だけ入力してURLが空欄の場合はエラー
        if title and not url:

            self.add_error(
                "url",
                "参考URLを入力してください。"
            )

        return cleaned_data


# =========================================
# Trip参考URLフォーム
# =========================================

class TripReferenceUrlForm(
    ReferenceUrlFormMixin,
    forms.ModelForm,
):

    class Meta:

        model = TripReferenceUrl

        fields = (
            "title",
            "url",
        )

        labels = {
            "title": "参考URL名",
            "url": "URL",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：航空会社、旅行情報、公式サイト",
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),
        }


TripReferenceUrlFormSet = forms.inlineformset_factory(
    Trip,
    TripReferenceUrl,
    form=TripReferenceUrlForm,
    extra=1,
    can_delete=True,
)


# =========================================
# Day参考URLフォーム
# =========================================

class DayReferenceUrlForm(
    ReferenceUrlFormMixin,
    forms.ModelForm,
):

    class Meta:

        model = DayReferenceUrl

        fields = (
            "title",
            "url",
        )

        labels = {
            "title": "参考URL名",
            "url": "URL",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：モデルコース、観光情報、公式サイト",
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),
        }


DayReferenceUrlFormSet = forms.inlineformset_factory(
    Day,
    DayReferenceUrl,
    form=DayReferenceUrlForm,
    extra=1,
    can_delete=True,
)


# =========================================
# スケジュール作成・編集フォーム
# =========================================

class ScheduleForm(forms.ModelForm):

    class Meta:

        model = Schedule

        fields = (
            "start_time",
            "end_time",
            "name",
            "memo",
        )

        labels = {
            "start_time": "開始時間",
            "end_time": "終了時間",
            "name": "スケジュール名",
            "memo": "メモ",
        }

        widgets = {

            "start_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                },
                format="%H:%M",
            ),

            "end_time": forms.TimeInput(
                attrs={
                    "type": "time",
                    "class": "form-control",
                },
                format="%H:%M",
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：ホテル出発、中央市場、空港へ移動",
                }
            ),

            "memo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "予定や補足を入力してください",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        start_time = cleaned_data.get(
            "start_time"
        )

        end_time = cleaned_data.get(
            "end_time"
        )

        if (
            start_time is None
            and end_time is not None
        ):

            self.add_error(
                "start_time",
                "終了時間を入力する場合は開始時間も入力してください。"
            )

        if (
            start_time is not None
            and end_time is not None
            and end_time < start_time
        ):

            self.add_error(
                "end_time",
                "終了時間は開始時間以降にしてください。"
            )

        return cleaned_data


# =========================================
# スケジュール参考URLフォーム
# =========================================

class ScheduleReferenceUrlForm(
    ReferenceUrlFormMixin,
    forms.ModelForm,
):

    class Meta:

        model = ScheduleReferenceUrl

        fields = (
            "title",
            "url",
        )

        labels = {
            "title": "参考URL名",
            "url": "URL",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：Googleマップ、公式サイト、予約ページ",
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),
        }


ScheduleReferenceUrlFormSet = forms.inlineformset_factory(
    Schedule,
    ScheduleReferenceUrl,
    form=ScheduleReferenceUrlForm,
    extra=1,
    can_delete=True,
)


# =========================================
# 全体費用参考URLフォーム
# =========================================

class TripExpenseReferenceUrlForm(
    ReferenceUrlFormMixin,
    forms.ModelForm,
):

    class Meta:

        model = TripExpenseReferenceUrl

        fields = (
            "title",
            "url",
        )

        labels = {
            "title": "参考URL名",
            "url": "URL",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：予約ページ、料金表、公式サイト",
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com",
                }
            ),
        }


TripExpenseReferenceUrlFormSet = forms.inlineformset_factory(
    TripExpense,
    TripExpenseReferenceUrl,
    form=TripExpenseReferenceUrlForm,
    extra=1,
    can_delete=True,
)


# 全体費用作成・編集フォーム

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


# =========================================
# Day費用作成・編集フォーム
# =========================================

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

    def clean(self):

        cleaned_data = super().clean()

        name = (
            cleaned_data.get(
                "name",
                ""
            )
            or ""
        ).strip()

        amount = cleaned_data.get(
            "amount"
        )

        cleaned_data["name"] = name

        # 費用名だけ入力され、
        # 金額が空欄の場合は保存しない
        if (
            name
            and amount is None
        ):

            self.add_error(
                "amount",
                "費用を登録する場合は金額を入力してください。"
            )

        return cleaned_data


# =========================================
# Day費用 FormSet
#
# 旅の記録フォームの中で
# 複数の費用明細をまとめて編集する
#
# 「＋ 費用を追加」ではDB保存せず、
# 最後の「保存」で旅の記録と一括保存する
# =========================================

DayExpenseFormSet = forms.inlineformset_factory(
    Day,
    DayExpense,
    form=DayExpenseForm,
    extra=1,
    can_delete=True,
)