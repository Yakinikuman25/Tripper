from django import forms

from base.models import Schedule


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
                    "placeholder": (
                        "例：ホテル出発、中央市場、空港へ移動"
                    ),
                }
            ),

            "memo": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "予定や補足を入力してください"
                    ),
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

        # =====================================
        # 終了時間のみ入力された場合
        # =====================================

        if (
            start_time is None
            and end_time is not None
        ):

            self.add_error(
                "start_time",
                (
                    "終了時間を入力する場合は"
                    "開始時間も入力してください。"
                ),
            )

        # =====================================
        # 終了時間が開始時間より前の場合
        # =====================================

        if (
            start_time is not None
            and end_time is not None
            and end_time < start_time
        ):

            self.add_error(
                "end_time",
                (
                    "終了時間は"
                    "開始時間以降にしてください。"
                ),
            )

        return cleaned_data