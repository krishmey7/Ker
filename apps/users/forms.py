from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    """Inscription rapide mobile-first."""

    display_name = forms.CharField(max_length=80, required=False, label="Prénom ou pseudo")

    class Meta:
        model = User
        fields = ("username", "display_name", "password1", "password2")


class LoginForm(AuthenticationForm):
    """Connexion."""

    username = forms.CharField(label="Identifiant")
