from datetime import datetime
from rest_framework import serializers
from Authentication.models import User
from Provider.models import Service, CoachProfile, Product
from .models import ServiceBooking, ProviderWallet, WalletTransaction


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

        booking = ServiceBooking.objects.create(
            user=user,
            coach=service.coach,
            service=service,
            booking_time=booking_time,
            amount=service.price,
            currency=service.currency,
            **validated_data
        )
        return booking


class ProductSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'Thumbnail']


class ServiceBookingDetailSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    coach = CoachBookingInfoSerializer(read_only=True)
    service = ServiceSimpleSerializer(read_only=True)
    product = ProductSimpleSerializer(read_only=True)
    order_type = serializers.SerializerMethodField()

    class Meta:
        model = ServiceBooking
        fields = [
            'id',
            'user',
            'coach',
            'service',
            'product',
            'order_type',
            'booking_date',
            'booking_time',
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

    def get_order_type(self, obj):
        if obj.product_id:
            return 'product'
        return 'service'


class ProductPurchaseCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ServiceBooking
        fields = ['product_id',]

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product with given ID does not exist.")
        if product.status != "published":
            raise serializers.ValidationError("This product is not available for purchase.")
        return value

    def create(self, validated_data):
        product_id = validated_data.pop('product_id')
        product = Product.objects.get(id=product_id)
        user = self.context['request'].user

        booking = ServiceBooking.objects.create(
            user=user,
            coach=product.coach,
            product=product,
            amount=product.price,
            currency='USD',
            payment_status='pending',
            status='pending',
            **validated_data
        )
        return booking


class ProviderWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderWallet
        fields = ['id', 'balance', 'created_at', 'updated_at']


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'transaction_type', 'amount', 'balance_after', 'description', 'booking', 'created_at']



