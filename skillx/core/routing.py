from django.urls import re_path
from core.consumers import LiveQueueConsumer, LiveChatConsumer, MatchChatConsumer

websocket_urlpatterns = [
    re_path(r'^ws/queue/$', LiveQueueConsumer.as_asgi()),
    re_path(r'^ws/live/(?P<room_id>[a-zA-Z0-9_-]+)/$', LiveChatConsumer.as_asgi()),
    re_path(r'^ws/chat/(?P<username>[\w.@+-]+)/$', MatchChatConsumer.as_asgi()),
]
