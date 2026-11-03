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

    # Page 3: Support Ticket Center (SQL Database CRUD)
    path('support/', views.support_view, name='support'),
    path('support/ticket/<str:ticket_number>/update/', views.support_ticket_update, name='support_ticket_update'),
    path('support/ticket/<str:ticket_number>/delete/', views.support_ticket_delete, name='support_ticket_delete'),

    # REST APIs for FAQs & Error Codes (SQL Grounded)
    path('api/faqs/', views.api_faqs, name='api_faqs'),
    path('api/error-codes/', views.api_error_codes, name='api_error_codes'),

    # REST APIs for Support Tickets (Full CRUD: Create, Read, Update, Delete)
    path('api/tickets/', views.api_tickets_list, name='api_tickets_list'),
    path('api/ticket/create/', views.api_create_ticket, name='api_create_ticket'),
    path('api/ticket/<str:ticket_number>/', views.api_ticket_detail, name='api_ticket_detail'),
    path('api/ticket/<str:ticket_number>/update/', views.support_ticket_update, name='api_ticket_update'),
    path('api/ticket/<str:ticket_number>/delete/', views.support_ticket_delete, name='api_ticket_delete'),

    # System Health Check & Telemetry Dashboard
    path('health/', views.health_check_view, name='health_check'),

    # AI Assistant Endpoints (Grounded FAQ + MongoDB Logging)
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/chat/feedback/', views.api_chat_feedback, name='api_chat_feedback'),

    # Custom Error Preview / Direct Test Routes
    path('test-404/', views.test_404_view, name='test_404'),
    path('test-500/', views.test_500_view, name='test_500'),

    # Favorites (Interactive AJAX & Standard Fallback)
    path('song/<int:song_id>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_list, name='favorites_list'),

    # AI DJ & Track Generation
    path('ai/dj/', views.ai_mood_dj, name='ai_mood_dj'),
    path('ai/generate/', views.ai_generate_song, name='ai_generate_song'),

    # User Authentication (Stored in MongoDB 'users')
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
