from django import forms


# =========================================
# Trip再利用
# =========================================

class TripReuseForm(
    forms.Form,
):

    start_date = forms.DateField(
        label="新しい旅行開始日",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )