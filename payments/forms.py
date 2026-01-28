from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError

from .models import PayoutRequest


class PayoutRequestForm(forms.ModelForm):
    class Meta:
        model = PayoutRequest
        fields = ["amount"]

    def clean_amount(self):
        amt = self.cleaned_data.get("amount")
        if amt is None:
            raise ValidationError("Amount is required.")
        if amt <= Decimal("0.00"):
            raise ValidationError("Amount must be greater than zero.")
        return amt
