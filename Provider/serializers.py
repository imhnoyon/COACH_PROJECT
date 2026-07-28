import json
from rest_framework import serializers
from Administration.models import Category
from Administration.serializers import CategorySerializer
from Authentication.models import User
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
    category=serializers.SerializerMethodField(read_only=True)

    

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