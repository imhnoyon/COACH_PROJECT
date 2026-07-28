

from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView, Response

from Administration.models import Category
from .serializers import CategorySerializer
from utils.api_response import APIResponse
from rest_framework.permissions import IsAdminUser
# Create your views here.
class CategoryCreateView(APIView):
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CategorySerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return APIResponse.success(
                message="Category created successfully.",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        return APIResponse.error(
            message="Validation failed.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
        
        

    