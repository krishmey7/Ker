from django.urls import re_path

from apps.game.consumers import GameRoomConsumer

websocket_urlpatterns = [
    re_path(r"ws/couple/(?P<room_code>\w+)/$", GameRoomConsumer.as_asgi()),
]
