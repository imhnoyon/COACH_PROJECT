from datetime import datetime
from rest_framework import serializers
from Authentication.models import User
from Provider.models import Service, CoachProfile
from .models import ServiceBooking


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'phone_number']


class CoachBookingInfoSerializer(serializers.ModelSerializer):
    profile_photo = serializers.SerializerMethodField()
    about = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'phone_number', 'profile_photo', 'about']

    def get_profile_photo(self, obj):
        request = self.context.get('request')
        if hasattr(obj, 'coach_profile') and obj.coach_profile.profile_photo:
            if request:
                return request.build_absolute_uri(obj.coach_profile.profile_photo.url)
            return obj.coach_profile.profile_photo.url
        return None

    def get_about(self, obj):
        if hasattr(obj, 'coach_profile'):
            return obj.coach_profile.about
        return None


class ServiceSimpleSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id',
            'title',
            'description',
            'service_type',
            'session_format',
            'session_duration',
            'price',
            'currency',
            'booking_type',
            'category',
        ]

    def get_category(self, obj):
        if not obj.category:
            return None
        return {
            'id': obj.category.id,
            'name': obj.category.name,
            'description': obj.category.description,
        }


class ServiceBookingCreateSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    booking_date = serializers.DateField()
    booking_time = serializers.CharField()
    # session_type = serializers.CharField(required=False, allow_blank=True)
    # session_format = serializers.CharField(required=False, allow_blank=True)
    # notes = serializers.CharField(required=False, allow_blank=True)

    def validate_service_id(self, value):
        try:
            service = Service.objects.get(id=value)
        except Service.DoesNotExist:
            raise serializers.ValidationError("Service with given ID does not exist.")
        if service.status != "published":
            raise serializers.ValidationError("This service is not available for booking.")
        return value

    def validate_booking_time(self, value):
        # Support formats like '11:00 AM', '11:00PM', '11:00:00', '11:00'
        time_formats = ['%I:%M %p', '%I:%M%p', '%H:%M:%S', '%H:%M']
        for fmt in time_formats:
            try:
                parsed_time = datetime.strptime(value.strip(), fmt).time()
                return parsed_time
            except ValueError:
                continue
        raise serializers.ValidationError("Invalid time format. Example formats: '11:00 AM' or '11:00:00'.")

    def create(self, validated_data):
        service_id = validated_data.pop('service_id')
        service = Service.objects.get(id=service_id)
        user = self.context['request'].user

        booking_time = validated_data.pop('booking_time')
        # session_type = validated_data.get('session_type') or service.service_type
        # session_format = validated_data.get('session_format') or service.session_format

        booking = ServiceBooking.objects.create(
            user=user,
            coach=service.coach,
            service=service,
            booking_time=booking_time,
            # session_type=session_type,
            # session_format=session_format,
            amount=service.price,
            currency=service.currency,
            **validated_data
        )
        return booking


class ServiceBookingDetailSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    coach = CoachBookingInfoSerializer(read_only=True)
    service = ServiceSimpleSerializer(read_only=True)

    class Meta:
        model = ServiceBooking
        fields = [
            'id',
            'user',
            'coach',
            'service',
            'booking_date',
            'booking_time',
            'session_type',
            'session_format',
            'amount',
            'currency',
            'status',
            'payment_status',
            'payment_method',
            'transaction_id',
            'notes',
            'created_at',
            'updated_at',
        ]
