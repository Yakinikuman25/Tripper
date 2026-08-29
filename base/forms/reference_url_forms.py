from django import forms

from base.models import (
    Trip,
    Day,
    Schedule,
    TripExpense,
    TripReferenceUrl,
    DayReferenceUrl,
    ScheduleReferenceUrl,
    TripExpenseReferenceUrl,
)


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

        cleaned_data[
            "title"
        ] = title

        cleaned_data[
            "url"
        ] = url

        # =====================================
        # URL名だけ入力して
        # URLが空欄の場合はエラー
        # =====================================

        if (
            title
            and not url
        ):

            self.add_error(
                "url",
                "参考URLを入力してください。",
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
                    "placeholder": (
                        "例：航空会社、旅行情報、公式サイト"
                    ),
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "https://example.com"
                    ),
                }
            ),
        }


TripReferenceUrlFormSet = (
    forms.inlineformset_factory(
        Trip,
        TripReferenceUrl,
        form=TripReferenceUrlForm,
        extra=1,
        can_delete=True,
    )
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
                    "placeholder": (
                        "例：モデルコース、観光情報、公式サイト"
                    ),
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "https://example.com"
                    ),
                }
            ),
        }


DayReferenceUrlFormSet = (
    forms.inlineformset_factory(
        Day,
        DayReferenceUrl,
        form=DayReferenceUrlForm,
        extra=1,
        can_delete=True,
    )
)


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
                    "placeholder": (
                        "例：Googleマップ、公式サイト、予約ページ"
                    ),
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "https://example.com"
                    ),
                }
            ),
        }


ScheduleReferenceUrlFormSet = (
    forms.inlineformset_factory(
        Schedule,
        ScheduleReferenceUrl,
        form=ScheduleReferenceUrlForm,
        extra=1,
        can_delete=True,
    )
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
                    "placeholder": (
                        "例：予約ページ、料金表、公式サイト"
                    ),
                }
            ),

            "url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "https://example.com"
                    ),
                }
            ),
        }


TripExpenseReferenceUrlFormSet = (
    forms.inlineformset_factory(
        TripExpense,
        TripExpenseReferenceUrl,
        form=TripExpenseReferenceUrlForm,
        extra=1,
        can_delete=True,
    )
)