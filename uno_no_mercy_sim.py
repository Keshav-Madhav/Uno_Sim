import os
import json
import random
from pathlib import Path
import gc
from collections import defaultdict

# =================== Setup: Create Data Folder ===================
DATA_DIR = Path(__file__).parent / "simulation_data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
print(f"Created folder: {DATA_DIR}")

# =================== Card & Player Classes ===================
class Card:
    def __init__(self, card_type, color=None, value=None):
        self.type = card_type  # "number", "action", or "wild"
        self.color = color  # "Red", "Blue", "Green", "Yellow" or None (for wild cards)
        self.value = value  # For numbers: 0-9; for actions/wilds: string describing the card
    
    def __str__(self):
        if self.type == "wild":
            return f"{self.value}{f' ({self.color})' if self.color else ''}"
        else:
            return f"{self.color} {self.value}"

class Player:
    def __init__(self, player_id):
        self.id = player_id
        self.hand = []
    
    def draw(self, deck, count=1):
        drawn_cards = []
        for _ in range(count):
            if deck:
                card = deck.pop()
                self.hand.append(card)
                drawn_cards.append(card)
                SimulationStats.increment_draw_count(1)
                SimulationStats.draw_events += 1
        return drawn_cards
    
    def find_best_card(self, top_card):
        if not top_card:
            return self.hand[0] if self.hand else None
        
        # Use active color if top card is wild and has one
        is_wild_with_no_color = top_card.type == "wild" and not top_card.color
        active_color = top_card.color if top_card.color else None
        
        playable_cards = [card for card in self.hand if (
            card.type == "wild" or 
            is_wild_with_no_color or 
            (active_color and (card.color == active_color or card.value == top_card.value)) or
            (not active_color and (card.color == top_card.color or card.value == top_card.value))
        )]
        
        if not playable_cards:
            return None
        
        non_wild_playable = [card for card in playable_cards if card.type != "wild"]
        best_score = -float('inf')
        best_card = None
        
        for card in playable_cards:
            score = 0
            if card.type == "wild":
                score = 0.5 if non_wild_playable else 1
                if card.value == "ColorRoulette":
                    score -= 0.5
            else:
                if active_color and card.color == active_color:
                    score += 10
                if card.value == top_card.value:
                    score += 5
                if card.type == "action":
                    if card.value == "Skip":
                        score += 3
                    elif card.value == "Reverse":
                        score += 2
                    elif card.value == "DiscardColor":
                        score += 2
                    elif card.value in ("Draw2", "Draw4"):
                        score += 1 if len(non_wild_playable) > 1 else 3
                if card.type == "number":
                    if card.value == 0:
                        score += 5 if len(self.hand) > 5 else 2
                    if card.value == 7:
                        score += 5 if len(self.hand) > 5 else 2
            
            if score > best_score:
                best_score = score
                best_card = card
        
        return best_card
    
    def has_matching_card(self, top_card):
        return any(
            card.color == top_card.color or 
            (card.type == "number" and card.value == top_card.value)
            for card in self.hand
        )
    
    def play_card(self, card):
        if not card:
            return None
        
        for i, c in enumerate(self.hand):
            if (c.type == card.type and 
                c.color == card.color and 
                c.value == card.value):
                return self.hand.pop(i)
        return None

# =================== UnoGame Class ===================
class UnoGame:
    def __init__(self, n, m, k, mercy_rule=True, verbose=False, metrics_collector=None, track_one_round_detail=False):
        self.players = [Player(i+1) for i in range(n)]
        self.deck = self.create_deck()
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1
        self.max_turns = k
        self.mercy_rule = mercy_rule
        self.turn_count = 0
        self.verbose = verbose
        self.metrics_collector = metrics_collector
        self.winner_id = None
        self.pending_draw = 0
        self.pending_draw_type = None
        self.track_one_round_detail = track_one_round_detail
        self.game_log = [] if track_one_round_detail else None
        self.winner_hand_snapshot = None
        
        self.shuffle_deck()
        self.deal_initial_cards(m)
        
        start_card = self.deck.pop()
        self.discard_pile.append(start_card)
        self.log_msg(f"Game started with {n} players, {m} cards each, max {k} turns")
        self.log_msg(f"Starting card: {start_card}")
    
    def log_msg(self, message):
        if self.track_one_round_detail and self.game_log is not None:
            self.game_log.append(message)
        if self.verbose:
            print(message)
    
    def create_deck(self):
        colors = ["Red", "Blue", "Green", "Yellow"]
        deck = []
        
        for color in colors:
            # Number cards (0-9, two of each except 0)
            for number in range(10):
                deck.append(Card("number", color, number))
                if number != 0:
                    deck.append(Card("number", color, number))
            
            # Action cards
            for _ in range(3):
                deck.append(Card("action", color, "Skip"))
            for _ in range(2):
                deck.append(Card("action", color, "SkipAll"))
            for _ in range(3):
                deck.append(Card("action", color, "Reverse"))
            for _ in range(3):
                deck.append(Card("action", color, "Draw2"))
            for _ in range(2):
                deck.append(Card("action", color, "Draw4"))
            for _ in range(3):
                deck.append(Card("action", color, "DiscardColor"))
        
        # Wild cards
        for _ in range(8):
            deck.append(Card("wild", None, "ReverseDraw4"))
        for _ in range(4):
            deck.append(Card("wild", None, "Draw6"))
        for _ in range(4):
            deck.append(Card("wild", None, "Draw10"))
        for _ in range(8):
            deck.append(Card("wild", None, "ColorRoulette"))
        
        return deck
    
    def shuffle_deck(self):
        random.shuffle(self.deck)
    
    def deal_initial_cards(self, m):
        for player in self.players:
            player.draw(self.deck, m)
    
    def get_top_card(self):
        return self.discard_pile[-1] if self.discard_pile else None
    
    def play_turn(self):
        turn_draw_count = 0
        current_max_hand_size = max(len(player.hand) for player in self.players)
        if current_max_hand_size > SimulationStats.max_hand_size_ever:
            SimulationStats.max_hand_size_ever = current_max_hand_size
        
        player = self.players[self.current_player_index]
        pre_turn_hand = [str(card) for card in player.hand]
        
        # Handle pending draw stacking
        if self.pending_draw > 0:
            allowed_stacking = {
                "Draw2": ["Draw2", "Draw4", "Draw6", "Draw10"],
                "Draw4": ["Draw4", "Draw6", "Draw10"],
                "Draw6": ["Draw6", "Draw10"],
                "Draw10": ["Draw10"]
            }
            penalty_mapping = {"Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10}
            allowed_responses = allowed_stacking.get(self.pending_draw_type, [])
            
            stackable_cards = [
                card for card in player.hand if (
                    (card.type == "action" and card.value in ("Draw2", "Draw4")) or
                    (card.type == "wild" and card.value in ("Draw6", "Draw10"))
                ) and card.value in allowed_responses
            ]
            
            if stackable_cards:
                card_to_play = stackable_cards[0]
                played_card = player.play_card(card_to_play)
                
                if played_card.type == "wild":
                    color_counts = defaultdict(int)
                    for card in player.hand:
                        if card.color:
                            color_counts[card.color] += 1
                    chosen_color = max(color_counts.items(), key=lambda x: x[1])[0] if color_counts else "Red"
                    played_card.color = chosen_color
                
                self.discard_pile.append(played_card)
                self.pending_draw += penalty_mapping[played_card.value]
                self.pending_draw_type = played_card.value
                SimulationStats.total_stacking_events += 1
                SimulationStats.total_stacked_penalty += penalty_mapping[played_card.value]
                self.log_msg(f"► Player {player.id} stacks with {played_card}, new pending draw: {self.pending_draw}")
                
                if self.metrics_collector:
                    self.metrics_collector(played_card)
                
                self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
                self.turn_count += 1
                SimulationStats.total_cards_drawn_in_turns += turn_draw_count
                if turn_draw_count > SimulationStats.max_cards_drawn_in_turn:
                    SimulationStats.max_cards_drawn_in_turn = turn_draw_count
                return False
            else:
                drawn_cards = player.draw(self.deck, self.pending_draw)
                turn_draw_count += len(drawn_cards)
                SimulationStats.total_pending_draw_resolved += self.pending_draw
                self.log_msg(f"► Player {player.id} cannot stack and draws {self.pending_draw} cards (hand now: {len(player.hand)} cards).")
                self.pending_draw = 0
                self.pending_draw_type = None
                self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
                self.turn_count += 1
                SimulationStats.total_cards_drawn_in_turns += turn_draw_count
                if turn_draw_count > SimulationStats.max_cards_drawn_in_turn:
                    SimulationStats.max_cards_drawn_in_turn = turn_draw_count
                return False
        
        # Normal turn
        top_card = self.get_top_card()
        self.log_msg(f"\n[TURN {self.turn_count + 1}] Player {player.id}'s turn")
        self.log_msg(f"Top card: {top_card}")
        
        best_card = player.find_best_card(top_card)
        if best_card:
            if best_card.type == "wild":
                played_card = player.play_card(best_card)
                color_counts = defaultdict(int)
                for card in player.hand:
                    if card.color:
                        color_counts[card.color] += 1
                chosen_color = max(color_counts.items(), key=lambda x: x[1])[0] if color_counts else "Red"
                played_card.color = chosen_color
                self.discard_pile.append(played_card)
                self.log_msg(f"► Player {player.id} played {played_card}")
                self.log_msg(f"► Chosen color: {chosen_color}")
                self.log_msg(f"► Cards remaining: {len(player.hand)}")
            else:
                played_card = player.play_card(best_card)
                self.discard_pile.append(played_card)
                self.log_msg(f"► Player {player.id} played {played_card}")
                self.log_msg(f"► Cards remaining: {len(player.hand)}")
            
            if self.metrics_collector:
                self.metrics_collector(played_card)
            
            self.handle_card_effects(best_card)
            
            if best_card.type == "number":
                if best_card.value == 0:
                    self.switch_hands_in_cycle()
                elif best_card.value == 7:
                    self.switch_hands_with_choice(player)
        else:
            drawn_cards = player.draw(self.deck, 1)
            turn_draw_count += len(drawn_cards)
            if drawn_cards:
                self.log_msg(f"► Player {player.id} had no valid card and drew 1 card")
                self.log_msg(f"► Cards remaining: {len(player.hand)}")
            else:
                self.log_msg(f"► Player {player.id} had no valid card and deck is empty")
                self.log_msg(f"► Cards remaining: {len(player.hand)}")
        
        # Check for mercy elimination
        if self.mercy_rule and len(player.hand) >= 25:
            self.log_msg(f"⚠️ Player {player.id} is eliminated with {len(player.hand)} cards due to mercy!")
            SimulationStats.total_mercy_eliminations += 1
            self.players.pop(self.current_player_index)
            if self.current_player_index >= len(self.players):
                self.current_player_index = 0
        else:
            self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
        
        self.turn_count += 1
        SimulationStats.total_cards_drawn_in_turns += turn_draw_count
        if turn_draw_count > SimulationStats.max_cards_drawn_in_turn:
            SimulationStats.max_cards_drawn_in_turn = turn_draw_count
        
        if len(player.hand) == 0:
            self.log_msg(f"🏆 Player {player.id} wins!")
            self.winner_hand_snapshot = pre_turn_hand
            self.winner_id = player.id
            return True
        
        return False
    
    def handle_card_effects(self, card):
        penalty_mapping = {"Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10}
        
        if card.type == "action":
            if card.value == "Skip":
                self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
                self.log_msg(f"⚡ Player {self.players[self.current_player_index].id} was skipped!")
            elif card.value == "SkipAll":
                self.log_msg(f"⚡ SkipAll played! All other players are skipped. Player {self.players[self.current_player_index].id} goes again.")
                self.current_player_index = (self.current_player_index - self.direction) % len(self.players)
            elif card.value == "Reverse":
                self.direction *= -1
                self.log_msg(f"⚡ Direction reversed! Now going {'forward' if self.direction > 0 else 'backward'}")
            elif card.value == "Draw2":
                if self.pending_draw == 0:
                    self.pending_draw = penalty_mapping["Draw2"]
                    self.pending_draw_type = "Draw2"
                    self.log_msg(f"⚡ Draw2 played. Pending draw set to 2.")
            elif card.value == "Draw4":
                if self.pending_draw == 0:
                    self.pending_draw = penalty_mapping["Draw4"]
                    self.pending_draw_type = "Draw4"
                    self.log_msg(f"⚡ Draw4 played. Pending draw set to 4.")
            elif card.value == "DiscardColor":
                active_player = self.players[self.current_player_index]
                discard_color = card.color
                discarded = [c for c in active_player.hand if c.color == discard_color]
                active_player.hand = [c for c in active_player.hand if c.color != discard_color]
                self.discard_pile.extend(discarded)
                self.log_msg(f"⚡ Player {active_player.id} discarded {len(discarded)} {discard_color} cards (hand now: {len(active_player.hand)}).")
        
        elif card.type == "wild":
            if card.value == "ReverseDraw4":
                target_index = (self.current_player_index - self.direction) % len(self.players) if self.direction > 0 else (self.current_player_index + 1) % len(self.players)
                target_player = self.players[target_index]
                target_player.draw(self.deck, 4)
                self.log_msg(f"⚡ Player {target_player.id} draws 4 cards due to ReverseDraw4!")
                self.direction *= -1
                self.log_msg(f"⚡ Direction reversed due to ReverseDraw4! Now going {'forward' if self.direction > 0 else 'backward'}")
            elif card.value == "Draw6":
                if self.pending_draw == 0:
                    self.pending_draw = penalty_mapping["Draw6"]
                    self.pending_draw_type = "Draw6"
                    self.log_msg(f"⚡ Draw6 played. Pending draw set to 6.")
            elif card.value == "Draw10":
                if self.pending_draw == 0:
                    self.pending_draw = penalty_mapping["Draw10"]
                    self.pending_draw_type = "Draw10"
                    self.log_msg(f"⚡ Draw10 played. Pending draw set to 10.")
            elif card.value == "ColorRoulette":
                next_player_index = (self.current_player_index + self.direction) % len(self.players)
                next_player = self.players[next_player_index]
                chosen_color = card.color
                
                self.log_msg(f"⚡ ColorRoulette: Player {next_player.id} chooses {chosen_color}")
                draw_count = 0
                while self.deck:
                    drawn_cards = next_player.draw(self.deck, 1)
                    draw_count += len(drawn_cards)
                    if drawn_cards and drawn_cards[0].color == chosen_color:
                        break
                self.log_msg(f"⚡ Player {next_player.id} had to draw {draw_count} cards due to ColorRoulette")
    
    def switch_hands_in_cycle(self):
        n = len(self.players)
        if n <= 1:
            return
        
        temp_hands = [player.hand for player in self.players]
        for i in range(n):
            source_index = (i - self.direction) % n
            self.players[i].hand = temp_hands[source_index]
        
        self.log_msg("⚡ All players' hands have been cycled (card 0 effect).")
        SimulationStats.total_cycles_on_0 += 1
    
    def switch_hands_with_choice(self, current_player):
        current_count = len(current_player.hand)
        target_player = None
        
        for player in self.players:
            if player.id != current_player.id and len(player.hand) < current_count:
                if target_player is None or len(player.hand) < len(target_player.hand):
                    target_player = player
        
        if target_player:
            current_player.hand, target_player.hand = target_player.hand, current_player.hand
            self.log_msg(f"⚡ Player {current_player.id} switched hands with Player {target_player.id} (card 7 effect).")
            SimulationStats.total_switches_on_7 += 1
        else:
            self.log_msg(f"⚡ Player {current_player.id} chose not to switch hands (card 7 effect) because no opponent had fewer cards.")
    
    def check_and_recycle_deck(self):
        if len(self.deck) < 5:
            self.log_msg("♻️ Shuffling discard pile back into deck")
            top_card = self.discard_pile.pop()
            self.deck = self.discard_pile
            self.discard_pile = [top_card] if top_card else []
            self.shuffle_deck()
    
    def print_game_state(self):
        self.log_msg("GAME STATE")
        self.log_msg(f"Turn: {self.turn_count}")
        self.log_msg(f"Direction: {'→' if self.direction > 0 else '←'}")
        self.log_msg(f"Top card: {self.get_top_card()}")
        self.log_msg(f"Deck size: {len(self.deck)}")
        self.log_msg(f"Discard pile: {len(self.discard_pile)}")
        self.log_msg("\nPlayers:")
        for i, player in enumerate(self.players):
            marker = "►" if i == self.current_player_index else " "
            self.log_msg(f"{marker} Player {player.id}: {len(player.hand)} cards")
    
    def start_game(self):
        game_over = False
        while not game_over and self.turn_count < self.max_turns and len(self.players) > 1:
            self.check_and_recycle_deck()
            if self.turn_count % 10 == 0:
                self.print_game_state()
            game_over = self.play_turn()
        
        if not game_over:
            winner_index = 0
            min_cards = float('inf')
            for i, player in enumerate(self.players):
                if len(player.hand) < min_cards:
                    min_cards = len(player.hand)
                    winner_index = i
            self.log_msg(f"🏁 Game Over after {self.turn_count} turns!")
            self.log_msg(f"🏆 Player {self.players[winner_index].id} wins with {min_cards} cards!")
        
        self.log_msg("FINAL STANDINGS")
        sorted_players = sorted(self.players, key=lambda p: len(p.hand))
        for i, player in enumerate(sorted_players):
            self.log_msg(f"{i+1}. Player {player.id}: {len(player.hand)} cards{' 🏆' if i == 0 else ''}")
        
        if len(sorted_players) < len(self.players):
            self.log_msg(f"ELIMINATED PLAYERS: {len(self.players) - len(sorted_players)} players were eliminated")
        
        self.log_msg("GAME STATISTICS")
        self.log_msg(f"Total turns played: {self.turn_count}")
        self.log_msg(f"Cards remaining in deck: {len(self.deck)}")
        self.log_msg(f"Cards in discard pile: {len(self.discard_pile)}")
        self.log_msg(f"Final top card: {self.get_top_card()}")

# =================== Simulation Metrics ===================
class SimulationStats:
    total_games = 0
    total_turns = 0
    turn_counts = defaultdict(int)
    card_play_counts = defaultdict(int)
    special_card_counts = {"Draw2": 0, "Draw4": 0, "Draw6": 0, "Draw10": 0, "ReverseDraw4": 0, "ColorRoulette": 0}
    total_non_numbered_cards = 0
    action_card_count = 0
    wild_card_count = 0
    total_draws = 0
    draw_events = 0
    total_cards_drawn_in_turns = 0
    max_cards_drawn_in_turn = 0
    one_round_game_count = 0
    one_round_game_examples = []
    max_examples_to_store = 5
    total_stacking_events = 0
    total_stacked_penalty = 0
    total_pending_draw_resolved = 0
    total_switches_on_7 = 0
    total_cycles_on_0 = 0
    total_mercy_eliminations = 0
    max_hand_size_ever = 0
    
    @classmethod
    def update_card_play(cls, card):
        key = card.value if card.type == "wild" else str(card)
        cls.card_play_counts[key] += 1
        
        if card.value in ["Draw2", "Draw4", "Draw6", "Draw10", "ReverseDraw4", "ColorRoulette"]:
            cls.special_card_counts[card.value] += 1
        
        if card.type != "number":
            cls.total_non_numbered_cards += 1
            if card.type == "action":
                cls.action_card_count += 1
            elif card.type == "wild":
                cls.wild_card_count += 1
    
    @classmethod
    def increment_draw_count(cls, num):
        cls.total_draws += num
    
    @classmethod
    def record_game_turn_count(cls, turns):
        cls.turn_counts[turns] += 1
    
    @classmethod
    def write_stats_to_disk(cls, batch_number):
        stats = {
            "total_games": cls.total_games,
            "total_turns": cls.total_turns,
            "avg_turns": cls.total_turns / cls.total_games if cls.total_games else 0,
            "card_play_counts": dict(cls.card_play_counts),
            "special_card_counts": cls.special_card_counts,
            "stacking_metrics": {
                "total_stacking_events": cls.total_stacking_events,
                "total_stacked_penalty": cls.total_stacked_penalty,
                "total_pending_draw_resolved": cls.total_pending_draw_resolved
            },
            "draw_metrics": {
                "total_draws": cls.total_draws,
                "draw_events": cls.draw_events,
                "max_cards_drawn_in_turn": cls.max_cards_drawn_in_turn,
                "avg_draws_per_turn": cls.total_cards_drawn_in_turns / cls.total_turns if cls.total_turns else 0
            },
            "hand_switching_metrics": {
                "total_switches_on_7": cls.total_switches_on_7,
                "total_cycles_on_0": cls.total_cycles_on_0
            },
            "mercy_metrics": {
                "total_mercy_eliminations": cls.total_mercy_eliminations,
                "avg_mercy_losses": cls.total_mercy_eliminations / cls.total_games if cls.total_games else 0
            },
            "additional_metrics": {
                "total_non_numbered_cards": cls.total_non_numbered_cards,
                "action_card_count": cls.action_card_count,
                "wild_card_count": cls.wild_card_count,
                "non_numbered_ratio": ((cls.total_non_numbered_cards / sum(cls.card_play_counts.values())) * 100 if cls.card_play_counts else 0),
                "max_hand_size_ever": cls.max_hand_size_ever,
                "one_round_game_count": cls.one_round_game_count
            },
            "turn_counts": dict(cls.turn_counts)
        }
        
        stats_file = DATA_DIR / f"uno_stats_batch_{batch_number}.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
        
        if cls.one_round_game_examples:
            examples_file = DATA_DIR / f"one_round_examples_batch_{batch_number}.json"
            with open(examples_file, "w") as f:
                json.dump(cls.one_round_game_examples, f, indent=2)
        
        print(f"Stats written to disk for batch {batch_number}")
    
    @classmethod
    def reset_for_new_batch(cls):
        cls.one_round_game_examples = []
    
    @classmethod
    def print_simulation_summary(cls):
        print("\n======= Simulation Summary =======")
        print(f"Total games simulated: {cls.total_games}")
        print(f"Total turns played: {cls.total_turns}")
        avg_turns = cls.total_turns / cls.total_games if cls.total_games else 0
        print(f"Average game duration (turns): {avg_turns:.2f}")
        
        game_turn_durations = list(cls.turn_counts.keys())
        longest_game = max(game_turn_durations) if game_turn_durations else 0
        shortest_game = min(game_turn_durations) if game_turn_durations else 0
        print(f"Longest game (turns): {longest_game}")
        print(f"Shortest game (turns): {shortest_game}")
        
        print(f"One-round games: {cls.one_round_game_count} ({(cls.one_round_game_count / cls.total_games * 100 if cls.total_games else 0):.2f}%)")
        print(f"Total mercy eliminations: {cls.total_mercy_eliminations}")
        print("Check output files for detailed statistics.")
        print("==================================\n")
    
    @classmethod
    def print_simulation_metrics(cls):
        print("\n======= Simulation Metrics =======")
        print(f"Total games simulated: {cls.total_games}")
        print(f"Total turns played: {cls.total_turns}")
        avg_turns = cls.total_turns / cls.total_games if cls.total_games else 0
        print(f"Average game duration (turns): {avg_turns:.2f}")
        
        game_turn_durations = list(cls.turn_counts.keys())
        longest_game = max(game_turn_durations) if game_turn_durations else 0
        shortest_game = min(game_turn_durations) if game_turn_durations else 0
        print(f"Longest game (turns): {longest_game}")
        print(f"Shortest game (turns): {shortest_game}")

        # Top 15 most played cards
        card_entries = sorted(cls.card_play_counts.items(), key=lambda x: x[1], reverse=True)
        print("\nTop 15 most played cards:")
        for card, count in card_entries[:15]:
            print(f"  {card}: {count} times")
        
        if card_entries:
            least_played = min(card_entries, key=lambda x: x[1])
            print(f"\nLeast played card: {least_played[0]} played {least_played[1]} times")

        print("\nFrequency of special draw cards played:")
        for special in ["Draw2", "Draw4", "Draw6", "Draw10", "ReverseDraw4", "ColorRoulette"]:
            print(f"  {special}: {cls.special_card_counts.get(special, 0)} times")

        print("\nStackable Draw Metrics:")
        print(f"Total stacking events: {cls.total_stacking_events}")
        print(f"Total penalty added via stacking: {cls.total_stacked_penalty}")
        print(f"Total pending draw penalty resolved: {cls.total_pending_draw_resolved}")

        print("\nDraw Metrics:")
        print(f"Total cards drawn: {cls.total_draws}")
        print(f"Total draw events: {cls.draw_events}")
        print(f"Most cards drawn in a single turn: {cls.max_cards_drawn_in_turn}")
        avg_draws_per_turn = cls.total_cards_drawn_in_turns / cls.total_turns if cls.total_turns else 0
        print(f"Average cards drawn per turn: {avg_draws_per_turn:.2f}")

        print("\nHand Switching Metrics:")
        print(f"Total switches on card 7: {cls.total_switches_on_7}")
        print(f"Total cycles on card 0: {cls.total_cycles_on_0}")

        print("\nMercy Metrics:")
        print(f"Total mercy eliminations: {cls.total_mercy_eliminations}")
        avg_mercy_losses = cls.total_mercy_eliminations / cls.total_games if cls.total_games else 0
        print(f"Average mercy losses per game: {avg_mercy_losses:.2f}")

        print("\nAdditional Metrics:")
        print(f"Total non-numbered cards played: {cls.total_non_numbered_cards}")
        print(f"  (Action cards: {cls.action_card_count}, Wild cards: {cls.wild_card_count})")
        total_card_plays = sum(cls.card_play_counts.values())
        non_numbered_ratio = (cls.total_non_numbered_cards / total_card_plays * 100) if total_card_plays else 0
        print(f"Non-numbered cards constitute {non_numbered_ratio:.2f}% of all plays.")
        print(f"Maximum hand size observed: {cls.max_hand_size_ever}")
        print(f"Games lasting only 1 round: {cls.one_round_game_count}")
        
        if cls.one_round_game_count > 0 and cls.one_round_game_examples:
            print("Example of a 1-round game (detailed log):")
            example = cls.one_round_game_examples[0]
            print(f"  Game #{example['game_number']}: Winner: Player {example['winner_id']}")
            print(f"  Winning player's hand (pre-winning turn): {example['winning_player_hand']}")
            print("  Move Log:")
            for msg in example.get('game_log', [])[:10]:  # Show first 10 log entries
                print(f"    {msg}")
        print("==================================\n")

# =================== Simulation Runner ===================
def run_simulations_in_batches(total_simulations, batch_size):
    print(f"Starting {total_simulations} simulations in batches of {batch_size}...")
    
    completed_simulations = 0
    batch_number = 1
    
    while completed_simulations < total_simulations:
        current_batch_size = min(batch_size, total_simulations - completed_simulations)
        print(f"Running batch {batch_number}: {current_batch_size} simulations")
        
        for i in range(current_batch_size):
            should_track_detail = len(SimulationStats.one_round_game_examples) < SimulationStats.max_examples_to_store
            
            game = UnoGame(
                n=6, 
                m=7, 
                k=100000, 
                mercy_rule=True, 
                verbose=False,
                metrics_collector=SimulationStats.update_card_play,
                track_one_round_detail=should_track_detail
            )
            
            game.start_game()
            
            SimulationStats.total_games += 1
            SimulationStats.total_turns += game.turn_count
            SimulationStats.record_game_turn_count(game.turn_count)
            
            if game.turn_count == 1:
                SimulationStats.one_round_game_count += 1
                if should_track_detail:
                    SimulationStats.one_round_game_examples.append({
                        "game_number": completed_simulations + i + 1,
                        "winner_id": game.winner_id,
                        "winning_player_hand": game.winner_hand_snapshot,
                        "game_log": game.game_log.copy() if game.game_log else []
                    })
            
            if (i + 1) % (batch_size // 10) == 0 or i == current_batch_size - 1:
                print(f"Completed {i + 1}/{current_batch_size} simulations in batch {batch_number}")
        
        SimulationStats.write_stats_to_disk(batch_number)
        SimulationStats.reset_for_new_batch()
        
        completed_simulations += current_batch_size
        batch_number += 1
        
        gc.collect()
    
    # Write final summary and metrics
    SimulationStats.print_simulation_summary()
    SimulationStats.print_simulation_metrics()

# Run simulations with the desired batch size
BATCH_SIZE = 10000
run_simulations_in_batches(100000, BATCH_SIZE)

# To run a single game with verbose output:
# game = UnoGame(n=4, m=7, k=100000, mercy_rule=False, verbose=True)
# game.start_game()