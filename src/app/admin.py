from django.contrib import admin
from .models import Game # Make sure you import your Game model

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = [
        'game_id',
        'room_code',
        'num_players',
        'current_player',
        'game_over',
        'winner_player_num',
        'is_game_started',
        'disconnected_player', # Added
        'reconnect_timer_start', # Added
        'terminated_due_to_disconnect', # Added
        'created_at',
        'last_updated',
    ]
    
    readonly_fields = [
        'game_id',
        'created_at',
        'last_updated',
    ]

    # You might have other configurations here
    # filter_horizontal = []
    # fieldsets = ()