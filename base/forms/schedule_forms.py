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
            "planned_amount",
            "actual_amount",
            "memo",
        )

        labels = {
            "start_time": "開始時間",
            "end_time": "終了時間",
            "name": "スケジュール名",
            "planned_amount": "予定金額",
            "actual_amount": "実際支払額",
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

            "planned_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：5000",
                }
            ),

            "actual_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：5500",
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

        planned_amount = cleaned_data.get(
            "planned_amount"
        )

        actual_amount = cleaned_data.get(
            "actual_amount"
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

        # =====================================
        # 実際支払額だけ入力された場合
        #
        # 予約・事前決済などですでに
        # 金額が確定しているケース
        #
        # 実際支払額を予定金額にも設定する
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
# Schedule旅の記録フォーム
#
# 旅行中・旅行完了後に
# 実際支払額を記録する
# =========================================

class ScheduleRecordForm(forms.ModelForm):

    class Meta:

        model = Schedule

        fields = (
            "actual_amount",
        )

        labels = {
            "actual_amount": "実際支払額",
        }

        widgets = {

            "actual_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "例：5500",
                }
            ),
        }