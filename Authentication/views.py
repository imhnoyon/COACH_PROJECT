from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from  utils.api_response import APIResponse
from utils.emails import generate_otp, otp_expiry, send_verification_email
from .serializers import *
from .models import *


class RegistrationAPIView(APIView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()

            # Generate OTP
            code = generate_otp()
            OTP.objects.create(
                user=user,
                code=code,
                expires_at=otp_expiry(),
                purpose="verify"
            )

            # Send verification email
            if user.email:
                send_verification_email(user.email, code, full_name=user.full_name)

            return APIResponse.success(
            message="Registration completed successfully.OTP sent to your email for verification.",
            data={"user_id": str(user.id)},
            status_code=status.HTTP_201_CREATED
        )

        return APIResponse.error(
            message="Invalid data provided",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
           