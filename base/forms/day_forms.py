from django import forms

from base.models import Day


# =========================================
# Day編集フォーム
# 旅行前の計画を編集するフォーム
# =========================================

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
                    "placeholder": (
                        "Dayタイトルを入力してください"
                    ),
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
                    "placeholder": (
                        "この日の計画メモを入力してください"
                    ),
                }
            ),
        }


# =========================================
# Day旅の記録フォーム
# 旅行中・旅行後の実績を記録するフォーム
# =========================================

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
                    "placeholder": (
                        "この日の感想を入力してください"
                    ),
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