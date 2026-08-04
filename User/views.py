from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q
from django.db.models.functions import Coalesce
from Provider.serializers import *
from Provider.models import *
from User.models import CoachRating, AppRating
from .serializers import *
from utils.api_response import APIResponse

from Payments.models import ServiceBooking

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
        coach_profiles = CoachProfile.objects.filter(status="approved")\
            .annotate(avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0))\
            .order_by('-avg_rating')\
            .select_related('user')\
            .prefetch_related('categories')
        serializer = CoachProfileSerializer(coach_profiles, many=True, context={'request': request})
        return APIResponse.success(
            message="Coach profiles retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
class RecommendedCoachProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        coach_profiles = CoachProfile.objects.filter(status="approved")\
            .annotate(avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0))\
            .order_by('-avg_rating')\
            .select_related('user')\
            .prefetch_related('categories')
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
        
        
class CoachRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, coach_id):
        coach_profile = CoachProfile.objects.filter(id=coach_id).first()
        if not coach_profile:
            return APIResponse.error(
                message="Coach profile not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Enforce that the user has a completed booking with the coach
        has_completed_booking = ServiceBooking.objects.filter(
            user=request.user,
            coach=coach_profile.user,
            status="completed"
        ).exists()

        if not has_completed_booking:
            return APIResponse.error(
                message="You can only review this coach after completing a booking with them.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Enforce that the user can review only once per coach
        if CoachRating.objects.filter(coach_id=coach_id, user=request.user).exists():
            return APIResponse.error(
                message="You have already submitted a review for this coach.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()
        data['coach'] = coach_id

        serializer = CoachRatingSerializer(data=data)

        if serializer.is_valid():
            serializer.save(user=request.user)

            return APIResponse.success(
                message="Rating submitted successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            message="Invalid data.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AppRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if AppRating.objects.filter(user=request.user).exists():
            return APIResponse.error(
                message="You have already submitted a rating for this app.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = AppRatingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return APIResponse.success(
                message="App rating submitted successfully.",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        return APIResponse.error(
            message="Invalid data.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AppRatingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_ratings = AppRating.objects.all()
        serializer = AppRatinglistSerializer(app_ratings, many=True, context={'request': request})
        return APIResponse.success(
            message="App ratings retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

class CoachProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, coach_id):
        # We fetch the coach profile by coach_id (which is its pk) and annotate avg_rating
        coach_profile = CoachProfile.objects.filter(id=coach_id, status="approved")\
            .annotate(avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0))\
            .select_related('user')\
            .prefetch_related('categories', 'certifications', 'qualifications')\
            .first()

        if not coach_profile:
            return APIResponse.error(
                message="Coach profile not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = CoachProfileDetailSerializer(coach_profile, context={'request': request})
        return APIResponse.success(
            message="Coach profile details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class RecommendedCoachProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        coach_profiles = CoachProfile.objects.filter(status="approved")\
            .annotate(
                avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0),
                completed_sessions_count=Count('user__received_bookings', filter=Q(user__received_bookings__status='completed'))
            )\
            .order_by('-avg_rating', '-completed_sessions_count')\
            .select_related('user')\
            .prefetch_related('categories')

        serializer = CoachProfileSerializer(coach_profiles, many=True, context={'request': request})
        return APIResponse.success(
            message="Recommended coach profiles retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class BlogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category = request.query_params.get('category', None)
        if category:
            if category.isdigit():
                blogs = Blog.objects.filter(status="published", category__id=int(category))
            else:
                blogs = Blog.objects.filter(status="published", category__name__iexact=category)
        else:
            blogs = Blog.objects.filter(status="published")

        blogs = blogs.select_related('category', 'coach', 'coach__coach_profile')
        serializer = UserBlogSerializer(blogs, many=True, context={'request': request})
        return APIResponse.success(
            message="Blogs retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class BlogDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, blog_id):
        try:
            blog = Blog.objects.select_related('category', 'coach', 'coach__coach_profile').get(id=blog_id, status="published")
        except Blog.DoesNotExist:
            return APIResponse.error(
                message="Blog not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = UserBlogSerializer(blog, context={'request': request})
        return APIResponse.success(
            message="Blog details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        
class DigitalProductListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        digital_products = Product.objects.filter(status="published").select_related('category', 'coach', 'coach__coach_profile')
        serializer = DigitalProductSerializer(digital_products, many=True, context={'request': request})
        return APIResponse.success(
            message="Digital products retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
class UserServiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services = Service.objects.filter(status="published").select_related('coach', 'coach__coach_profile').prefetch_related('benefits')
        serializer = userServiceCreateSerializer(services, many=True, context={'request': request})
        return APIResponse.success(
            message="Services retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )