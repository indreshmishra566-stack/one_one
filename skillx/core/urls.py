from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.edit_profile, name='edit_profile'),

    # Live system
    path('live/', views.live_lobby, name='live_lobby'),
    path('live/room/<str:room_id>/', views.live_room, name='live_room'),

    # Smart match browse
    path('match/', views.find_match, name='find_match'),
    path('matches/', views.my_matches, name='my_matches'),

    # Persistent chat
    path('chat/<str:username>/', views.chat, name='chat'),

    # API
    path('api/queue-status/', views.queue_status, name='queue_status'),
]
