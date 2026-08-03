from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from Provider.serializers import CategorySerializer
from Provider.models import CoachProfile,Category
from .serializers import PostCreateSerializer, CoachProfileSerializer
from utils.api_response import APIResponse

class PostCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return APIResponse.success(
            message="Post created successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )
        
        
class CoachProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        coach_profiles = CoachProfile.objects.filter(status="approved").select_related('user').prefetch_related('categories')
        serializer = CoachProfileSerializer(coach_profiles, many=True, context={'request': request})
        return APIResponse.success(
            message="Coach profiles retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )



class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):


        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True, context={'request': request})
        return APIResponse.success(
            message="Categories retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )