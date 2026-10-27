from django.contrib import admin
from .models import Mood, Song, Favorite, FAQ, ErrorCode, SupportTicket

@admin.register(Mood)
class MoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'song_count')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'mood', 'genre', 'duration', 'is_featured', 'favorite_count', 'created_at')
    list_filter = ('mood', 'is_featured', 'genre')
    search_fields = ('title', 'artist', 'album', 'description')
    ordering = ('-is_featured', '-created_at')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'song', 'created_at')
    list_filter = ('song__mood', 'created_at')
    search_fields = ('user__username', 'song__title', 'song__artist')

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'category', 'order', 'created_at')
    list_filter = ('category',)
    search_fields = ('question', 'answer')
    ordering = ('order', 'id')

@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_site_specific', 'created_at')
    list_filter = ('category', 'is_site_specific')
    search_fields = ('code', 'name', 'meaning', 'common_causes')
    ordering = ('code',)

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'subject', 'user_email', 'status', 'priority', 'ai_generated', 'created_at')
    list_filter = ('status', 'priority', 'category', 'ai_generated')
    search_fields = ('ticket_number', 'user_name', 'user_email', 'subject', 'description')
    ordering = ('-created_at',)

