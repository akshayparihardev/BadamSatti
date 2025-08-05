# badam_satti_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index/', views.index, name='index'),
    path('create_room/', views.create_room, name='create_room'),
    path('join_room/', views.join_room, name='join_room'),
    path('waiting_room/<str:room_code>/', views.wait_room, name='waiting_room'),
    path('rules/', views.rules, name='rules'),
    path('play_game/<str:game_id>/', views.game_view, name='play_game'),
    path('pass_turn/<str:game_id>/', views.pass_turn, name='pass_turn'),
    path('get_game_state/<str:game_id>/', views.get_game_state, name='get_game_state'),
    path('play_card/<str:game_id>/', views.play_card, name='play_card'),
    path('start_game/<str:game_id>/', views.start_game, name='start_game'),
    path('check_room_status/<str:room_code>/', views.check_room_status, name='check_room_status'),
    path('remove_player/<str:game_id>/', views.remove_player, name='remove_player'),
    path('reconnect_player/<str:game_id>/', views.reconnect_player, name='reconnect_player'),
    path('player_ping/<str:game_id>/', views.player_ping, name='player_ping'),

    # The old rejoin URLs have been removed as this functionality is now handled by the 'join_room' view.
]