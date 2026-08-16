import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'chat_{self.group_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        user_name = data.get('user_name')
        image_url = data.get('image_url')
        created_at = data.get('created_at')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_name': user_name,
                'image_url': image_url,
                'created_at': created_at
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event.get('message'),
            'user_name': event.get('user_name'),
            'image_url': event.get('image_url'),
            'created_at': event.get('created_at')
        }))
