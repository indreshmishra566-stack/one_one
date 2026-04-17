"""
MatchChatConsumer
-----------------
Persistent chat between two mutually matched users.
Room name is deterministic from sorted user IDs.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone


class MatchChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.partner_username = self.scope['url_route']['kwargs']['username']

        try:
            self.partner = await self.get_user(self.partner_username)
        except User.DoesNotExist:
            await self.close()
            return

        # Verify match exists
        is_matched = await self.check_match()
        if not is_matched:
            await self.close()
            return

        # Deterministic room name from sorted user IDs
        uid1, uid2 = sorted([self.user.id, self.partner.id])
        self.room_group = f'match_chat_{uid1}_{uid2}'

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group'):
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            content = data.get('content', '').strip()
            if not content:
                return

            timestamp = timezone.now().strftime('%H:%M')
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

    async def chat_message(self, event):
        await self.send(json.dumps({
            'type': 'message',
            'sender': event['sender'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'is_mine': event['sender'] == self.user.username,
        }))

    async def typing_indicator(self, event):
        if event['sender'] != self.user.username:
            await self.send(json.dumps({
                'type': 'typing',
                'sender': event['sender'],
                'is_typing': event['is_typing'],
            }))

    @database_sync_to_async
    def get_user(self, username):
        return User.objects.get(username=username)

    @database_sync_to_async
    def check_match(self):
        from core.models import Match
        from django.db.models import Q
        uid1, uid2 = sorted([self.user.id, self.partner.id])
        return Match.objects.filter(user1_id=uid1, user2_id=uid2).exists()

    @database_sync_to_async
    def save_message(self, content):
        from core.models import Message
        Message.objects.create(
            sender=self.user,
            receiver=self.partner,
            content=content,
        )
