import random
from collections import defaultdict

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

class Player:
    def __init__(self, player_id, is_human=False):
        self.id = player_id
        self.hand = []
        self.is_human = is_human

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

class UnoGame:
    def __init__(self, num_players, initial_cards, human_ids=None, mercy_rule=True):
        self.players = [Player(i+1, i+1 in (human_ids or [])) for i in range(num_players)]
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
        print(f"Game started with {num_players} players, {initial_cards} cards each")
        print(f"Starting card: {start_card}")

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
            print("Shuffling discard pile back into deck")
            top = self.discard_pile.pop() if self.discard_pile else None
            self.deck = self.discard_pile
            self.discard_pile = [top] if top else []
            self.shuffle_deck()

    def print_game_state(self):
        print("\nGAME STATE")
        print(f"Turn: {self.turn_count}")
        print(f"Direction: {'→' if self.direction > 0 else '←'}")
        print(f"Top card: {self.get_top_card()}")
        print(f"Deck size: {len(self.deck)}")
        print("Players:")
        for i, p in enumerate(self.players):
            marker = "►" if i == self.current_player_index else " "
            human = " (YOU)" if p.is_human else ""
            print(f"{marker} Player {p.id}{human}: {len(p.hand)} cards")

    def play_turn(self):
        self.check_recycle_deck()
        player = self.players[self.current_player_index]
        top_card = self.get_top_card()
        
        print(f"\n[TURN {self.turn_count+1}] Player {player.id}'s turn {'(YOU)' if player.is_human else ''}")
        print(f"Top card: {top_card}")
        
        if self.pending_draw > 0:
            return self.handle_pending_draw(player, top_card)
        
        played_card = None
        if player.is_human:
            played_card = self.handle_human_turn(player, top_card)
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
            if player.is_human:
                played = self.handle_human_stack_choice(player, stackable)
            else:
                played = stackable[0]
                player.play_card(played)
                self.discard_pile.append(played)
                print(f"Player {player.id} stacks {played}")
                if played.type == "wild":
                    color = self.choose_color_ai(player)
                    played.color = color
                    print(f"Player {player.id} chooses {color}")
                self.update_pending_draw(played.value)
            self.advance_turn()
        else:
            player.draw(self.deck, self.pending_draw)
            print(f"Player {player.id} draws {self.pending_draw} cards")
            self.pending_draw = 0
            self.pending_draw_type = None
            self.advance_turn()
        return False

    def update_pending_draw(self, value):
        penalties = {"Draw2":2, "Draw4":4, "Draw6":6, "Draw10":10}
        self.pending_draw += penalties.get(value, 0)
        self.pending_draw_type = value

    def handle_human_turn(self, player, top_card):
        print("Your hand:")
        for i, card in enumerate(player.hand):
            print(f"{i+1}. {card}")
        
        if player.has_playable_card(top_card):
            choice = self.get_human_choice(player, top_card)
            if choice == 'draw':
                self.draw_and_play(player, top_card)
                return None
            else:
                played = player.play_card(choice)
                self.discard_pile.append(played)
                print(f"You played {played}")
                if played.type == "wild":
                    color = self.get_color_choice()
                    played.color = color
                    print(f"You chose {color}")
                return played
        else:
            return self.handle_no_playable(player, top_card)

    def handle_ai_turn(self, player, top_card):
        best = player.find_best_card(top_card)
        if best:
            played = player.play_card(best)
            self.discard_pile.append(played)
            print(f"Player {player.id} plays {played}")
            if played.type == "wild":
                color = self.choose_color_ai(player)
                played.color = color
                print(f"Player {player.id} chooses {color}")
            return played
        else:
            drawn = player.draw(self.deck, 1)
            if drawn:
                print(f"Player {player.id} draws a card")
                if player.is_valid_choice(drawn[0], top_card):
                    played = player.play_card(drawn[0])
                    self.discard_pile.append(played)
                    print(f"Player {player.id} plays drawn card {played}")
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
            print(f"Player {player.id} wins!")
            self.winner_id = player.id
            self.game_over = True
            return True
        elif self.mercy_rule and len(player.hand) > 25:
            print(f"Player {player.id} eliminated ({len(player.hand)} cards)")
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
                print(f"Player {self.players[self.current_player_index].id} skipped!")
            elif card.value == "SkipAll":
                print("SkipAll played! All others skipped")
                self.current_player_index = (self.current_player_index - self.direction) % len(self.players)
            elif card.value == "Reverse":
                self.direction *= -1
                print(f"Direction reversed! Now {'←' if self.direction < 0 else '→'}")
            elif card.value == "Draw2":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw2"]
                    self.pending_draw_type = "Draw2"
                    print("Draw2 pending")
            elif card.value == "Draw4":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw4"]
                    self.pending_draw_type = "Draw4"
                    print("Draw4 pending")
            elif card.value == "DiscardColor":
                player = self.players[self.current_player_index]
                discard_color = card.color
                discard = [c for c in player.hand if c.color == discard_color]
                player.hand = [c for c in player.hand if c.color != discard_color]
                self.discard_pile.extend(discard)
                print(f"Player {player.id} discarded {len(discard)} {discard_color} cards")
        elif card.type == "wild":
            if card.value == "ReverseDraw4":
                target_idx = (self.current_player_index - self.direction) % len(self.players)
                target = self.players[target_idx]
                target.draw(self.deck, 4)
                self.direction *= -1
                print(f"Player {target.id} drew 4, direction reversed")
            elif card.value == "Draw6":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw6"]
                    self.pending_draw_type = "Draw6"
                    print("Draw6 pending")
            elif card.value == "Draw10":
                if not self.pending_draw:
                    self.pending_draw = penalties["Draw10"]
                    self.pending_draw_type = "Draw10"
                    print("Draw10 pending")
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
                print(f"Player {next_player.id} drew {drawn} cards until {color}")

    def switch_hands_cycle(self):
        if len(self.players) < 2:
            return
        hands = [p.hand for p in self.players]
        for i in range(len(self.players)):
            self.players[i].hand = hands[(i - self.direction) % len(self.players)]
        print("Hands rotated!")

    def switch_hands_choice(self, current_player):
        others = [p for p in self.players if p != current_player]
        if not others:
            return
        
        if current_player.is_human:
            print("Choose player to swap hands with:")
            for i, p in enumerate(others):
                print(f"{i+1}. Player {p.id} ({len(p.hand)} cards)")
            while True:
                try:
                    choice = input("Enter number or 's' to skip: ")
                    if choice.lower() == 's':
                        return
                    idx = int(choice) - 1
                    if 0 <= idx < len(others):
                        target = others[idx]
                        break
                except:
                    print("Invalid choice")
            print(f"Swapped hands with Player {target.id}")
        else:
            target = min(others, key=lambda p: len(p.hand))
            if len(target.hand) >= len(current_player.hand):
                return
        
        current_player.hand, target.hand = target.hand, current_player.hand

    def get_color_choice(self):
        while True:
            choice = input("Choose color (R/B/G/Y): ").upper()
            colors = {'R': 'Red', 'B': 'Blue', 'G': 'Green', 'Y': 'Yellow'}
            if choice in colors:
                return colors[choice]
            print("Invalid color choice")

    def handle_human_stack_choice(self, player, stackable):
        print("Your stackable cards:")
        for i, card in enumerate(stackable):
            print(f"{i+1}. {card}")
        while True:
            choice = input("Choose card to stack or 'd' to draw: ")
            if choice.lower() == 'd':
                player.draw(self.deck, self.pending_draw)
                print(f"Drew {self.pending_draw} cards")
                self.pending_draw = 0
                return None
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(stackable):
                    card = stackable[idx]
                    played = player.play_card(card)
                    self.discard_pile.append(played)
                    if played.type == "wild":
                        color = self.get_color_choice()
                        played.color = color
                    return played
            except:
                print("Invalid choice")

    def get_human_choice(self, player, top_card):
        while True:
            choice = input("Enter card number or 'd' to draw: ")
            if choice.lower() == 'd':
                return 'draw'
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(player.hand):
                    card = player.hand[idx]
                    if player.is_valid_choice(card, top_card):
                        return card
                    print("Can't play that card")
            except:
                print("Invalid input")

    def draw_and_play(self, player, top_card):
        drawn = player.draw(self.deck, 1)
        if drawn:
            print(f"Drew: {drawn[0]}")
            if player.is_valid_choice(drawn[0], top_card):
                choice = input("Play this card? (y/n): ").lower()
                if choice == 'y':
                    played = player.play_card(drawn[0])
                    self.discard_pile.append(played)
                    if played.type == "wild":
                        color = self.get_color_choice()
                        played.color = color
                    self.handle_card_effects(played)
                    return played
        return None

    def handle_no_playable(self, player, top_card):
        print("No playable cards - drawing")
        drawn = player.draw(self.deck, 1)
        if drawn:
            print(f"Drew: {drawn[0]}")
            if player.is_valid_choice(drawn[0], top_card):
                choice = input("Play this card? (y/n): ").lower()
                if choice == 'y':
                    played = player.play_card(drawn[0])
                    self.discard_pile.append(played)
                    if played.type == "wild":
                        color = self.get_color_choice()
                        played.color = color
                    self.handle_card_effects(played)
                    return played
        return None

    def start_game(self):
        while not self.game_over:
            self.print_game_state()
            game_ended = self.play_turn()
            if game_ended:
                break
        print("\nGame Over!")
        if self.winner_id:
            print(f"Winner: Player {self.winner_id}")
        else:
            print("No winner - game ended early")

def main():
    print("=== UNO Game ===")
    num_players = int(input("Number of players (2-8): "))
    initial_cards = int(input("Initial cards per player (5-10): "))
    human_ids = []
    human_input = input("Human player IDs (comma separated or 'all'): ")
    if human_input.lower() == 'all':
        human_ids = list(range(1, num_players+1))
    else:
        human_ids = [int(x) for x in human_input.split(",") if x.strip().isdigit()]
    mercy = input("Enable mercy rule (y/n): ").lower() == 'y'
    
    game = UnoGame(num_players, initial_cards, human_ids, mercy)
    game.start_game()

if __name__ == "__main__":
    main()