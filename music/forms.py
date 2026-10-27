from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm

class UserRegisterForm(forms.ModelForm):
    """
    Beginner-friendly registration form extending Django's User model.
    Includes username, email, password, and password confirmation.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'name@example.com',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a strong password (min 8 chars)',
            'autocomplete': 'new-password'
        })
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Repeat your password',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Choose a unique username',
                'autocomplete': 'username'
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match!")

        if password and len(password) < 6:
            self.add_error('password', "Password must be at least 6 characters long.")

        return cleaned_data


class UserLoginForm(AuthenticationForm):
    """
    Styled login form built on Django's standard AuthenticationForm.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your username',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your password',
            'autocomplete': 'current-password'
        })
    )
