import json
from rest_framework import serializers
from Administration.models import Category
from Administration.serializers import CategorySerializer
from Authentication.models import User
from Payments.models import ServiceBooking
from .models import *


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = ['id', 'name', 'document', 'created_at']


class QualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Qualification
        fields = ['id', 'name', 'document', 'created_at']


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'phone_number','latitude', 'longitude',]


class CoachProfileDetailSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    qualifications = QualificationSerializer(many=True, read_only=True)

    class Meta:
        model = CoachProfile
        fields = [
            'id',
            'user',
            'profile_photo',
            'about',
            'categories',
            'certifications',
            'qualifications',
            'introduction_video',
            'expertises',
            'is_completed',
            'status',
            'created_at',
            'updated_at',
        ]


class CreateCoachProfileSerializer(serializers.ModelSerializer):
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    profile_photo = serializers.ImageField(required=False)
    about = serializers.CharField(required=False)

    class Meta:
        model = CoachProfile
        fields = [
            'profile_photo',
            'about',
            'category_ids',
            'introduction_video',
            'expertises',
        ]

    def validate_expertises(self, value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = [x.strip() for x in value.split(',') if x.strip()]
        if not isinstance(value, list):
            raise serializers.ValidationError("Expertises must be a list of strings.")
        return value


# Service creation serializer
class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientBenefit
        fields = ['id', 'outcome']


class ServiceCreateSerializer(serializers.ModelSerializer):
    benefits = BenefitSerializer(many=True, read_only=True)
    category = serializers.SerializerMethodField(read_only=True)
    category_write = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    
    class Meta:
        model = Service
        fields = [
            'id',
            'coach',
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
            'benefits',
            'category',
            'category_write',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['coach', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        # Support category as ID under 'category' or 'category_id'
        if 'category' in data and not isinstance(data['category'], dict):
            data = data.copy()
            data['category_write'] = data.pop('category')
        elif 'category_id' in data:
            data = data.copy()
            data['category_write'] = data.pop('category_id')
        return super().to_internal_value(data)
        
        
        
    def get_category(self, obj):
        if not obj.category:
            return None
        return {
            'id': obj.category.id,
            'name': obj.category.name,
            'description': obj.category.description,
        }
        
        

class BlogSerializer(serializers.ModelSerializer):
    category_details = serializers.SerializerMethodField(read_only=True)

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
        
        
        
class ProductSerializer(serializers.ModelSerializer):
    category_details = serializers.SerializerMethodField(read_only=True)

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
        
        
        
        
class ServiceBookingPendingSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    service = serializers.SerializerMethodField()
    booking_type = serializers.CharField(source='service.booking_type', read_only=True)
    session_url = serializers.URLField(source='service.session_url', read_only=True)
    session_duration = serializers.CharField(source='service.session_duration', read_only=True)
    service_id = serializers.IntegerField(source='service.id', read_only=True)
    coach_id = serializers.IntegerField(source='coach.coach_profile.id', read_only=True)

    class Meta:
        model = ServiceBooking
        fields = [
            'id',
            'coach_id',
            'service_id',
            'user',
            'service',
            'booking_date',
            'booking_time',
            'amount',
            'booking_type',
            'session_url',
            'session_duration',
            'currency',
            'status',
            'payment_status',
            'notes',
            'created_at',
        ]

    def get_service(self, obj):
        if not obj.service:
            return None
        return {
            'id': obj.service.id,
            'title': obj.service.title,
            'session_duration': obj.service.session_duration,
            'price': obj.service.price,
            'currency': obj.service.currency,
        }
        
        
        
