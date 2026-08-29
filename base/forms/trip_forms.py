from django import forms

from base.models import Trip


# =========================================
# Trip作成・編集フォーム
# =========================================

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

    def __init__(
        self,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.fields[
            "start_date"
        ].input_formats = [
            "%Y-%m-%d",
        ]

        self.fields[
            "end_date"
        ].input_formats = [
            "%Y-%m-%d",
        ]

        # =====================================
        # 編集時
        #
        # 登録済みハッシュタグを
        # 4つの入力欄へ設定する
        # =====================================

        if (
            self.instance
            and self.instance.pk
        ):

            hashtag_names = []

            for trip_hashtag in (
                self.instance
                .trip_hashtags
                .select_related(
                    "hashtag"
                )
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

                if index < len(
                    hashtag_names
                ):

                    self.fields[
                        field_name
                    ].initial = (
                        hashtag_names[
                            index
                        ]
                    )

    def clean(self):

        cleaned_data = (
            super().clean()
        )

        # =====================================
        # ハッシュタグ
        # =====================================

        hashtag_field_names = (
            "hashtag_1",
            "hashtag_2",
            "hashtag_3",
            "hashtag_4",
        )

        cleaned_hashtags = []

        for field_name in (
            hashtag_field_names
        ):

            hashtag = (
                cleaned_data.get(
                    field_name,
                    ""
                )
                or ""
            ).strip()

            # -------------------------
            # 「#」を入力しても
            # DBには#を付けず保存する
            # -------------------------

            hashtag = (
                hashtag
                .lstrip("#")
                .strip()
            )

            if not hashtag:

                cleaned_data[
                    field_name
                ] = ""

                continue

            # -------------------------
            # 空白文字を禁止
            # -------------------------

            if any(
                character.isspace()
                for character
                in hashtag
            ):

                self.add_error(
                    field_name,
                    (
                        "1つの入力欄には"
                        "ハッシュタグを1つだけ"
                        "入力してください。"
                    ),
                )

                continue

            # -------------------------
            # 最大50文字
            # -------------------------

            if len(hashtag) > 50:

                self.add_error(
                    field_name,
                    (
                        "ハッシュタグは"
                        "1つ50文字以内で"
                        "入力してください。"
                    ),
                )

                continue

            # -------------------------
            # 同じハッシュタグの
            # 重複登録を防ぐ
            # -------------------------

            if (
                hashtag
                not in cleaned_hashtags
            ):

                cleaned_hashtags.append(
                    hashtag
                )

            cleaned_data[
                field_name
            ] = hashtag

        # -------------------------
        # Trip保存処理で使用
        # -------------------------

        cleaned_data[
            "hashtags"
        ] = cleaned_hashtags

        # =====================================
        # 旅行期間
        # =====================================

        start_date = (
            cleaned_data.get(
                "start_date"
            )
        )

        end_date = (
            cleaned_data.get(
                "end_date"
            )
        )

        if (
            start_date
            and end_date
            and end_date < start_date
        ):

            self.add_error(
                "end_date",
                (
                    "旅行終了日は"
                    "旅行開始日以降にしてください。"
                ),
            )

        return cleaned_data


# =========================================
# Trip完了フォーム
# =========================================

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

            "main_media": (
                forms.ClearableFileInput(
                    attrs={
                        "class": "form-control",
                    }
                )
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

        cleaned_data = (
            super().clean()
        )

        main_media = (
            cleaned_data.get(
                "main_media"
            )
        )

        overview = (
            cleaned_data.get(
                "overview"
            )
        )

        is_public = (
            cleaned_data.get(
                "is_public"
            )
        )

        # =====================================
        # 公開する場合
        #
        # ・代表写真
        # ・感想
        #
        # を必須にする
        # =====================================

        if is_public:

            if not main_media:

                self.add_error(
                    "main_media",
                    (
                        "公開する場合は"
                        "代表写真を登録してください。"
                    ),
                )

            if not overview:

                self.add_error(
                    "overview",
                    (
                        "公開する場合は"
                        "感想を入力してください。"
                    ),
                )

        return cleaned_data