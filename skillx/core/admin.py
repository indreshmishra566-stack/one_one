from django.contrib import admin
from .models import Profile, Match, Message, LiveMessage

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'skills_have', 'skills_want', 'is_live')
    search_fields = ('user__username', 'skills_have', 'skills_want')
    list_filter = ('is_live',)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user1__username', 'user2__username')
    ordering = ('-score',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'content', 'timestamp')
    list_filter = ('timestamp',)

@admin.register(LiveMessage)
class LiveMessageAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'sender', 'content', 'timestamp')
    list_filter = ('room_id',)
    search_fields = ('sender__username', 'content')
