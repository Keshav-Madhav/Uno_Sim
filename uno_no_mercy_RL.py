import random
from collections import defaultdict
import numpy as np

class Card:
    def __init__(self, type, color=None, value=None):
        self.type = type  # "number", "action", or "wild"
        self.color = color  # "Red", "Blue", "Green", "Yellow" or None
        self.value = value  # varies by card type

    def __str__(self):
        if self.type == "wild":
            return f"{self.value}{f' ({self.color})' if self.color else ''}"
        else:
            return f"{self.color} {self.value}"

    def to_vector(self):
        """Convert card to numerical vector representation"""
        # Card type: [number, action, wild]
        type_vec = [0, 0, 0]
        if self.type == "number":
            type_vec[0] = 1
        elif self.type == "action":
            type_vec[1] = 1
        else:
            type_vec[2] = 1
        
        # Color: [Red, Blue, Green, Yellow, None]
        color_vec = [0, 0, 0, 0, 0]
        if self.color == "Red":
            color_vec[0] = 1
        elif self.color == "Blue":
            color_vec[1] = 1
        elif self.color == "Green":
            color_vec[2] = 1
        elif self.color == "Yellow":
            color_vec[3] = 1
        else:
            color_vec[4] = 1
        
        # Value: one-hot encoded for common values
        value_vec = [0] * 20  # Adjust size based on possible values
        if self.type == "number":
            value_vec[int(self.value)] = 1
        else:
            # Map action/wild values to positions 10-19
            action_values = {
                "Skip": 10, "SkipAll": 11, "Reverse": 12, "Draw2": 13,
                "Draw4": 14, "DiscardColor": 15, "ReverseDraw4": 16,
                "Draw6": 17, "Draw10": 18, "ColorRoulette": 19
            }
            if self.value in action_values:
                value_vec[action_values[self.value]] = 1
        
        return type_vec + color_vec + value_vec

class Player:
    def __init__(self, player_id, is_human=False, is_rl=False):
        self.id = player_id
        self.hand = []
        self.is_human = is_human
        self.is_rl = is_rl

    def draw(self, deck, count=1):
        drawn = []
        for _ in range(count):
            if deck:
                card = deck.pop()
                self.hand.append(card)
                drawn.append(card)
        return drawn

    def find_best_card(self, top_card):
        if not top_card:
            return self.hand[0] if self.hand else None
        
        active_color = top_card.color or None
        playable = []
        for card in self.hand:
            if card.type == "wild":
                playable.append(card)
                continue
            if active_color:
                if card.color == active_color or card.value == top_card.value:
                    playable.append(card)
            else:
                if card.color == top_card.color or card.value == top_card.value:
                    playable.append(card)
        
        if not playable:
            return None
        
        non_wild = [c for c in playable if c.type != "wild"]
        best_score = -float('inf')
        best_card = None
        
        for card in playable:
            score = 0
            if card.type == "wild":
                score = 0.5 if non_wild else 1
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
                        score += 1 if len(non_wild) > 1 else 3
                if card.type == "number":
                    if card.value in (0, 7):
                        score += 5 if len(self.hand) > 5 else 2
            if score > best_score:
                best_score = score
                best_card = card
        return best_card

    def has_playable_card(self, top_card):
        active_color = top_card.color or None
        for card in self.hand:
            if card.type == "wild":
                return True
            if active_color:
                if card.color == active_color or card.value == top_card.value:
                    return True
            else:
                if card.color == top_card.color or card.value == top_card.value:
                    return True
        return False

    def has_card_with_value(self, value):
        return any(card.value == value for card in self.hand)

    def play_card(self, card):
        for i, c in enumerate(self.hand):
            if c.type == card.type and c.color == card.color and c.value == card.value:
                return self.hand.pop(i)
        return None

    def is_valid_choice(self, card, top_card):
        if card.type == "wild":
            return True
        if top_card.type == "wild" and not top_card.color:
            return True
        active_color = top_card.color or None
        return (card.color == active_color) if active_color else (card.color == top_card.color or card.value == top_card.value)

class RLAgent:
    def __init__(self, player_id):
        self.id = player_id
        self.hand = []
        self.is_rl = True
    
    def get_action(self, game_state):
        """
        This method should be implemented by the RL model
        Returns:
            - card_index: index of card to play in hand (-1 for draw)
            - color_choice: if playing wild card (0-3 for R/B/G/Y)
        """
        # Placeholder - replace with actual RL model inference
        playable_indices = []
        for i, card in enumerate(self.hand):
            if game_state['is_valid_play'](card):
                playable_indices.append(i)
        
        if playable_indices:
            card_idx = random.choice(playable_indices)
            color = random.randint(0, 3) if self.hand[card_idx].type == "wild" else None
            return card_idx, color
        else:
            return -1, None  # Draw card
    
    def update_model(self, reward, new_state, done):
        """
        Update RL model based on game outcome
        """
        # To be implemented by RL training framework
        pass

class UnoGame:
    def __init__(self, num_players=4, initial_cards=7, rl_player_id=1, mercy_rule=True):
        self.players = []
        for i in range(num_players):
            if i+1 == rl_player_id:
                self.players.append(RLAgent(i+1))
            else:
                self.players.append(Player(i+1))
        
        self.deck = []
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1
        self.turn_count = 0
        self.game_over = False
        self.pending_draw = 0
        self.pending_draw_type = None
        self.winner_id = None
        self.mercy_rule = mercy_rule
        
        self.create_deck()
        self.shuffle_deck()
        self.deal_initial_cards(initial_cards)
        
        start_card = self.deck.pop()
        self.discard_pile.append(start_card)

    def create_deck(self):
        colors = ["Red", "Blue", "Green", "Yellow"]
        for color in colors:
            for num in range(10):
                self.deck.append(Card("number", color, num))
                self.deck.append(Card("number", color, num))
            for _ in range(3):
                self.deck.append(Card("action", color, "Skip"))
            for _ in range(2):
                self.deck.append(Card("action", color, "SkipAll"))
            for _ in range(3):
                self.deck.append(Card("action", color, "Reverse"))
            for _ in range(3):
                self.deck.append(Card("action", color, "Draw2"))
            for _ in range(2):
                self.deck.append(Card("action", color, "Draw4"))
            for _ in range(3):
                self.deck.append(Card("action", color, "DiscardColor"))
        for _ in range(8):
            self.deck.append(Card("wild", None, "ReverseDraw4"))
        for _ in range(4):
            self.deck.append(Card("wild", None, "Draw6"))
        for _ in range(4):
            self.deck.append(Card("wild", None, "Draw10"))
        for _ in range(8):
            self.deck.append(Card("wild", None, "ColorRoulette"))

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def deal_initial_cards(self, m):
        for player in self.players:
            player.draw(self.deck, m)

    def get_top_card(self):
        return self.discard_pile[-1] if self.discard_pile else None

    def check_recycle_deck(self):
        if len(self.deck) < 5:
            top = self.discard_pile.pop() if self.discard_pile else None
            self.deck = self.discard_pile
            self.discard_pile = [top] if top else []
            self.shuffle_deck()

    def get_game_state(self, player_id):
        """
        Return the game state from the perspective of the specified player
        """
        player = next(p for p in self.players if p.id == player_id)
        top_card = self.get_top_card()
        
        state = {
            'current_player': player_id,
            'top_card': top_card.to_vector() if top_card else [0]*28,  # 28 is length of card vector
            'hand': [card.to_vector() for card in player.hand],
            'hand_sizes': [len(p.hand) for p in self.players],
            'direction': self.direction,
            'pending_draw': self.pending_draw,
            'pending_draw_type': self.pending_draw_type,
            'num_players': len(self.players),
            'turn_count': self.turn_count,
            'is_valid_play': lambda card: player.is_valid_choice(card, top_card) if top_card else True
        }
        return state

    def play_turn(self):
        self.check_recycle_deck()
        player = self.players[self.current_player_index]
        top_card = self.get_top_card()
        
        if self.pending_draw > 0:
            return self.handle_pending_draw(player, top_card)
        
        played_card = None
        if player.is_rl:
            played_card = self.handle_rl_turn(player, top_card)
        else:
            played_card = self.handle_ai_turn(player, top_card)
        
        if played_card:
            self.handle_card_effects(played_card)
            if played_card.type == "number":
                if played_card.value == 0:
                    self.switch_hands_cycle()
                elif played_card.value == 7:
                    self.switch_hands_choice(player)
        
        if self.check_winner(player):
            return True
        
        self.advance_turn()
        return False

    def handle_rl_turn(self, player, top_card):
        game_state = self.get_game_state(player.id)
        card_idx, color_choice = player.get_action(game_state)
        
        if card_idx == -1:  # Draw card
            drawn = player.draw(self.deck, 1)
            if drawn and player.is_valid_choice(drawn[0], top_card):
                # RL agent can choose to play drawn card
                game_state = self.get_game_state(player.id)
                card_idx, color_choice = player.get_action(game_state)
                if card_idx == len(player.hand) - 1:  # Play the drawn card
                    played = player.play_card(drawn[0])
                    self.discard_pile.append(played)
                    if played.type == "wild":
                        colors = ["Red", "Blue", "Green", "Yellow"]
                        played.color = colors[color_choice % 4]
                    return played
            return None
        else:
            if 0 <= card_idx < len(player.hand):
                card = player.hand[card_idx]
                if player.is_valid_choice(card, top_card):
                    played = player.play_card(card)
                    self.discard_pile.append(played)
                    if played.type == "wild":
                        colors = ["Red", "Blue", "Green", "Yellow"]
                        played.color = colors[color_choice % 4]
                    return played
        return None

    def handle_pending_draw(self, player, top_card):
        allowed_stacking = {
            "Draw2": ["Draw2", "Draw4", "Draw6", "Draw10"],
            "Draw4": ["Draw4", "Draw6", "Draw10"],
            "Draw6": ["Draw6", "Draw10"],
            "Draw10": ["Draw10"]
        }
        allowed = allowed_stacking.get(self.pending_draw_type, [])
        stackable = [c for c in player.hand if (
            (c.type == "action" and c.value in ["Draw2", "Draw4"]) or
            (c.type == "wild" and c.value in ["Draw6", "Draw10"])
        ) and c.value in allowed]
        
        if stackable:
            if player.is_rl:
                # RL agent chooses whether to stack
                game_state = self.get_game_state(player.id)
                card_idx, color_choice = player.get_action(game_state)
                if 0 <= card_idx < len(player.hand):
                    card = player.hand[card_idx]
                    if card in stackable:
                        played = player.play_card(card)
                        self.discard_pile.append(played)
                        if played.type == "wild":
                            colors = ["Red", "Blue", "Green", "Yellow"]
                            played.color = colors[color_choice % 4]
                        self.update_pending_draw(played.value)
            else:
                # AI always stacks if possible
                played = stackable[0]
                player.play_card(played)
                self.discard_pile.append(played)
                if played.type == "wild":
                    color = self.choose_color_ai(player)
                    played.color = color
                self.update_pending_draw(played.value)
            self.advance_turn()
        else:
            player.draw(self.deck, self.pending_draw)
            self.pending_draw = 0
            self.pending_draw_type = None
            self.advance_turn()
        return False

    def update_pending_draw(self, value):
        penalties = {"Draw2":2, "Draw4":4, "Draw6":6, "Draw10":10}
        self.pending_draw += penalties.get(value, 0)
        self.pending_draw_type = value

    def handle_ai_turn(self, player, top_card):
        best = player.find_best_card(top_card)
        if best:
            played = player.play_card(best)
            self.discard_pile.append(played)
            if played.type == "wild":
                color = self.choose_color_ai(player)
                played.color = color
            return played
        else:
            drawn = player.draw(self.deck, 1)
            if drawn and player.is_valid_choice(drawn[0], top_card):
                played = player.play_card(drawn[0])
                self.discard_pile.append(played)
                if played.type == "wild":
                    color = self.choose_color_ai(player)
                    played.color = color
                return played
        return None

    def choose_color_ai(self, player):
        counts = defaultdict(int)
        for c in player.hand:
            if c.color: counts[c.color] += 1
        return max(counts, key=counts.get, default="Red")

    def check_winner(self, player):
        if len(player.hand) == 0:
            self.winner_id = player.id
            self.game_over = True
            return True
        elif self.mercy_rule and len(player.hand) > 25:
            self.players = [p for p in self.players if p.id != player.id]
            self.current_player_index %= len(self.players)
            if len(self.players) == 1:
                self.winner_id = self.players[0].id
                self.game_over = True
                return True
        return False

    def advance_turn(self):
        self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
        self.turn_count += 1

    def handle_card_effects(self, card):
        penalties = {"Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10}
        if card.type == "action":
            if card.value == "Skip":
                self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
            elif card.value == "SkipAll":
                self.current_player_index = (self.current_player_index - self.direction) % len(self.players)
            elif card.value == "Reverse":
                self.direction *= -1
            elif card.value == "Draw2":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw2"]
                    self.pending_draw_type = "Draw2"
            elif card.value == "Draw4":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw4"]
                    self.pending_draw_type = "Draw4"
            elif card.value == "DiscardColor":
                player = self.players[self.current_player_index]
                discard_color = card.color
                discard = [c for c in player.hand if c.color == discard_color]
                player.hand = [c for c in player.hand if c.color != discard_color]
                self.discard_pile.extend(discard)
        elif card.type == "wild":
            if card.value == "ReverseDraw4":
                target_idx = (self.current_player_index - self.direction) % len(self.players)
                target = self.players[target_idx]
                target.draw(self.deck, 4)
                self.direction *= -1
            elif card.value == "Draw6":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw6"]
                    self.pending_draw_type = "Draw6"
            elif card.value == "Draw10":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw10"]
                    self.pending_draw_type = "Draw10"
            elif card.value == "ColorRoulette":
                next_idx = (self.current_player_index + self.direction) % len(self.players)
                next_player = self.players[next_idx]
                color = card.color
                drawn = 0
                while self.deck:
                    card = self.deck.pop()
                    next_player.hand.append(card)
                    drawn += 1
                    if card.color == color:
                        break

    def switch_hands_cycle(self):
        if len(self.players) < 2:
            return
        hands = [p.hand for p in self.players]
        for i in range(len(self.players)):
            self.players[i].hand = hands[(i - self.direction) % len(self.players)]

    def switch_hands_choice(self, current_player):
        others = [p for p in self.players if p != current_player]
        if not others:
            return
        
        if current_player.is_rl:
            # RL agent chooses who to swap with
            game_state = self.get_game_state(current_player.id)
            # For simplicity, we'll just swap with player with fewest cards
            target = min(others, key=lambda p: len(p.hand))
            if len(target.hand) < len(current_player.hand):
                current_player.hand, target.hand = target.hand, current_player.hand
        else:
            # AI logic for choosing who to swap with
            target = min(others, key=lambda p: len(p.hand))
            if len(target.hand) < len(current_player.hand):
                current_player.hand, target.hand = target.hand, current_player.hand

    def train_rl_agent(self, episodes=1000):
        """Train the RL agent by playing multiple games"""
        for episode in range(episodes):
            self.reset_game()
            done = False
            while not done:
                player = self.players[self.current_player_index]
                if player.is_rl:
                    # Get current state
                    state = self.get_game_state(player.id)
                    
                    # RL agent makes move
                    card_idx, color_choice = player.get_action(state)
                    
                    # Execute move and get next state
                    played_card = self.handle_rl_turn(player, self.get_top_card())
                    
                    # Get reward
                    reward = 0
                    if self.check_winner(player):
                        reward = 100  # Big reward for winning
                        done = True
                    elif played_card:
                        # Small positive reward for playing a card
                        reward = 1
                        # Additional reward for reducing hand size
                        reward += (1 / len(player.hand)) if player.hand else 0
                    else:
                        # Small penalty for drawing
                        reward = -0.5
                    
                    # Get new state
                    new_state = self.get_game_state(player.id)
                    
                    # Update RL model
                    player.update_model(reward, new_state, done)
                else:
                    # Other players take their turns
                    done = self.play_turn()
            
            # Print progress
            if (episode + 1) % 100 == 0:
                print(f"Episode {episode + 1}, Winner: Player {self.winner_id}")

    def reset_game(self):
        """Reset the game for a new episode"""
        self.deck = []
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1
        self.turn_count = 0
        self.game_over = False
        self.pending_draw = 0
        self.pending_draw_type = None
        self.winner_id = None
        
        self.create_deck()
        self.shuffle_deck()
        
        # Reset player hands
        for player in self.players:
            player.hand = []
            player.draw(self.deck, 7)
        
        start_card = self.deck.pop()
        self.discard_pile.append(start_card)

def main():
    # Create game with 4 players (1 RL agent)
    game = UnoGame(num_players=4, rl_player_id=1)
    
    # Train the RL agent
    game.train_rl_agent(episodes=1000)

if __name__ == "__main__":
    main()