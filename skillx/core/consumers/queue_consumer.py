"""
LiveQueueConsumer
-----------------
Handles the "Go Live" waiting room.
Each user connects → added to channel layer group "live_queue"
Server continuously attempts to pair users using the smart matching engine.
When a pair is found both users are redirected to a shared live chat room.
"""

import json
import asyncio
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from core.matching import find_best_match_from_queue

# In-memory queue: list of {user_id, channel_name, skills_have, skills_want, username}
# In production replace with Redis-backed store
LIVE_QUEUE: list = []
QUEUE_LOCK = asyncio.Lock()


class LiveQueueConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.profile = await self.get_profile()
        if not self.profile:
            await self.close()
            return

        await self.accept()

        async with QUEUE_LOCK:
            # Remove any stale entry for this user
            self._remove_from_queue(self.user.id)

            entry = {
                'user_id': self.user.id,
                'username': self.user.username,
                'channel_name': self.channel_name,
                'skills_have': self.profile['skills_have'],
                'skills_want': self.profile['skills_want'],
            }
            LIVE_QUEUE.append(entry)

        await self.send(json.dumps({
            'type': 'queued',
            'queue_size': len(LIVE_QUEUE),
            'message': 'You\'re in the queue! Searching for your best skill match...',
        }))

        # Start the matching loop
        asyncio.ensure_future(self.try_match())

    async def disconnect(self, close_code):
        async with QUEUE_LOCK:
            self._remove_from_queue(self.user.id)

    def _remove_from_queue(self, user_id: int):
        global LIVE_QUEUE
        LIVE_QUEUE = [e for e in LIVE_QUEUE if e['user_id'] != user_id]

    async def try_match(self):
        """Poll the queue every 2 seconds to find the best match."""
        for attempt in range(30):  # 60 second timeout
            await asyncio.sleep(2)

            async with QUEUE_LOCK:
                # Make sure we're still in queue
                still_queued = any(e['user_id'] == self.user.id for e in LIVE_QUEUE)
                if not still_queued:
                    return

                profile = await self.get_profile()
                if not profile:
                    return

                best_id, score = find_best_match_from_queue(
                    self.user.id,
                    profile['skills_have'],
                    profile['skills_want'],
                    LIVE_QUEUE,
                )

                if best_id:
                    # Find partner entry
                    partner_entry = next((e for e in LIVE_QUEUE if e['user_id'] == best_id), None)
                    if not partner_entry:
                        continue

                    # Generate shared room id
                    room_id = str(uuid.uuid4())[:8]

                    # Remove both from queue
                    self._remove_from_queue(self.user.id)
                    self._remove_from_queue(best_id)

                    # Notify both users
                    matched_payload = {
                        'type': 'matched',
                        'room_id': room_id,
                        'score': score,
                    }

                    # Notify partner via their channel
                    partner_payload = dict(matched_payload)
                    partner_payload['partner_username'] = self.user.username
                    await self.channel_layer.send(
                        partner_entry['channel_name'],
                        {'type': 'send_match', 'payload': partner_payload}
                    )

                    # Notify self
                    await self.send(json.dumps({
                        **matched_payload,
                        'partner_username': partner_entry['username'],
                    }))
                    return

            # Send heartbeat with queue position
            await self.send(json.dumps({
                'type': 'searching',
                'queue_size': len(LIVE_QUEUE),
                'attempt': attempt + 1,
            }))

        # Timeout
        async with QUEUE_LOCK:
            self._remove_from_queue(self.user.id)
        await self.send(json.dumps({
            'type': 'timeout',
            'message': 'No match found right now. Try updating your skills!',
        }))

    # Called by channel layer when partner was found
    async def send_match(self, event):
        await self.send(json.dumps(event['payload']))

    @database_sync_to_async
    def get_profile(self):
        try:
            profile = self.user.profile
            return {
                'skills_have': profile.skills_have,
                'skills_want': profile.skills_want,
            }
        except Exception:
            return None
