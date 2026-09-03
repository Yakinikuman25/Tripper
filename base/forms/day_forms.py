from django import forms

from base.models import Day


# =========================================
# Day編集フォーム
#
# 旅行計画時に使用する
#
# ・Dayタイトル
# ・自由費予算
# ・Day予定金額
# ・Day実際支払額
# ・メモ
#
# を編集する
# =========================================

class DayForm(forms.ModelForm):

    class Meta:

        model = Day

        fields = (
            "title",
            "budget",
            "planned_amount",
            "actual_amount",
            "memo",
        )

        labels = {
            "title": "Dayタイトル",
            "budget": "自由費予算",
            "planned_amount": "Day予定金額",
            "actual_amount": "Day実際支払額",
            "memo": "メモ",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Dayタイトルを入力してください"
                    ),
                }
            ),

            # =====================================
            # 自由費予算
            #
            # 食事・コンビニ・
            # 細かな交通費など
            # =====================================

            "budget": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：5000",
                }
            ),

            # =====================================
            # Day予定金額
            #
            # 例：
            # ・1日ツアー
            # ・1日レンタカー
            # ・そのDay全体にかかる費用
            # =====================================

            "planned_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：35000",
                }
            ),

            # =====================================
            # Day実際支払額
            #
            # 予約・事前決済などで
            # すでに支払った場合に入力する
            # =====================================

            "actual_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：36000",
                }
            ),

            "memo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "この日の計画メモを入力してください"
                    ),
                }
            ),
        }

    # =====================================
    # 入力内容チェック
    #
    # 予定金額が未入力で
    # 実際支払額だけ入力された場合
    #
    # 実際支払額を
    # 予定金額にも設定する
    # =====================================

    def clean(self):

        cleaned_data = (
            super().clean()
        )

        planned_amount = (
            cleaned_data.get(
                "planned_amount"
            )
        )

        actual_amount = (
            cleaned_data.get(
                "actual_amount"
            )
        )

        if (
            planned_amount is None
            and actual_amount is not None
        ):

            cleaned_data[
                "planned_amount"
            ] = actual_amount

        return cleaned_data


# =========================================
# Day旅の記録フォーム
#
# 旅行中・旅行後の実績を記録する
#
# ・写真
# ・感想
# ・自由費実績
# ・Day実際支払額
#
# を記録する
# =========================================

class DayRecordForm(forms.ModelForm):

    class Meta:

        model = Day

        fields = (
            "media",
            "content",
            "actual_cost",
            "actual_amount",
        )

        labels = {
            "media": "写真",
            "content": "感想",
            "actual_cost": "自由費実績",
            "actual_amount": "Day実際支払額",
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
                    "placeholder": (
                        "この日の感想を入力してください"
                    ),
                }
            ),

            # =====================================
            # 自由費実績
            #
            # 食事・コンビニ・
            # 細かな交通費など
            #
            # DayExpenseの明細を基にした
            # 自由費の実績
            # =====================================

            "actual_cost": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：4800",
                }
            ),

            # =====================================
            # Day実際支払額
            #
            # 例：
            # ・1日ツアー
            # ・1日レンタカー
            # ・そのDay全体にかかった費用
            # =====================================

            "actual_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：36000",
                }
            ),
        }

    # =====================================
    # 保存
    #
    # 旅行中に初めて金額が決まり、
    #
    # planned_amount
    # → 未入力
    #
    # actual_amount
    # → 入力あり
    #
    # の場合は、
    # 実際支払額を予定金額にも設定する
    # =====================================

    def save(
        self,
        commit=True,
    ):

        day = (
            super().save(
                commit=False
            )
        )

        if (
            day.planned_amount is None
            and day.actual_amount is not None
        ):

            day.planned_amount = (
                day.actual_amount
            )

        if commit:

            day.save()

            self.save_m2m()

        return day