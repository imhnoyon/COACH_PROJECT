import json
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Conversation, Message, UserPresence

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer handling real-time chat for a specific conversation:
    - Real-time messages (text, booking references, etc.)
    - Automatic and manual read receipts (is_read updates with double checkmarks)
    - Typing indicators (starts typing / stops typing)
    - Participant online/offline presence tracking
    - Heartbeat ping/pong
    """

    async def connect(self):
        self.user = self.scope.get('user')

        # 1. Authentication check
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
        self.room_group_name = f'chat_{self.conversation_id}'

        # 2. Permission check: verify user belongs to this conversation
        is_participant = await self.check_participant(self.conversation_id, self.user)
        if not is_participant:
            await self.close(code=4003)
            return

        # 3. Join conversation room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # 4. Update presence to online
        await self.update_user_presence(self.user, is_online=True)

        # 5. Broadcast online status to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_event',
                'user_id': self.user.id,
                'is_online': True,
            }
        )

        # 6. Automatically mark incoming unread messages as read upon entering chat
        updated_count = await self.mark_messages_read(self.conversation_id, self.user)
        if updated_count > 0:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_read_event',
                    'conversation_id': int(self.conversation_id),
                    'reader_id': self.user.id,
                    'read_at': timezone.now().isoformat(),
                }
            )

    async def disconnect(self, close_code):
        if hasattr(self, 'user') and self.user.is_authenticated:
            # Update presence to offline
            await self.update_user_presence(self.user, is_online=False)

            # Broadcast offline status to room
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_status_event',
                        'user_id': self.user.id,
                        'is_online': False,
                        'last_seen': timezone.now().isoformat(),
                    }
                )
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
            return

        action = data.get('action') or data.get('type')

        # 1. SEND MESSAGE
        if action == 'send_message':
            content = data.get('content', '').strip()
            message_type = data.get('message_type', 'text')

            if not content and message_type == 'text':
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Message content cannot be empty.'
                }))
                return

            # Save message to database with full base URL for media
            base_url = self.get_base_url()
            message_dict, recipient_ids = await self.create_message_db(
                conversation_id=self.conversation_id,
                sender=self.user,
                content=content,
                message_type=message_type,
                base_url=base_url
            )

            # Broadcast message to conversation room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_event',
                    'message': message_dict,
                }
            )

            # Also send real-time notification to recipients' personal channels
            for recipient_id in recipient_ids:
                await self.channel_layer.group_send(
                    f'user_{recipient_id}',
                    {
                        'type': 'notification_message_event',
                        'conversation_id': int(self.conversation_id),
                        'message': message_dict,
                    }
                )

        # 2. MARK AS READ
        elif action == 'mark_as_read':
            updated_count = await self.mark_messages_read(self.conversation_id, self.user)
            if updated_count > 0:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_read_event',
                        'conversation_id': int(self.conversation_id),
                        'reader_id': self.user.id,
                        'read_at': timezone.now().isoformat(),
                    }
                )

        # 3. TYPING INDICATOR
        elif action == 'typing':
            is_typing = bool(data.get('is_typing', True))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_typing_event',
                    'sender_id': self.user.id,
                    'user_id': self.user.id,
                    'user_name': self.user.full_name or self.user.email,
                    'is_typing': is_typing,
                }
            )

        # 4. PING HEARTBEAT
        elif action == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': timezone.now().isoformat()
            }))

    # -------------------------------------------------------------
    # Channel Layer Event Handlers
    # -------------------------------------------------------------
    async def chat_message_event(self, event):
        """Dispatched when a new message is posted to this conversation."""
        message = event['message']
        # Add is_mine helper relative to this WebSocket client
        message_copy = dict(message)
        message_copy['is_mine'] = (message['sender']['id'] == self.user.id)

        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'data': message_copy,
        }))

    async def chat_read_event(self, event):
        """Dispatched when participant marks messages as read."""
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'conversation_id': event['conversation_id'],
            'reader_id': event['reader_id'],
            'read_at': event['read_at'],
        }))

    async def chat_typing_event(self, event):
        """Dispatched when someone is typing/stops typing (ignore if sent by self)."""
        if event.get('sender_id') == self.user.id:
            return

        await self.send(text_data=json.dumps({
            'type': 'typing_status',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing'],
        }))

    async def user_status_event(self, event):
        """Dispatched when a user connects/disconnects."""
        await self.send(text_data=json.dumps({
            'type': 'presence_status',
            'user_id': event['user_id'],
            'is_online': event['is_online'],
            'last_seen': event.get('last_seen'),
        }))

    async def notification_message_event(self, event):
        """Safe fallback if user group notification is received."""
        pass


    # -------------------------------------------------------------
    # Database Helper Methods (Async)
    # -------------------------------------------------------------
    @database_sync_to_async
    def check_participant(self, conversation_id, user):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            return conversation.participants.filter(id=user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def update_user_presence(self, user, is_online):
        presence, _ = UserPresence.objects.get_or_create(user=user)
        presence.is_online = is_online
        presence.save(update_fields=['is_online', 'last_seen'])

    @database_sync_to_async
    def mark_messages_read(self, conversation_id, reader_user):
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            unread_messages = conversation.messages.filter(is_read=False, is_deleted=False).exclude(sender=reader_user)
            count = unread_messages.count()
            if count > 0:
                unread_messages.update(is_read=True, read_at=timezone.now())
            return count
        except Conversation.DoesNotExist:
            return 0

    def get_base_url(self):
        headers = dict(self.scope.get('headers', []))
        host = headers.get(b'host', b'').decode('utf-8')
        scheme = 'https' if self.scope.get('scheme') == 'wss' else 'http'
        return f"{scheme}://{host}" if host else ""

    @database_sync_to_async
    def create_message_db(self, conversation_id, sender, content, message_type, base_url=""):
        conversation = Conversation.objects.get(id=conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            message_type=message_type
        )
        # Touch conversation updated_at
        conversation.save(update_fields=['updated_at'])

        # Find recipient IDs
        recipient_ids = list(conversation.participants.exclude(id=sender.id).values_list('id', flat=True))

        # Avatar helper
        avatar_url = None
        if sender.image:
            try:
                avatar_url = sender.image.url
            except Exception:
                avatar_url = None
        elif hasattr(sender, 'coach_profile') and sender.coach_profile.profile_photo:
            try:
                avatar_url = sender.coach_profile.profile_photo.url
            except Exception:
                avatar_url = None

        if avatar_url and not avatar_url.startswith('http') and base_url:
            avatar_url = f"{base_url}{avatar_url}"

        attachment_url = None
        if message.attachment:
            attachment_url = message.attachment.url
            if not attachment_url.startswith('http') and base_url:
                attachment_url = f"{base_url}{attachment_url}"

        formatted_time = message.created_at.strftime('%I:%M %p').lstrip('0')  # e.g. "2:55 PM"

        message_data = {
            'id': message.id,
            'conversation_id': conversation.id,
            'sender': {
                'id': sender.id,
                'email': sender.email,
                'full_name': sender.full_name,
                'role': sender.role,
                'avatar_url': avatar_url,
            },
            'message_type': message.message_type,
            'content': message.content,
            'attachment_url': attachment_url,
            'is_read': message.is_read,
            'read_at': message.read_at.isoformat() if message.read_at else None,
            'created_at': message.created_at.isoformat(),
            'formatted_time': formatted_time,
            'relative_time': 'Just now',
        }

        return message_data, recipient_ids


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Global user-level WebSocket consumer for instant alerts:
    - New message notifications across the entire app
    - Real-time unread messages badge counter updates
    """

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.user_group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

        # Send current total unread count upon connecting
        total_unread = await self.get_total_unread_count(self.user)
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'total_unread': total_unread,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
            action = data.get('action') or data.get('type')
            if action == 'get_unread_count':
                total_unread = await self.get_total_unread_count(self.user)
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'total_unread': total_unread,
                }))
            elif action == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
        except json.JSONDecodeError:
            pass

    async def notification_message_event(self, event):
        """Called when a new message is received by this user in any conversation."""
        total_unread = await self.get_total_unread_count(self.user)
        await self.send(text_data=json.dumps({
            'type': 'new_message_notification',
            'conversation_id': event.get('conversation_id'),
            'message': event.get('message'),
            'total_unread': total_unread,
        }))

    async def unread_count_update(self, event):
        """Called when total unread count changes."""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'total_unread': event.get('total_unread', 0),
        }))

    @database_sync_to_async
    def get_total_unread_count(self, user):
        return Message.objects.filter(
            conversation__participants=user,
            is_read=False,
            is_deleted=False
        ).exclude(sender=user).count()

