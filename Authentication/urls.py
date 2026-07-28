
from django import views
from django.urls import include, path
from .views import *

urlpatterns = [
    path('register/', RegistrationAPIView.as_view(), name='register'),
    path('resend-verification-code/', ResendVerificationCodeView.as_view(), name='resend_verification_code'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('signin/', SignInView.as_view(), name='signin'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-reset-code/', VerifyResetCodeView.as_view(), name='verify_reset_code'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='refresh_token'),
    path('change-password/', ChangePasswordAPIView.as_view(), name='change_password'),
]