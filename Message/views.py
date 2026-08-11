import logging
from django.db import transaction
from django.db.models import Q, Max
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Conversation, Message, UserPresence
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    StartConversationSerializer,
    format_relative_time,
    get_user_avatar_url,
)
from utils.api_response import APIResponse
from utils.paginations import CustomPagination
from Payments.models import ServiceBooking

logger = logging.getLogger(__name__)
User = get_user_model()


def broadcast_channel_message(group_name, payload):
    """Safely broadcasts a message via Django Channels layer."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(group_name, payload)
    except Exception as e:
        logger.warning(f"Failed to broadcast to channel layer group '{group_name}': {e}")


class ConversationListView(APIView):
    """
    List all conversations for the authenticated user.
    Supports search: ?search=<name_or_content>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        search_query = request.query_params.get('search', '').strip()

        conversations = Conversation.objects.filter(
            participants=user
        ).prefetch_related(
            'participants',
            'participants__presence',
            'messages',
            'booking'
        ).distinct()

        if search_query:
            conversations = conversations.filter(
                Q(participants__full_name__icontains=search_query) |
                Q(participants__email__icontains=search_query) |
                Q(messages__content__icontains=search_query)
            ).distinct()

        conversations = conversations.order_by('-updated_at')

        serializer = ConversationListSerializer(
            conversations,
            many=True,
            context={'request': request}
        )

        return APIResponse.success(
            message="Conversations retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

class StartConversationView(APIView):
    """
    Start or retrieve an existing conversation with a user/coach.
    Optionally links a booking and sends an initial message.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user_id = serializer.validated_data['user_id']
        booking_id = serializer.validated_data.get('booking_id')
        initial_message = serializer.validated_data.get('initial_message', '').strip()

        if target_user_id == request.user.id:
            return APIResponse.error(
                message="You cannot start a conversation with yourself.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        recipient = User.objects.get(id=target_user_id)
        booking = None
        if booking_id:
            booking = ServiceBooking.objects.filter(id=booking_id).first()

        with transaction.atomic():
            # Check if a 1-on-1 conversation already exists between these two users
            existing_conv = Conversation.objects.filter(
                participants=request.user
            ).filter(
                participants=recipient
            ).first()

            created = False
            if existing_conv:
                conversation = existing_conv
                if booking and not conversation.booking:
                    conversation.booking = booking
                    conversation.save(update_fields=['booking'])
            else:
                conversation = Conversation.objects.create(booking=booking)
                conversation.participants.add(request.user, recipient)
                created = True

            # If initial message provided, create and broadcast it
            if initial_message:
                new_msg = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=initial_message,
                    message_type='text'
                )
                conversation.save(update_fields=['updated_at'])

                # Prepare payload for broadcast
                msg_serializer = MessageSerializer(new_msg, context={'request': request})
                msg_data = msg_serializer.data

                # Broadcast to conversation room & recipient personal channel
                broadcast_channel_message(
                    f'chat_{conversation.id}',
                    {
                        'type': 'chat_message_event',
                        'message': msg_data,
                    }
                )
                broadcast_channel_message(
                    f'user_{recipient.id}',
                    {
                        'type': 'notification_message_event',
                        'conversation_id': conversation.id,
                        'message': msg_data,
                    }
                )

        detail_serializer = ConversationDetailSerializer(conversation, context={'request': request})
        res_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        res_msg = "Conversation created successfully." if created else "Conversation retrieved successfully."
        return APIResponse.success(
            message=res_msg,
            data=detail_serializer.data,
            status_code=res_status
        )


class ConversationDetailView(APIView):
    """
    Get detailed information about a specific conversation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            conversation = Conversation.objects.prefetch_related(
                'participants', 'participants__presence', 'booking'
            ).get(id=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return APIResponse.error(
                message="Conversation not found or access denied.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return APIResponse.success(
            message="Conversation details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class MessageListView(APIView):
    """
    Get paginated message history for a conversation.
    Optional query param: ?mark_as_read=true (default: true)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            conversation = Conversation.objects.get(id=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return APIResponse.error(
                message="Conversation not found or access denied.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        mark_as_read = request.query_params.get('mark_as_read', 'true').lower() in ('true', '1')

        if mark_as_read:
            unread_msgs = conversation.messages.filter(
                is_read=False,
                is_deleted=False
            ).exclude(sender=request.user)

            if unread_msgs.exists():
                unread_msgs.update(is_read=True, read_at=timezone.now())

                # Broadcast read event to room
                broadcast_channel_message(
                    f'chat_{conversation.id}',
                    {
                        'type': 'chat_read_event',
                        'conversation_id': conversation.id,
                        'reader_id': request.user.id,
                        'read_at': timezone.now().isoformat(),
                    }
                )

        messages = conversation.messages.filter(is_deleted=False).select_related('sender').order_by('created_at')
        paginator = CustomPagination()
        paginated_messages = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(paginated_messages, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data, message="Messages retrieved successfully.")


class SendMessageView(APIView):
    """
    Send a message in a conversation via REST API.
    Supports multipart/form-data for file/image uploads.
    Broadcasts message via WebSockets automatically!
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(id=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return APIResponse.error(
                message="Conversation not found or access denied.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        content = serializer.validated_data.get('content', '')
        attachment = serializer.validated_data.get('attachment', None)
        message_type = serializer.validated_data.get('message_type', 'text')

        # Auto-detect message type if attachment is present
        if attachment and message_type == 'text':
            if hasattr(attachment, 'content_type') and attachment.content_type.startswith('image/'):
                message_type = 'image'
            else:
                message_type = 'file'

        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=content,
                attachment=attachment,
                message_type=message_type
            )
            conversation.save(update_fields=['updated_at'])

        msg_serializer = MessageSerializer(message, context={'request': request})
        msg_data = msg_serializer.data

        # Broadcast real-time event to conversation room
        broadcast_channel_message(
            f'chat_{conversation.id}',
            {
                'type': 'chat_message_event',
                'message': msg_data,
            }
        )

        # Notify other participants via personal channels
        for recipient in conversation.participants.exclude(id=request.user.id):
            broadcast_channel_message(
                f'user_{recipient.id}',
                {
                    'type': 'notification_message_event',
                    'conversation_id': conversation.id,
                    'message': msg_data,
                }
            )

        return APIResponse.success(
            message="Message sent successfully.",
            data=msg_data,
            status_code=status.HTTP_201_CREATED
        )


class MarkMessagesAsReadView(APIView):
    """
    Mark all unread messages in a conversation as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conversation = Conversation.objects.get(id=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return APIResponse.error(
                message="Conversation not found or access denied.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        unread_messages = conversation.messages.filter(
            is_read=False,
            is_deleted=False
        ).exclude(sender=request.user)

        updated_count = unread_messages.update(
            is_read=True,
            read_at=timezone.now()
        )

        if updated_count > 0:
            # Broadcast read receipt to WebSocket room
            broadcast_channel_message(
                f'chat_{conversation.id}',
                {
                    'type': 'chat_read_event',
                    'conversation_id': conversation.id,
                    'reader_id': request.user.id,
                    'read_at': timezone.now().isoformat(),
                }
            )

        return APIResponse.success(
            message=f"{updated_count} messages marked as read.",
            data={'marked_count': updated_count},
            status_code=status.HTTP_200_OK
        )


class TotalUnreadCountView(APIView):
    """
    Get the total count of unread messages for the logged-in user across all conversations.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_unread = Message.objects.filter(
            conversation__participants=request.user,
            is_read=False,
            is_deleted=False
        ).exclude(sender=request.user).count()

        return APIResponse.success(
            message="Unread count retrieved successfully.",
            data={'total_unread': total_unread},
            status_code=status.HTTP_200_OK
        )


class DeleteMessageView(APIView):
    """
    Soft-delete a message (only allowed for the message sender).
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            message = Message.objects.get(id=pk, sender=request.user, is_deleted=False)
        except Message.DoesNotExist:
            return APIResponse.error(
                message="Message not found or access denied.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        message.is_deleted = True
        message.save(update_fields=['is_deleted'])

        return APIResponse.success(
            message="Message deleted successfully.",
            data={'message_id': pk},
            status_code=status.HTTP_200_OK
        )
