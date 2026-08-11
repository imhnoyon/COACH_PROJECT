from django.contrib import admin
from .models import Conversation, Message, UserPresence


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'message_type', 'content', 'attachment', 'is_read', 'read_at', 'created_at')
    can_delete = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_participants', 'booking', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participants__email', 'participants__full_name')
    inlines = [MessageInline]

    def get_participants(self, obj):
        return ", ".join([u.full_name or u.email for u in obj.participants.all()])
    get_participants.short_description = "Participants"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'message_type', 'short_content', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'is_deleted', 'created_at')
    search_fields = ('content', 'sender__email', 'sender__full_name')
    readonly_fields = ('created_at', 'updated_at', 'read_at')

    def short_content(self, obj):
        return obj.content[:40] if obj.content else f"[{obj.message_type}]"
    short_content.short_description = "Content"


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_online', 'last_seen')
    list_filter = ('is_online', 'last_seen')
    search_fields = ('user__email', 'user__full_name')

