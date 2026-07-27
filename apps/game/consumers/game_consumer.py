"""Consumer WebSocket jeu — synchronisation temps réel de la room couple."""
import traceback
from django.db import OperationalError

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.game.services import GameRealtimeService


class GameRoomConsumer(AsyncJsonWebsocketConsumer):
    """Room privée : question IA, réponses, reveal, question suivante."""

    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"].upper()
        self.group_name = f"couple_{self.room_code}"
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close()
            return

        if not await self._user_in_room(user.id):
            await self.close()
            return

        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            state = await self._get_session_state(user.id)
            await self.send_json({"type": "session_state", "payload": state})
        except Exception as exc:
            print("Erreur WebSocket Consumer dans connect:", str(exc))
            traceback.print_exc()
            await self.close()
            return

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """Route les événements client vers le service temps réel."""
        user = self.scope["user"]
        event_type = content.get("type")
        payload = content.get("payload", {})

        try:
            result = await database_sync_to_async(GameRealtimeService.handle_event)(
                room_code=self.room_code,
                user_id=user.id,
                event_type=event_type,
                payload=payload,
            )
        except OperationalError as exc:
            if "locked" in str(exc).lower():
                await self.send_json(
                    {
                        "type": "error",
                        "payload": {
                            "message": "Serveur occupé — réessayez dans une seconde.",
                        },
                    }
                )
                return
            raise
        except Exception as exc:
            print("================ WS ERROR ================")
            print("Erreur WebSocket Consumer dans receive_json:", str(exc))
            print("Received event:", event_type, payload)
            traceback.print_exc()
            print("==========================================")
            await self.send_json(
                {
                    "type": "error",
                    "payload": {
                        "message": f"Erreur interne WebSocket : {str(exc)}",
                    },
                }
            )
            return

        if result and result.get("broadcast"):
            try:
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "room.event", "data": result["broadcast"]},
                )
            except Exception as exc:
                print("Erreur WebSocket Consumer lors de group_send:", str(exc))
                traceback.print_exc()
                await self.send_json(
                    {
                        "type": "error",
                        "payload": {"message": "Erreur de diffusion WebSocket."},
                    }
                )
        elif result is None and event_type == "answer_submitted":
            await self.send_json(
                {
                    "type": "error",
                    "payload": {"message": "Impossible d'enregistrer la réponse. Réessayez."},
                }
            )

    async def room_event(self, event):
        """Diffuse un événement à tous les clients de la room."""
        await self.send_json(event["data"])

    @database_sync_to_async
    def _user_in_room(self, user_id: int) -> bool:
        from apps.couples.models import Couple
        from apps.users.models import User

        couple = Couple.objects.filter(room_code=self.room_code).first()
        if not couple:
            return False
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return False
        return couple.contains(user)

    @database_sync_to_async
    def _get_session_state(self, user_id: int) -> dict:
        return GameRealtimeService.get_room_state(self.room_code, user_id)
