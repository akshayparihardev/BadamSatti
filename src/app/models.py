# badam_satti_app/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _
import json
import uuid
from django.utils import timezone
import random
from datetime import timedelta

# --- Constants for the game ---
CARD_RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']
CARD_SUITS = ['H', 'D', 'C', 'S']

CARDS_MAP = {
    1: "AH", 2: "2H", 3: "3H", 4: "4H", 5: "5H", 6: "6H", 7: "7H", 8: "8H", 9: "9H", 10: "TH", 11: "JH", 12: "QH", 13: "KH",
    14: "AD", 15: "2D", 16: "3D", 17: "4D", 18: "5D", 19: "6D", 20: "7D", 21: "8D", 22: "9D", 23: "TD", 24: "JD", 25: "QD", 26: "KD",
    27: "AC", 28: "2C", 29: "3C", 30: "4C", 31: "5C", 32: "6C", 33: "7C", 34: "8C", 35: "9C", 36: "TC", 37: "JC", 38: "QC", 39: "KC",
    40: "AS", 41: "2S", 42: "3S", 43: "4S", 44: "5S", 45: "6S", 46: "7S", 47: "8S", 48: "9S", 49: "TS", 50: "JS", 51: "QS", 52: "KS",
}


class Game(models.Model):
    game_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_code = models.CharField(max_length=10, unique=True)
    num_players = models.IntegerField(default=4)
    players_data = models.TextField(default='[]')
    current_player = models.IntegerField(default=1)
    desk_cards = models.TextField(default='{}')
    is_game_started = models.BooleanField(default=False)
    game_over = models.BooleanField(default=False)
    winner_player_num = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    disconnected_player = models.IntegerField(null=True, blank=True)
    reconnect_timer_start = models.DateTimeField(null=True, blank=True)
    terminated_due_to_disconnect = models.BooleanField(default=False)
    game_scores = models.TextField(default='{}')


    def __str__(self):
        return f"Game {self.room_code}"

    @staticmethod
    def _get_rank_value(rank_name):
        if rank_name in CARD_RANKS:
            return CARD_RANKS.index(rank_name) + 1
        return None

    @staticmethod
    def _get_rank_name(rank_value):
        if 1 <= rank_value <= 13:
            return CARD_RANKS[rank_value - 1]
        return None

    def _calculate_and_save_scores(self, final_players_data):
        scores = []
        rank_to_value = {rank: i + 1 for i, rank in enumerate(CARD_RANKS)}
        rank_to_value['T'] = 10

        for player in final_players_data:
            player_score = 0
            for card_num, card_name in player['hand']:
                rank = card_name[:-1]
                player_score += rank_to_value.get(rank, 0)

            scores.append({
                'name': player['name'],
                'player_num': player['player_num'],
                'score': player_score,
                'remaining_cards': len(player['hand'])
            })

        scores.sort(key=lambda x: x['score'])
        self.game_scores = json.dumps(scores)


    def _get_valid_moves(self, player_hand, desk_cards):
        valid_moves = []
        is_desk_empty = all(not cards for cards in desk_cards.values())

        if is_desk_empty:
            for card_num, card_name in player_hand:
                if card_num == 7:
                    valid_moves.append(card_num)
            return valid_moves

        desk_suit_cards = {suit: [c[1] for c in cards] for suit, cards in desk_cards.items()}

        for card_num, card_name in player_hand:
            rank = card_name[:-1]
            suit = card_name[-1]

            if rank == '7':
                valid_moves.append(card_num)
                continue
            
            if ('7' + suit) not in desk_suit_cards.get(suit, []):
                continue

            rank_value = self._get_rank_value(rank)
            next_lower_rank_name = self._get_rank_name(rank_value - 1)
            next_higher_rank_name = self._get_rank_name(rank_value + 1)
            
            can_place = False
            if next_lower_rank_name and (next_lower_rank_name + suit) in desk_suit_cards.get(suit, []):
                can_place = True
            if not can_place and next_higher_rank_name and (next_higher_rank_name + suit) in desk_suit_cards.get(suit, []):
                can_place = True
            
            if can_place:
                valid_moves.append(card_num)

        return valid_moves

    def update_game_state_after_move(self, card_num, player_num):
        players_data = json.loads(self.players_data)
        desk_cards = json.loads(self.desk_cards)

        card_to_play = None
        for p_data in players_data:
            if p_data['player_num'] == player_num:
                card_to_play = next((card for card in p_data['hand'] if card[0] == card_num), None)
                if card_to_play:
                    p_data['hand'] = [card for card in p_data['hand'] if card[0] != card_num]
                break

        if not card_to_play:
            return False

        card_name = card_to_play[1]
        suit = card_name[-1]
        if suit not in desk_cards:
            desk_cards[suit] = []
        desk_cards[suit].append(card_to_play)
        desk_cards[suit].sort(key=lambda x: x[0])

        player_hand_after_move = next((p['hand'] for p in players_data if p['player_num'] == player_num), None)
        if not player_hand_after_move:
            self.game_over = True
            self.winner_player_num = player_num
            self._calculate_and_save_scores(players_data)

        self.players_data = json.dumps(players_data)
        self.desk_cards = json.dumps(desk_cards)
        self.current_player = (self.current_player % self.num_players) + 1
        
        self.save()
        return True

    def get_player_hand(self, player_num):
        players_data = json.loads(self.players_data)
        for player in players_data:
            if player['player_num'] == player_num:
                return player['hand']
        return None

    def get_player_data(self, player_num):
        players_data = json.loads(self.players_data)
        return next((p for p in players_data if p['player_num'] == player_num), None)

    def get_players_data(self):
        return json.loads(self.players_data)

    def get_desk_cards(self):
        return json.loads(self.desk_cards)

    def is_player_turn(self, player_num):
        return self.current_player == player_num

    def get_valid_moves_for_player(self, player_num):
        player_hand = self.get_player_hand(player_num)
        desk_cards = self.get_desk_cards()
        return self._get_valid_moves(player_hand, desk_cards)

    def pass_turn(self, player_num):
        self.current_player = (self.current_player % self.num_players) + 1
        self.save()
        return True, "Turn passed successfully."

    def handle_player_disconnect(self, player_num):
        if not self.disconnected_player:
            self.disconnected_player = player_num
            self.reconnect_timer_start = timezone.now()
            self.save()
            print(f"DEBUG: Player {player_num} disconnected from game {self.game_id}. Timer started.")

    def check_for_termination(self):
        if self.disconnected_player and self.reconnect_timer_start:
            time_elapsed = timezone.now() - self.reconnect_timer_start
            if time_elapsed.total_seconds() >= 120:
                disconnected_player_num = self.disconnected_player
                players_data = json.loads(self.players_data)

                remaining_players = [p for p in players_data if p['player_num'] != disconnected_player_num]

                if not remaining_players or len(remaining_players) < 2:
                    self.game_over = True
                    self.terminated_due_to_disconnect = True
                    self.winner_player_num = None
                else:
                    remaining_players.sort(key=lambda p: p['player_num'])

                    current_player_original_num = self.current_player
                    new_current_player_num = self.current_player

                    for i, player in enumerate(remaining_players):
                        new_num = i + 1
                        if player['player_num'] == current_player_original_num:
                            new_current_player_num = new_num
                        player['player_num'] = new_num

                    if self.current_player == disconnected_player_num:
                        self.current_player = disconnected_player_num
                        if self.current_player > len(remaining_players):
                            self.current_player = 1
                    else:
                        self.current_player = new_current_player_num

                    self.players_data = json.dumps(remaining_players)
                    self.num_players = len(remaining_players)

                self.disconnected_player = None
                self.reconnect_timer_start = None
                self.save()
                print(f"DEBUG: Player {disconnected_player_num} removed due to timeout. Game continues.")
                return True
        return False

    def update_player_ping_time(self, player_num):
        players_data = json.loads(self.players_data)
        for player in players_data:
            if player['player_num'] == player_num:
                player['last_ping_time'] = timezone.now().isoformat()
                break
        self.players_data = json.dumps(players_data)
        self.save()

    def check_for_player_inactivity(self, ping_timeout_seconds=20):
        if self.game_over or not self.is_game_started or self.disconnected_player is not None:
            return

        players_data = json.loads(self.players_data)
        for player in players_data:
            if 'last_ping_time' in player and player['last_ping_time']:
                try:
                    last_ping_time = timezone.datetime.fromisoformat(player['last_ping_time'])
                    time_since_last_ping = timezone.now() - last_ping_time

                    if time_since_last_ping.total_seconds() > ping_timeout_seconds:
                        print(f"DEBUG: Player {player['player_num']} detected as inactive. Marking as disconnected.")
                        self.handle_player_disconnect(player['player_num'])
                        break
                except (ValueError, TypeError):
                    print(f"DEBUG: Invalid last_ping_time for Player {player['player_num']}. Setting now.")
                    self.update_player_ping_time(player['player_num'])