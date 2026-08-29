from django import forms

from base.models import (
    Day,
    TripExpense,
    DayExpense,
)


# =========================================
# 全体費用作成・編集フォーム
# =========================================

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
                    "placeholder": (
                        "例：航空券、ホテル、ツアー"
                    ),
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
                    "placeholder": (
                        "例：予約内容や補足を入力してください"
                    ),
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

        # =====================================
        # 予定金額が未入力で、
        # 実際支払額だけ入力された場合
        #
        # 実際支払額を予定金額にも
        # 自動で設定する
        # =====================================

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
                    "placeholder": (
                        "例：昼食、電車、入場料"
                    ),
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

        cleaned_data[
            "name"
        ] = name

        # =====================================
        # 費用名だけ入力され、
        # 金額が空欄の場合は保存しない
        # =====================================

        if (
            name
            and amount is None
        ):

            self.add_error(
                "amount",
                (
                    "費用を登録する場合は"
                    "金額を入力してください。"
                ),
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