# your_app_name/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
import asyncio
from asgiref.sync import sync_to_async
from datetime import timedelta
import datetime # Import datetime for timedelta

from .models import Game # Assuming your Game model is in .models

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope['url_route']['kwargs']['room_code']
        self.room_group_name = f'game_{self.room_code}'
        self.player_num = self.scope['session'].get('player_num') # Assuming you store player_num in session
        self.game_id = self.scope['session'].get('game_id') # Get game_id from session

        if not self.player_num or not self.game_id:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        game = await sync_to_async(Game.objects.get)(game_id=self.game_id)
        
        # Handle reconnection
        if game.disconnected_player == self.player_num and game.is_halted:
            reconnected, message = await sync_to_async(game.handle_player_reconnect)(self.player_num)
            if reconnected:
                # Notify all players in the group that the player reconnected
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_message',
                        'message': 'player_reconnected',
                        'player_num': self.player_num,
                        'status_message': message
                    }
                )
                await self.send_game_state_to_group() # Send updated state to all
        
        # Start the periodic termination check task for this game, only if not already started
        # In a production environment, a more robust solution like a Celery Beat task
        # or a shared timer per game instance would be better. This is for demonstration.
        if not hasattr(self, 'termination_check_task') or self.termination_check_task.done():
            self.termination_check_task = asyncio.create_task(self.periodic_termination_check())


    async def disconnect(self, close_code):
        print(f"Player {self.player_num} disconnected from {self.room_code} (game: {self.game_id})")
        
        # Cancel the periodic check task if it exists
        if hasattr(self, 'termination_check_task') and not self.termination_check_task.done():
            self.termination_check_task.cancel()

        try:
            game = await sync_to_async(Game.objects.get)(game_id=self.game_id)
            await sync_to_async(game.handle_player_disconnect)(self.player_num)
            
            # Notify all players in the group that a player disconnected
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_message',
                    'message': 'player_disconnected',
                    'player_num': self.player_num,
                    'reconnect_timer_start': str(game.reconnect_timer_start) if game.reconnect_timer_start else None, # Send as string
                    'status_message': f"Player {self.player_num} disconnected. Game halted. Reconnect timer started (2 minutes)."
                }
            )
            # Ensure game state is broadcast after disconnect
            await self.send_game_state_to_group()

        except Game.DoesNotExist:
            print(f"Game {self.game_id} not found on disconnect.")
        except Exception as e:
            print(f"Error handling disconnect for game {self.game_id}: {e}")

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )


    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        game = await sync_to_async(Game.objects.get)(game_id=self.game_id)

        # Before processing any game-related action, check if the game is halted
        if game.is_halted and message_type not in ['player_reconnect_attempt']: # Allow reconnect attempts
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Game is currently halted due to a disconnected player. No moves can be made.'
            }))
            return

        if message_type == 'play_card':
            card_num = data.get('card_num')
            # Check player turn and if game is halted within the model method
            success, msg = await sync_to_async(game.update_game_state_after_move)(card_num, self.player_num)
            if success:
                await self.send_game_state_to_group()
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': msg
                }))
        elif message_type == 'pass_turn':
            # Check player turn and if game is halted within the model method
            success, msg = await sync_to_async(game.pass_turn)(self.player_num)
            if success:
                await self.send_game_state_to_group()
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': msg
                }))


    async def game_message(self, event):
        # This function receives messages from the channel layer group and sends them to the WebSocket
        message_type = event['type']
        if message_type == 'game_message':
            await self.send(text_data=json.dumps({
                'type': event['message'], # e.g., 'player_disconnected', 'player_reconnected', 'game_terminated'
                'player_num': event.get('player_num'),
                'reconnect_timer_start': event.get('reconnect_timer_start'),
                'status_message': event.get('status_message'),
                'time_remaining': event.get('time_remaining'), # For timer updates
                'game_over': event.get('game_over', False), # For game terminated
            }))
        elif message_type == 'game_state_update':
            await self.send(text_data=json.dumps({
                'type': 'game_state_update',
                'game_data': event['game_data']
            }))
            
    async def send_game_state_to_group(self):
        try:
            game = await sync_to_async(Game.objects.get)(game_id=self.game_id)
            players_data_list = json.loads(game.players_data)
            
            # To avoid sending other players' hand data, send hand size
            players_info = []
            for p_data in players_data_list:
                players_info.append({
                    'player_num': p_data['player_num'],
                    'name': p_data['name'],
                    'hand_size': len(p_data['hand'])
                })

            game_data = {
                'game_id': str(game.game_id),
                'room_code': game.room_code,
                'num_players': game.num_players,
                'players': players_info,
                'current_player_turn': game.current_player,
                'desk_cards': json.loads(game.desk_cards),
                'is_game_started': game.is_game_started,
                'game_over': game.game_over,
                'winner_player_num': game.winner_player_num,
                'disconnected_player': game.disconnected_player,
                'reconnect_timer_start': str(game.reconnect_timer_start) if game.reconnect_timer_start else None,
                'is_halted': game.is_halted,
            }

            # Calculate time remaining for reconnection for the frontend
            if game.is_halted and game.disconnected_player and game.reconnect_timer_start and not game.game_over:
                time_limit = timedelta(minutes=2)
                elapsed_time = timezone.now() - game.reconnect_timer_start
                time_left_seconds = (time_limit - elapsed_time).total_seconds()
                game_data['reconnect_time_left'] = max(0, int(time_left_seconds))
            else:
                game_data['reconnect_time_left'] = 0


            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_state_update',
                    'game_data': game_data
                }
            )
        except Game.DoesNotExist:
            print(f"Game {self.game_id} not found during state update.")
        except Exception as e:
            print(f"Error sending game state update for game {self.game_id}: {e}")


    async def periodic_termination_check(self):
        try:
            while True:
                game = await sync_to_async(Game.objects.get)(game_id=self.game_id)
                
                # Only run termination check if a player is disconnected and game is halted
                if game.disconnected_player and game.is_halted and not game.game_over:
                    terminated, message = await sync_to_async(game.check_for_game_termination)()
                    
                    if terminated:
                        print(f"Game {self.game_id} terminated: {message}")
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'game_message',
                                'message': 'game_terminated',
                                'status_message': message,
                                'game_over': True,
                                'player_num': game.disconnected_player # Inform which player caused termination
                            }
                        )
                        await self.send_game_state_to_group() # Send final terminated state
                        break # Stop this loop as the game is terminated
                    else:
                        # If not terminated, but still halted, send updated timer info
                        time_limit = timedelta(minutes=2)
                        elapsed_time = timezone.now() - game.reconnect_timer_start
                        time_left_seconds = (time_limit - elapsed_time).total_seconds()
                        
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                'type': 'game_message',
                                'message': 'reconnect_timer_update',
                                'player_num': game.disconnected_player,
                                'time_remaining': max(0, round(time_left_seconds)),
                                'status_message': f"Player {game.disconnected_player} is disconnected. Game halted. Time remaining: {max(0, round(time_left_seconds))} seconds."
                            }
                        )
                elif game.game_over:
                    # If game is already over (by winning or previous termination), stop the check
                    break
                elif not game.is_halted and not game.disconnected_player:
                    # If game is resumed and no one is disconnected, no need for this periodic check
                    break

                await asyncio.sleep(5) # Check every 5 seconds
        except asyncio.CancelledError:
            print(f"Periodic termination check task for game {self.game_id} cancelled.")
        except Game.DoesNotExist:
            print(f"Game {self.game_id} not found during periodic check, terminating task.")
        except Exception as e:
            print(f"Error in periodic termination check for game {self.game_id}: {e}")