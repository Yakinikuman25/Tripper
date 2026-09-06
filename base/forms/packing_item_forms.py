from django import forms

from ..models import PackingItem


class PackingItemForm(forms.ModelForm):

    class Meta:
        model = PackingItem

        fields = [
            "bag_type",
            "name",
            "quantity",
        ]

        labels = {
            "bag_type": "入れる場所",
            "name": "持ち物",
            "quantity": "個数",
        }

        widgets = {
            "bag_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "例：アウター、パスポート",
                }
            ),

            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "必要な場合のみ",
                }
            ),
        }


    def clean_name(self):

        name = self.cleaned_data.get("name", "").strip()

        if not name:
            raise forms.ValidationError(
                "持ち物名を入力してください。"
            )

        return name


    def clean_quantity(self):

        quantity = self.cleaned_data.get("quantity")

        if quantity is not None and quantity < 1:
            raise forms.ValidationError(
                "個数は1以上で入力してください。"
            )

        return quantity