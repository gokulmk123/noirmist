from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from allauth.account.utils import user_email
from django.contrib.auth import login


class NoUsernameAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return True

class NoUsernameSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email_address = user_email(sociallogin.user)
        if not email_address:
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(email=email_address)
            # Connect the social account to the existing user
            sociallogin.connect(request, user)
            # Explicitly log in the user to ensure session persistence
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        except User.DoesNotExist:
            # If no user exists, let allauth create a new one
            pass