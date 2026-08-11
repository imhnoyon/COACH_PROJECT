from django.db import models
from django.conf import settings
from django.utils import timezone


class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations"
    )
    booking = models.ForeignKey(
        'Payments.ServiceBooking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation #{self.id}"

    def get_other_participant(self, user):
        """Returns the other user in a 1-to-1 conversation."""
        return self.participants.exclude(id=user.id).first()

    def get_unread_count(self, user):
        """Returns count of unread messages for a specific participant."""
        return self.messages.filter(is_read=False, is_deleted=False).exclude(sender=user).count()

    def get_last_message(self):
        """Returns the most recent message in the conversation."""
        return self.messages.filter(is_deleted=False).order_by('-created_at').first()


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('booking', 'Booking Notice'),
        ('system', 'System'),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text'
    )
    content = models.TextField(blank=True, default='')
    attachment = models.FileField(upload_to='chat/attachments/',blank=True,null=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        sender_name = self.sender.full_name or self.sender.email
        return f"Msg #{self.id} from {sender_name}: {self.content[:30]}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class UserPresence(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presence")
    is_online = models.BooleanField(default=False, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Presence"
        verbose_name_plural = "User Presences"

    def __str__(self):
        status_text = "Online" if self.is_online else f"Offline (Last seen: {self.last_seen})"
        return f"{self.user.full_name or self.user.email} - {status_text}"

