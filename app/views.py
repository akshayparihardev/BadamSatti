import random
import json
import uuid # For generating unique game IDs

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from datetime import timedelta
import re

from .models import Game # Your new Game model

# --- Your original game logic functions ---
CARDS_MAP = {
    1:"AH", 2:"2H", 3:"3H", 4:"4H", 5:"5H", 6:"6H", 7:"7H", 8:"8H", 9:"9H", 10:"TH", 11:"JH", 12:"QH", 13:"KH",
    14:"AD", 15:"2D", 16:"3D", 17: "4D", 18: "5D", 19: "6D", 20: "7D", 21: "8D", 22: "9D", 23: "TD", 24: "JD", 25: "QD", 26: "KD",
    27: "AC", 28: "2C", 29: "3C", 30: "4C", 31: "5C", 32: "6C", 33: "7C", 34: "8C", 35: "9C", 36: "TC", 37: "JC", 38: "QC", 39: "KC",
    40: "AS", 41: "2S", 42: "3S", 43: "4S", 44: "5S", 45: "6S", 46: "7S", 47: "8S", 48: "9S", 49: "TS", 50: "JS", 51: "QS", 52: "KS",
}

def create_shuffled_deck():
    deck = [(num, card_str) for num, card_str in CARDS_MAP.items()]
    random.shuffle(deck)
    return deck

def get_cards_distributed(shuffled_deck, num_players):
    players_hands = {i: [] for i in range(1, num_players + 1)}
    current_deck = list(shuffled_deck)
    while current_deck:
        for player_num in range(1, num_players + 1):
            if not current_deck:
                break
            card = current_deck.pop(0)
            players_hands[player_num].append(card)
    return players_hands

# --- Django Views ---
def index(request):
    return render(request, 'index.html')

def rules(request):
    return render(request, 'rules.html')

def create_room(request):
    if request.method == 'POST':
        player_name = request.POST.get('player_name')
        num_players = request.POST.get('num_players')

        if not player_name or not num_players:
            return HttpResponseBadRequest("Player name and number of players are required.")

        num_players = int(num_players)

        while True:
            room_code = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
            if not Game.objects.filter(room_code=room_code).exists():
                break

        players_data = json.dumps([
            {"player_num": 1, "name": player_name, "hand": [], "last_ping_time": timezone.now().isoformat()}
        ])

        game = Game.objects.create(
            room_code=room_code,
            num_players=num_players,
            players_data=players_data,
            current_player=1,
            is_game_started=False,
            game_over=False
        )

        request.session['player_name'] = player_name
        request.session['room_code'] = room_code
        request.session['player_num'] = 1
        request.session['game_id'] = str(game.game_id)

        return redirect('waiting_room', room_code=room_code)

    # If the request is not POST, just redirect to the homepage.
    return redirect('index')


def join_room(request):
    if request.method == 'POST':
        room_code = request.POST.get('room_code', '').upper().strip()
        player_name = request.POST.get('player_name', '').strip()

        if not room_code or not player_name:
            return render(request, 'join-room.html', {'error': 'Room code and player name are required.'})

        try:
            game = Game.objects.get(room_code=room_code)
        except Game.DoesNotExist:
            return render(request, 'join-room.html', {'error': f'No game found with room code "{room_code}".'})

        if not game.is_game_started and (timezone.now() - game.created_at).total_seconds() > 300:
            return render(request, 'join-room.html', {'error': 'This game invitation has expired.'})

        players_data = json.loads(game.players_data)

        existing_player_data = next((p for p in players_data if p['name'].lower() == player_name.lower()), None)

        if existing_player_data:
            player_num = existing_player_data['player_num']

            request.session['player_name'] = existing_player_data['name']
            request.session['room_code'] = room_code
            request.session['player_num'] = player_num
            request.session['game_id'] = str(game.game_id)

            if game.disconnected_player == player_num:
                game.disconnected_player = None
                game.reconnect_timer_start = None
                game.save()
                print(f"DEBUG: Player {player_name} (Player {player_num}) successfully rejoined game {game.game_id} via room code.")

            if game.is_game_started:
                return redirect('play_game', game_id=str(game.game_id))
            else:
                return redirect('waiting_room', room_code=room_code)

        else:
            if game.is_game_started:
                return render(request, 'join-room.html', {'error': 'This game has already started. You cannot join as a new player.'})

            if len(players_data) >= game.num_players:
                return render(request, 'join-room.html', {'error': 'This room is already full.'})

            new_player_num = len(players_data) + 1
            players_data.append({
                "player_num": new_player_num,
                "name": player_name,
                "hand": [],
                "last_ping_time": timezone.now().isoformat()
            })
            game.players_data = json.dumps(players_data)
            game.save()

            request.session['player_name'] = player_name
            request.session['room_code'] = room_code
            request.session['player_num'] = new_player_num
            request.session['game_id'] = str(game.game_id)

            print(f"DEBUG: {player_name} joined room {room_code} as Player {new_player_num}.")

            return redirect('waiting_room', room_code=room_code)

    return render(request, 'join-room.html')

def wait_room(request, room_code):
    try:
        game = get_object_or_404(Game, room_code=room_code)

        player_name = request.session.get('player_name')
        player_num = request.session.get('player_num')
        session_game_id = request.session.get('game_id')

        players_data = json.loads(game.players_data)
        player_exists_in_game = any(p['name'] == player_name for p in players_data)

        if not player_name or not player_num or str(game.game_id) != session_game_id or not player_exists_in_game:
             if 'player_name' in request.session: del request.session['player_name']
             if 'room_code' in request.session: del request.session['room_code']
             if 'player_num' in request.session: del request.session['player_num']
             if 'game_id' in request.session: del request.session['game_id']
             return redirect('join_room')

        is_host = (player_num == 1)
        room_share_url = request.build_absolute_uri(f'/join_room/?room_code={room_code}')

        return render(request, 'waiting-room.html', {
            'room_code': room_code,
            'is_host': is_host,
            'num_players_needed': game.num_players,
            'room_share_url': room_share_url,
            'room_game_id': str(game.game_id)
        })
    except Exception as e:
        print(f"Error in waiting room view: {e}")
        return redirect('index')

@require_GET
def check_room_status(request, room_code):
    try:
        game = Game.objects.get(room_code=room_code)

        if not game.is_game_started:
            time_elapsed = (timezone.now() - game.created_at).total_seconds()
            if time_elapsed > 300: # 5 minutes
                game.delete()
                return JsonResponse({
                    'status': 'expired',
                    'message': 'Room expired because not all players joined within 5 minutes.',
                    'redirect_url': '/index/'
                })

        players_data = json.loads(game.players_data)
        current_players = [{'name': p['name'], 'player_num': p['player_num']} for p in players_data]

        player_name = request.session.get('player_name')
        player_exists_in_game = any(p['name'] == player_name for p in players_data)

        if not player_exists_in_game:
            return JsonResponse({'status': 'redirect', 'message': 'You have been removed from the room.', 'redirect_url': '/join_room/'})

        if game.is_game_started:
            return JsonResponse({
                'status': 'started',
                'redirect_url': f'/play_game/{game.game_id}/'
            })

        time_left = 300 - (timezone.now() - game.created_at).total_seconds()

        return JsonResponse({
            'status': 'waiting',
            'current_players': current_players,
            'is_game_started': game.is_game_started,
            'num_players': game.num_players,
            'game_id': str(game.game_id),
            'time_left_seconds': int(max(0, time_left))
        })
    except Game.DoesNotExist:
        return JsonResponse({
            'status': 'expired',
            'message': 'Room not found. It may have expired or never existed.',
            'redirect_url': '/index/'
        }, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

@require_GET
def game_view(request, game_id):
    try:
        game = get_object_or_404(Game, game_id=game_id)

        player_name = request.session.get('player_name')
        player_num = request.session.get('player_num')
        session_game_id = request.session.get('game_id')

        players_data = json.loads(game.players_data)
        player_exists_in_game = any(p['name'] == player_name for p in players_data)

        if not player_name or not player_num or str(game.game_id) != session_game_id or not player_exists_in_game:
            return redirect('index')

        return render(request, 'BadamSatti.html', {'game_id': game_id})
    except Exception as e:
        return redirect('index')

@require_GET
def get_game_state(request, game_id):
    try:
        game = Game.objects.get(game_id=game_id)

        player_num = request.session.get('player_num')

        players_data_list = json.loads(game.players_data)

        current_player_data = next((p for p in players_data_list if p['player_num'] == player_num), None)

        if not current_player_data:
            return JsonResponse({'status': 'error', 'message': 'Player not found in this game.'}, status=403)

        player_hand = current_player_data.get('hand', [])

        game.check_for_termination()

        if game.disconnected_player is None and game.is_game_started and not game.game_over:
            game.check_for_player_inactivity(ping_timeout_seconds=20)

        valid_moves = game.get_valid_moves_for_player(player_num)

        players_info = []
        for p_data in players_data_list:
            players_info.append({
                'player_num': p_data['player_num'],
                'name': p_data['name'],
                'hand_size': len(p_data['hand'])
            })

        game_message = ""
        if game.game_over:
            if game.terminated_due_to_disconnect:
                game_message = "Game terminated as a player did not reconnect in time."
            elif game.winner_player_num:
                winner_data = game.get_player_data(game.winner_player_num)
                winner_name = winner_data['name'] if winner_data else f"Player {game.winner_player_num}"
                game_message = f"Game Over! The winner is {winner_name} ❤️✨🎉"

        response_data = {
            'status': 'success',
            'room_code': game.room_code,
            'num_players': game.num_players,
            'players': players_info,
            'current_player_turn': game.current_player,
            'desk_cards': json.loads(game.desk_cards),
            'your_hand': player_hand,
            'your_player_num': player_num,
            'valid_moves': valid_moves,
            'game_over': game.game_over,
            'winner_player_num': game.winner_player_num,
            'is_game_started': game.is_game_started,
            'message': game_message,
            'disconnected_player': game.disconnected_player,
            'terminated_due_to_disconnect': game.terminated_due_to_disconnect,
        }
        
        if game.game_over:
            try:
                response_data['scores'] = json.loads(game.game_scores)
            except (json.JSONDecodeError, TypeError):
                response_data['scores'] = []

        if game.disconnected_player is not None and game.reconnect_timer_start:
            time_since_disconnect = timezone.now() - game.reconnect_timer_start
            time_left_seconds = 120 - time_since_disconnect.total_seconds()
            response_data['reconnect_time_left'] = max(0, int(time_left_seconds))
        else:
            response_data['reconnect_time_left'] = 0

        return JsonResponse(response_data)
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Game not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

@require_POST
def play_card(request, game_id):
    try:
        game = Game.objects.get(game_id=game_id)

        if game.disconnected_player is not None or game.terminated_due_to_disconnect:
            return JsonResponse({'status': 'error', 'message': 'Game is currently paused or terminated.'}, status=400)

        player_num = request.session.get('player_num')
        if not player_num or game.current_player != player_num:
            return JsonResponse({'status': 'error', 'message': 'It is not your turn.'}, status=403)

        data = json.loads(request.body)
        card_num_to_play = data.get('card_num')

        if not card_num_to_play:
            return JsonResponse({'status': 'error', 'message': 'Card not specified.'}, status=400)

        valid_moves = game.get_valid_moves_for_player(player_num)
        if card_num_to_play not in valid_moves:
            return JsonResponse({'status': 'error', 'message': 'Invalid move.'}, status=400)

        game.update_game_state_after_move(card_num_to_play, player_num)

        game.refresh_from_db()

        if game.game_over:
            winner_data = game.get_player_data(player_num)
            winner_name = winner_data['name'] if winner_data else f"Player {player_num}"
            return JsonResponse({'status': 'success', 'game_over': True, 'message': f'{winner_name} has won the game!'})

        return JsonResponse({'status': 'success', 'game_over': False})
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Game not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

@require_POST
def pass_turn(request, game_id):
    try:
        game = Game.objects.get(game_id=game_id)

        if game.disconnected_player is not None or game.terminated_due_to_disconnect:
            return JsonResponse({'status': 'error', 'message': 'Game is currently paused.'}, status=400)

        player_num = request.session.get('player_num')

        if not player_num or game.current_player != player_num:
            return JsonResponse({'status': 'error', 'message': 'It is not your turn.'}, status=403)

        success, message = game.pass_turn(player_num)

        if success:
            return JsonResponse({'status': 'success', 'message': message})
        else:
            return JsonResponse({'status': 'error', 'message': message}, status=400)
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Game not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

@require_POST
def start_game(request, game_id):
    try:
        game = get_object_or_404(Game, game_id=game_id)
        player_num = request.session.get('player_num')

        if player_num != 1:
            return JsonResponse({'status': 'error', 'message': 'Only the host can start the game.'}, status=403)

        players_data = json.loads(game.players_data)
        if len(players_data) < game.num_players:
            return JsonResponse({'status': 'error', 'message': 'Not all players have joined yet.'}, status=400)

        if game.is_game_started:
            return JsonResponse({'status': 'error', 'message': 'The game has already started.'}, status=400)

        shuffled_deck = create_shuffled_deck()
        players_hands = get_cards_distributed(shuffled_deck, game.num_players)

        first_player_num = None
        card_7h_num = 7 # The card number for 7 of Hearts

        for p_data in players_data:
            p_num = p_data['player_num']
            if p_num in players_hands:
                p_data['hand'] = players_hands[p_num]
            p_data['last_ping_time'] = timezone.now().isoformat()
            if any(card[0] == card_7h_num for card in p_data['hand']):
                first_player_num = p_num

        if first_player_num is None:
             # Fallback: if 7H isn't found (should never happen), assign to player 1
            first_player_num = 1

        game.players_data = json.dumps(players_data)
        game.current_player = first_player_num
        game.is_game_started = True
        game.desk_cards = json.dumps({ "H": [], "D": [], "C": [], "S": [] })
        game.save()

        return JsonResponse({'status': 'success', 'redirect_url': f'/play_game/{game.game_id}/'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)

@require_POST
def remove_player(request, game_id):
    try:
        game = Game.objects.get(game_id=game_id)
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Game not found.'}, status=404)

    requesting_player_num = request.session.get('player_num')
    if requesting_player_num != 1:
        return JsonResponse({'status': 'error', 'message': 'Only the host can remove players.'}, status=403)

    data = json.loads(request.body)
    player_to_remove_num = data.get('player_num_to_remove')

    if not player_to_remove_num:
        return JsonResponse({'status': 'error', 'message': 'Player number not provided.'}, status=400)

    player_to_remove_num = int(player_to_remove_num)

    if player_to_remove_num == 1:
        return JsonResponse({'status': 'error', 'message': 'You cannot remove yourself.'}, status=400)

    players_data = json.loads(game.players_data)
    new_players_data = [p for p in players_data if p['player_num'] != player_to_remove_num]

    if len(new_players_data) == len(players_data):
        return JsonResponse({'status': 'error', 'message': 'Player not found in the room.'}, status=404)

    # Re-number the remaining players to keep the sequence
    for i, player in enumerate(new_players_data):
        player['player_num'] = i + 1

    game.players_data = json.dumps(new_players_data)
    game.save()

    return JsonResponse({'status': 'success', 'message': 'Player removed successfully.'})

@require_POST
def reconnect_player(request, game_id):
    player_name = request.session.get('player_name')
    player_num = request.session.get('player_num')

    if not player_name or not player_num:
        return JsonResponse({'status': 'error', 'message': 'Session expired. Please rejoin.'}, status=400)

    try:
        game = Game.objects.get(game_id=game_id)

        if game.disconnected_player == player_num:
            game.disconnected_player = None
            game.reconnect_timer_start = None
            game.save()
            return JsonResponse({'status': 'success', 'message': 'Reconnected successfully!'})
        else:
            return JsonResponse({'status': 'error', 'message': 'You are not the disconnected player.'}, status=400)
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Game not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)


@require_POST
def player_ping(request, game_id):
    player_num = request.session.get('player_num')
    player_name = request.session.get('player_name')

    if not player_num or not player_name:
        return JsonResponse({'status': 'error', 'message': 'Session expired.'}, status=401)

    try:
        game = Game.objects.get(game_id=game_id)

        players_data = json.loads(game.players_data)
        player_in_game = any(p['player_num'] == player_num for p in players_data)

        if not player_in_game:
            # This can happen if the player was removed due to timeout
            return JsonResponse({'status': 'error', 'message': 'You are no longer in this game.'}, status=403)

        if game.disconnected_player == player_num:
            game.disconnected_player = None
            game.reconnect_timer_start = None

        game.update_player_ping_time(player_num)

        return JsonResponse({'status': 'success', 'message': 'Ping received.'})
    except Game.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Game not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)