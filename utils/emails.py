from django.core.mail import EmailMessage
import random
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def generate_otp():
    return str(random.randint(100000, 999999))

def otp_expiry(minutes=10):
    return timezone.now() + timedelta(minutes=minutes)

def generate_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "access_token_valid_till": int(
            (timezone.now() + timedelta(minutes=30)).timestamp() * 1000
        ),
        "refresh_token": str(refresh),
    }
    
    
    

def send_verification_email(email, code,full_name):
    subject = "COACH | Verify Your Email"

    html_content = render_to_string(
        "emails/email_verification.html",
        {
            "otp_code": code,
            "expiry_minutes": 10,
            "user": {"email": email, "full_name": full_name}
        }
    )

    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.content_subtype = "html"
    email_message.send()



def send_reset_password_email(email, code, full_name):
    subject = "COACH | Password Reset"

    html_content = render_to_string(
        "emails/password_reset.html",
        {
            "otp_code": code,
            "expiry_minutes": 10,
            "user": {"email": email, "full_name": full_name},
        }
    )

    message = EmailMessage(
        subject,
        html_content,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )
    message.content_subtype = "html"
    message.send()


def send_ban_email(email, full_name, reason=None):
    subject = "COACH | Account Banned"

    html_content = render_to_string(
        "emails/banned_email.html",
        {
            "user_name": full_name,
            "user": {
                "email": email,
                "full_name": full_name,
            },
            "reason": reason or "Violation of our community guidelines",
            "support_email": "support@voicevibe.com"
        }
    )

    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.content_subtype = "html"
    email_message.send()
    
def send_active_email(email, full_name):
    subject = "COACH | Your Account is Active Again 🎉"

    html_content = render_to_string(
        "emails/active_email.html",
        {
            "user_name": full_name,
            "support_email": "support@voicevibe.com"
        }
    )

    email_message = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    email_message.content_subtype = "html"
    email_message.send()