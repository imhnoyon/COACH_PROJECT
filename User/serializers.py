from datetime import datetime, date
from django.db.models.aggregates import Avg
from rest_framework import serializers
from Authentication.models import User
from Administration.models import Category
from Provider.models import CoachProfile, Product, Service, Blog
from Provider.serializers import CertificationSerializer, QualificationSerializer
from .models import *
from Payments.models import ServiceBooking

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


class CoachReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CoachRating
        fields = ["id", "user_name", "user_image", "rating", "review", "created_at"]

    def get_user_image(self, obj):
        if obj.user.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user.image.url)
            return obj.user.image.url
        return None


class CoachProfileDetailSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    categories = serializers.StringRelatedField(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    qualifications = QualificationSerializer(many=True, read_only=True)
    avg_rating = serializers.FloatField(read_only=True, default=0.0)
    services = serializers.SerializerMethodField(read_only=True)
    blogs = serializers.SerializerMethodField(read_only=True)
    reviews = serializers.SerializerMethodField(read_only=True)
    rating_breakdown = serializers.SerializerMethodField(read_only=True)

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
            "services",
            "blogs",
            "avg_rating",
            "reviews",
            "rating_breakdown",
            "created_at",
            "updated_at",
        ]

    def get_services(self, obj):
        services = Service.objects.filter(coach=obj.user, status="published")
        return UserServiceSerializer(services, many=True, context=self.context).data

    def get_blogs(self, obj):
        blogs = Blog.objects.filter(coach=obj.user, status="published")
        return UserBlogSerializer(blogs, many=True, context=self.context).data

    def get_reviews(self, obj):
        ratings = CoachRating.objects.filter(coach=obj).order_by("-created_at")
        return CoachReviewSerializer(ratings, many=True, context=self.context).data

    def get_rating_breakdown(self, obj):
        ratings = CoachRating.objects.filter(coach=obj)
        breakdown = {
            "5": ratings.filter(rating=5).count(),
            "4": ratings.filter(rating=4).count(),
            "3": ratings.filter(rating=3).count(),
            "2": ratings.filter(rating=2).count(),
            "1": ratings.filter(rating=1).count(),
        }
        return breakdown
    
    
    
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
        
        
class DigitalProductDetailsSerializer(serializers.ModelSerializer):
    category_details = serializers.SerializerMethodField(read_only=True)
    coach = BlogCoachSerializer(read_only=True)
    other_products = serializers.SerializerMethodField(read_only=True)

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
            'other_products',
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

    def get_other_products(self, obj):
        request = self.context.get('request')
        other_products = Product.objects.filter(coach=obj.coach, status="published").exclude(id=obj.id)
        return DigitalProductSerializer(other_products, many=True, context={'request': request}).data
        



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

class userServiceDetailsSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField(read_only=True)
    # coach = BlogCoachSerializer(read_only=True)
    provider_details = BlogCoachSerializer(source='coach', read_only=True)
    coach_id = serializers.IntegerField(source='coach.id', read_only=True)
    benefits = serializers.SerializerMethodField(read_only=True)
    other_sessions = serializers.SerializerMethodField(read_only=True)
   
    
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
            'benefits',
            'other_sessions',
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

    def get_benefits(self, obj):
        return [benefit.outcome for benefit in obj.benefits.all()]

    def get_other_sessions(self, obj):
        request = self.context.get('request')
        other_services = Service.objects.filter(coach=obj.coach, status="published").exclude(id=obj.id)
        return userServiceCreateSerializer(other_services, many=True, context={'request': request}).data
    
    
    
    
class BookingServicesSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source="service.title", read_only=True)
    service_category = serializers.CharField(source="service.category.name", read_only=True)
    service_type = serializers.CharField(source="service.service_type", read_only=True)
    session_format = serializers.CharField(source="service.session_format", read_only=True)
    session_duration = serializers.CharField(source="service.session_duration", read_only=True)
    session_link = serializers.CharField(source="service.session_url", read_only=True)
    coach_name = serializers.CharField(source="service.coach.full_name", read_only=True)
    # coach_profile_photo = serializers.SerializerMethodField(read_only=True)
    cancellation_policy= serializers.CharField(source="service.cancellation_policy", read_only=True)

    class Meta:
        model = ServiceBooking
        fields = ['id', 'coach_name', 'service_title', 'service_category', 'service_type', 'session_format', 'session_duration', 'session_link', 'booking_date', 'booking_time', 'amount','cancellation_policy', 'status', 'payment_status', 'payment_method', 'is_rescheduled']


class BookingRescheduleSerializer(serializers.Serializer):
    booking_date = serializers.DateField(required=True)
    booking_time = serializers.CharField(required=True)

    def validate_booking_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("Booking date cannot be in the past.")
        return value

    def validate_booking_time(self, value):
        time_formats = ['%I:%M %p', '%I:%M%p', '%H:%M:%S', '%H:%M']
        for fmt in time_formats:
            try:
                parsed_time = datetime.strptime(str(value).strip(), fmt).time()
                return parsed_time
            except ValueError:
                continue
        raise serializers.ValidationError("Invalid time format. Example formats: '11:00 AM' or '11:00:00'.")