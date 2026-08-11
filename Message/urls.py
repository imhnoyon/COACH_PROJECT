from django.urls import path
from .views import (
    ConversationListView,
    StartConversationView,
    ConversationDetailView,
    MessageListView,
    SendMessageView,
    MarkMessagesAsReadView,
    TotalUnreadCountView,
    DeleteMessageView,
)

urlpatterns = [
    # Conversations
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/start/', StartConversationView.as_view(), name='conversation-start'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:pk>/messages/', MessageListView.as_view(), name='conversation-messages'),
    
    # Messages
    path('conversations/<int:pk>/send/', SendMessageView.as_view(), name='conversation-send-message'),
    path('conversations/<int:pk>/read/', MarkMessagesAsReadView.as_view(), name='conversation-mark-read'),
    
    # Global / Helper
    path('unread-count/', TotalUnreadCountView.as_view(), name='total-unread-count'),
    path('messages/<int:pk>/delete/', DeleteMessageView.as_view(), name='message-delete'),
]
