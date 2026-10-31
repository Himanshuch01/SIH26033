from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "role", "phone", "village", "district", "org_name")
        labels = {"first_name": "Your name"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["role"].widget = forms.RadioSelect(choices=User.Role.choices)
        self.fields["role"].initial = User.Role.BUYER
        self.fields["org_name"].help_text = "FPO name for farmers, shop / mess name for buyers. Optional."
