"""
LiveChatConsumer
----------------
Handles real-time messaging inside a paired live session room.
Room is identified by room_id (UUID fragment).
Messages are broadcast to all members of the room group.
Messages are also persisted to the DB.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone


class LiveChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group = f'livechat_{self.room_id}'

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # Announce join
        await self.channel_layer.group_send(self.room_group, {
            'type': 'system_message',
            'text': f'{self.user.username} joined the session ✦',
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_send(self.room_group, {
            'type': 'system_message',
            'text': f'{self.user.username} left the session.',
        })
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            content = data.get('content', '').strip()
            if not content:
                return

            timestamp = timezone.now().strftime('%H:%M')

            # Persist to DB
            await self.save_message(content)

            await self.channel_layer.group_send(self.room_group, {
                'type': 'chat_message',
                'sender': self.user.username,
                'content': content,
                'timestamp': timestamp,
            })

        elif msg_type == 'typing':
            await self.channel_layer.group_send(self.room_group, {
                'type': 'typing_indicator',
                'sender': self.user.username,
                'is_typing': data.get('is_typing', False),
            })

    # ── Handlers ──────────────────────────────────────────────────────────

    async def chat_message(self, event):
        await self.send(json.dumps({
            'type': 'message',
            'sender': event['sender'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'is_mine': event['sender'] == self.user.username,
        }))

    async def system_message(self, event):
        await self.send(json.dumps({
            'type': 'system',
            'text': event['text'],
        }))

    async def typing_indicator(self, event):
        if event['sender'] != self.user.username:
            await self.send(json.dumps({
                'type': 'typing',
                'sender': event['sender'],
                'is_typing': event['is_typing'],
            }))

    # ── DB ────────────────────────────────────────────────────────────────

    @database_sync_to_async
    def save_message(self, content: str):
        from core.models import LiveMessage
        LiveMessage.objects.create(
            room_id=self.room_id,
            sender=self.user,
            content=content,
        )
