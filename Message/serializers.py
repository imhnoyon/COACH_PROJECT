from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Conversation, Message, UserPresence
from Payments.models import ServiceBooking

User = get_user_model()


def get_user_avatar_url(user, request=None):
    """Helper to extract user avatar or coach profile photo URL."""
    url = None
    if user.image:
        try:
            url = user.image.url
        except Exception:
            url = None
    elif hasattr(user, 'coach_profile') and user.coach_profile.profile_photo:
        try:
            url = user.coach_profile.profile_photo.url
        except Exception:
            url = None

    if url and request and not url.startswith('http'):
        return request.build_absolute_uri(url)
    return url


def format_relative_time(dt):
    """Formats a datetime into relative human-readable format matching mobile UI."""
    if not dt:
        return ""
    now = timezone.now()
    diff = now - dt

    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() // 60)
        return f"{minutes}m ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() // 3600)
        return f"{hours}h ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days}d ago"
    else:
        return dt.strftime("%b %d")


class ParticipantSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'phone_number', 'avatar_url', 'is_online', 'last_seen']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        return get_user_avatar_url(obj, request)

    def get_is_online(self, obj):
        presence = getattr(obj, 'presence', None)
        return presence.is_online if presence else False

    def get_last_seen(self, obj):
        presence = getattr(obj, 'presence', None)
        return presence.last_seen if presence else None


class MessageSerializer(serializers.ModelSerializer):
    sender = ParticipantSerializer(read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    attachment_url = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    relative_time = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender',
            'sender_id',
            'message_type',
            'content',
            'attachment',
            'attachment_url',
            'is_read',
            'read_at',
            'created_at',
            'formatted_time',
            'relative_time',
            'is_mine',
        ]
        read_only_fields = ['id', 'conversation', 'sender', 'is_read', 'read_at', 'created_at']

    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None

    def get_formatted_time(self, obj):
        return obj.created_at.strftime('%I:%M %p').lstrip('0')  # e.g. "2:55 PM"

    def get_relative_time(self, obj):
        return format_relative_time(obj.created_at)

    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content', 'attachment', 'message_type']
        extra_kwargs = {
            'content': {'required': False, 'allow_blank': True},
            'attachment': {'required': False, 'allow_null': True},
            'message_type': {'required': False, 'default': 'text'},
        }

    def validate(self, data):
        content = data.get('content', '').strip()
        attachment = data.get('attachment')
        if not content and not attachment:
            raise serializers.ValidationError("Either 'content' or 'attachment' must be provided.")
        return data


class ConversationListSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'other_participant',
            'last_message',
            'unread_count',
            'booking',
            'created_at',
            'updated_at',
        ]

    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        other_user = obj.get_other_participant(request.user)
        if other_user:
            return ParticipantSerializer(other_user, context=self.context).data
        return None

    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content,
                'message_type': last_msg.message_type,
                'sender_id': last_msg.sender_id,
                'is_read': last_msg.is_read,
                'created_at': last_msg.created_at,
                'formatted_time': last_msg.created_at.strftime('%I:%M %p').lstrip('0'),
                'relative_time': format_relative_time(last_msg.created_at),
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.get_unread_count(request.user)


class ConversationDetailSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    other_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    booking_details = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'participants',
            'other_participant',
            'unread_count',
            'booking',
            'booking_details',
            'created_at',
            'updated_at',
        ]

    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        other_user = obj.get_other_participant(request.user)
        if other_user:
            return ParticipantSerializer(other_user, context=self.context).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.get_unread_count(request.user)

    def get_booking_details(self, obj):
        if obj.booking:
            booking = obj.booking
            service_title = booking.service.title if booking.service else (booking.product.title if booking.product else None)
            return {
                'id': booking.id,
                'title': service_title,
                'amount': str(booking.amount),
                'currency': booking.currency,
                'status': booking.status,
                'booking_date': str(booking.booking_date) if booking.booking_date else None,
                'booking_time': str(booking.booking_time) if booking.booking_time else None,
            }
        return None


class StartConversationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    recipient_id = serializers.IntegerField(required=False)
    booking_id = serializers.IntegerField(required=False, allow_null=True)
    initial_message = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        target_user_id = data.get('user_id') or data.get('recipient_id')
        if not target_user_id:
            raise serializers.ValidationError({"user_id": "Field 'user_id' is required."})

        if not User.objects.filter(id=target_user_id, is_active=True).exists():
            raise serializers.ValidationError({"user_id": "Target user does not exist or is inactive."})

        data['user_id'] = target_user_id
        return data

    def validate_booking_id(self, value):
        if value is not None and not ServiceBooking.objects.filter(id=value).exists():
            raise serializers.ValidationError("Booking does not exist.")
        return value

