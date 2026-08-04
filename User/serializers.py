from django.db.models.aggregates import Avg
from rest_framework import serializers
from Authentication.models import User
from Administration.models import Category
from Provider.models import CoachProfile, Product, Service, Blog
from Provider.serializers import CertificationSerializer, QualificationSerializer
from .models import *

class PostCreateSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "category",
            "category_id",
            "title",
            "description",
            "urgency_Level",
            "day_price",
            "hours_price",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        day_price = attrs.get("day_price")
        hours_price = attrs.get("hours_price")

        if day_price is None and hours_price is None:
            raise serializers.ValidationError(
                "Either day_price or hours_price is required."
            )

        if day_price is not None and day_price <= 0:
            raise serializers.ValidationError(
                {"day_price": "Day price must be greater than 0."}
            )

        if hours_price is not None and hours_price <= 0:
            raise serializers.ValidationError(
                {"hours_price": "Hour price must be greater than 0."}
            )

        return attrs


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "email", "phone_number"]


class CoachProfileSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    categories = serializers.StringRelatedField(many=True, read_only=True)
    avg_rating = serializers.FloatField(read_only=True, default=0.0)
    completed_sessions_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = CoachProfile
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
        
        




class CoachRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    coach_name = serializers.CharField(source="coach.full_name", read_only=True)

    class Meta:
        model = CoachRating
        fields = [ "id","coach","coach_name","user","user_name","rating","review","created_at","updated_at",]
        read_only_fields = ["id","user","created_at","updated_at",]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError(
                "Rating must be between 1 and 5."
            )
        return value


class AppRatingSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    class Meta:
        model = AppRating
        fields = ["id", "user", "user_name", "rating", "review", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value


class AppRatinglistSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    image=serializers.ImageField(source="user.image", read_only=True)
    class Meta:
        model = AppRating
        fields = ["id", "user", "user_name", "image", "rating", "review", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class UserServiceSerializer(serializers.ModelSerializer):
    benefits = serializers.SerializerMethodField(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "title",
            "description",
            "service_type",
            "session_format",
            "session_duration",
            "currency",
            "price",
            "booking_type",
            "who_is_this_service_for",
            "preparation_instructions",
            "cancellation_policy",
            "status",
            "benefits",
            "category_name",
            "created_at",
            "updated_at",
        ]

    def get_benefits(self, obj):
        return [benefit.outcome for benefit in obj.benefits.all()]


class CoachProfileDetailSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    categories = serializers.StringRelatedField(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    qualifications = QualificationSerializer(many=True, read_only=True)
    avg_rating = serializers.FloatField(read_only=True, default=0.0)
    services = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CoachProfile
        fields = [
            "id",
            "user",
            "profile_photo",
            "introduction_video",
            "about",
            "expertises",
            "is_completed",
            "status",
            "categories",
            "certifications",
            "qualifications",
            "avg_rating",
            "services",
            "created_at",
            "updated_at",
        ]

    def get_services(self, obj):
        # Retrieve all published services for the coach (matching user account)
        services = Service.objects.filter(coach=obj.user, status="published")
        return UserServiceSerializer(services, many=True).data
    
    
    
class BlogCoachSerializer(serializers.ModelSerializer):
    profile_photo = serializers.SerializerMethodField(read_only=True)
    about = serializers.SerializerMethodField(read_only=True)
    rating = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "phone_number",'rating', "profile_photo", "about"]

    def get_profile_photo(self, obj):
        if getattr(obj, 'image', None):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        profile = getattr(obj, 'coach_profile', None)
        if profile and profile.profile_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(profile.profile_photo.url)
            return profile.profile_photo.url
        return None

    def get_about(self, obj):
        profile = getattr(obj, 'coach_profile', None)
        return profile.about if profile else None
    
    def get_rating(self, obj):
        profile = getattr(obj, 'coach_profile', None)
        if profile:
            avg_rating = CoachRating.objects.filter(coach=profile).aggregate(avg=Avg('rating'))['avg']
            return avg_rating if avg_rating is not None else 0.0
        return 0.0


class UserBlogSerializer(serializers.ModelSerializer):
    category_details = serializers.SerializerMethodField(read_only=True)
    coach = BlogCoachSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = [
            'id',
            'coach',
            'category',
            'category_details',
            'title',
            'content',
            'image',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['coach', 'created_at', 'updated_at']

    def get_category_details(self, obj):
        if not obj.category:
            return None
        return {
            'id': obj.category.id,
            'name': obj.category.name,
            'description': obj.category.description,
        }
        

        
        
class DigitalProductSerializer(serializers.ModelSerializer):
    category_details = serializers.SerializerMethodField(read_only=True)
    coach = BlogCoachSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'coach',
            'category',
            'category_details',
            'title',
            'description',
            'Thumbnail',
            'book_file',
            'price',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['coach', 'created_at', 'updated_at']

    def get_category_details(self, obj):
        if not obj.category:
            return None
        return {
            'id': obj.category.id,
            'name': obj.category.name,
            'description': obj.category.description,
        }
        



class userServiceCreateSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField(read_only=True)
    # coach = BlogCoachSerializer(read_only=True)
    provider_details = BlogCoachSerializer(source='coach', read_only=True)
    coach_id = serializers.IntegerField(source='coach.id', read_only=True)
   
    
    class Meta:
        model = Service
        fields = [
            'id',
            'coach_id',
            # 'coach',
            'provider_details',
            'title',
            'description',
            'service_type',
            'session_format',
            'session_duration',
            'currency',
            'price',
            'booking_type',
            'who_is_this_service_for',
            'preparation_instructions',
            'cancellation_policy',
            'session_url',
            'status',
            'category',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['coach', 'created_at', 'updated_at']
        
    def get_category(self, obj):
        if not obj.category:
            return None
        return {
            'id': obj.category.id,
            'name': obj.category.name,
            'description': obj.category.description,
        }

