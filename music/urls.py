from django.urls import path
from . import views

urlpatterns = [
    # Core Assessment Pages (>= 3 Pages)
    # Page 1: Home / Discovery / In-Browser Player
    path('', views.home, name='home'),
    path('mood/<slug:slug>/', views.mood_detail, name='mood_detail'),
    path('song/<int:song_id>/', views.song_detail, name='song_detail'),

    # Page 2: FAQ & 8 Error Codes Knowledge Base
    path('faq/', views.faq_view, name='faq'),

    # Page 3: Support Ticket Center (SQL Database)
    path('support/', views.support_view, name='support'),

    # System Health Check & Telemetry Dashboard
    path('health/', views.health_check_view, name='health_check'),

    # AI Assistant Endpoints (Grounded FAQ + MongoDB Logging)
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/chat/feedback/', views.api_chat_feedback, name='api_chat_feedback'),
    path('api/ticket/create/', views.api_create_ticket, name='api_create_ticket'),

    # Custom Error Preview / Direct Test Routes
    path('test-404/', views.test_404_view, name='test_404'),
    path('test-500/', views.test_500_view, name='test_500'),

    # Favorites (Interactive AJAX & Standard Fallback)
    path('song/<int:song_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_list, name='favorites_list'),

    # AI DJ & Track Generation
    path('ai/dj/', views.ai_mood_dj, name='ai_mood_dj'),
    path('ai/generate/', views.ai_generate_song, name='ai_generate_song'),
]

