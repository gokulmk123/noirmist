# forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re

User = get_user_model()

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$'
NAME_REGEX = r"^[A-Za-z\s]{3,50}$"
MOBILE_REGEX = r'^[6-9]\d{9}$'

class AdminLoginForm(forms.Form):
    username = forms.CharField(
        required=True,
        min_length=3,
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Enter your name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'})
    )
    password = forms.CharField(
        required=True,
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(NAME_REGEX, username):
            raise ValidationError("Name must contain only letters and spaces (3–50 characters).")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if not re.match(EMAIL_REGEX, email):
            raise ValidationError("Enter a valid email address (e.g., yourname@gmail.com).")
        return email

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if not username or not email or not password:
            raise ValidationError("All fields are required.")

        try:
            user = User.objects.get(username=username, email=email)
        except User.DoesNotExist:
            raise ValidationError("No admin account found with this username and email.")

        if not user.check_password(password):
            raise ValidationError("Incorrect password.")

        if not user.is_superuser:
            raise ValidationError("You are not authorized as an admin.")

        self.user = user
        return cleaned_data
    
    # ////////////////////////////////////////////////////////////////////////////////////////////////\

    # user sign up

class UserSignupForm(forms.ModelForm):
    password = forms.CharField(
        required=True,
        min_length=8,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'})
)

    class Meta:
        model = User
        fields = ['username', 'email', 'mobile', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Enter your name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter your email'}),
            'mobile': forms.TextInput(attrs={'placeholder': 'Enter your mobile'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not re.match(NAME_REGEX, username):
            raise ValidationError("Name must contain only letters and spaces (3–50 characters).")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not re.match(EMAIL_REGEX, email):
            raise ValidationError("Enter a valid email address.")
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email already exists.")
        return email

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '').strip()
        if not re.match(MOBILE_REGEX, mobile):
            raise ValidationError("Enter a valid 10-digit Indian mobile number.")
        return mobile

# ////////////////////////////////////////////////////////////////////////////



class UserLoginForm(forms.Form):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email',
            'class': 'w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email', '').lower()
        password = cleaned_data.get('password')

        if not email or not password:
            raise ValidationError("Both fields are required.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("No user found with this email.")

        if not user.check_password(password):
            raise ValidationError("Incorrect password.")

        if not user.is_active:
            raise ValidationError("Your account is not active. Please verify your email or contact support.")

        self.user = user
        return cleaned_data
    
class ShippingAddressForm(forms.Form):
    full_name = forms.CharField(max_length=100, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=True)
    city = forms.CharField(max_length=100, required=True)
    phone = forms.CharField(max_length=15, required=True)

