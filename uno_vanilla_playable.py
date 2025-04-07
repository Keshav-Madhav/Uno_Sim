import random
from collections import defaultdict

class Card:
    def __init__(self, color, value):
        self.color = color  # "Red", "Blue", "Green", "Yellow", or "Wild"
        self.value = value  # number (0-9), "Skip", "Reverse", "Draw2", or "Wild"/"Wild Draw4"

    def __str__(self):
        if self.color == "Wild":
            return f"{self.value}"
        else:
            return f"{self.color} {self.value}"

    def is_wild(self):
        return self.color == "Wild"
    
    def is_special(self):
        return self.value in ["Skip", "Reverse", "Draw2", "Wild", "Wild Draw4"]

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

    def can_play(self, card, top_card):
        if card.is_wild():
            return True
        return (card.color == top_card.color) or (card.value == top_card.value)

    def find_playable_cards(self, top_card):
        return [card for card in self.hand if self.can_play(card, top_card)]

    def play_card(self, card_index):
        if 0 <= card_index < len(self.hand):
            return self.hand.pop(card_index)
        return None

    def has_uno(self):
        return len(self.hand) == 1

    def shout_uno(self):
        print(f"Player {self.id} shouts UNO!")

class UnoGame:
    def __init__(self, num_players, human_ids=None):
        self.players = [Player(i+1, i+1 in (human_ids or [])) for i in range(num_players)]
        self.deck = []
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1  # 1 for clockwise, -1 for counter-clockwise
        self.game_over = False
        self.winner = None
        self.pending_draw = 0
        
        self.create_deck()
        self.shuffle_deck()
        self.deal_initial_cards(7)  # Standard UNO deals 7 cards to each player
        
        # Start with a non-special card
        while True:
            start_card = self.deck.pop()
            if not start_card.is_special():
                self.discard_pile.append(start_card)
                break
            self.deck.insert(0, start_card)  # Put it back at the bottom
        
        print(f"Game started with {num_players} players")
        print(f"Starting card: {start_card}")

    def create_deck(self):
        colors = ["Red", "Blue", "Green", "Yellow"]
        numbers = list(range(10)) + list(range(1, 10))  # One 0, two 1-9 of each color
        specials = ["Skip", "Reverse", "Draw2"] * 2  # Two of each special per color
        
        for color in colors:
            for num in numbers:
                self.deck.append(Card(color, num))
            for spec in specials:
                self.deck.append(Card(color, spec))
        
        # Add wild cards (4 of each)
        for _ in range(4):
            self.deck.append(Card("Wild", "Wild"))
            self.deck.append(Card("Wild", "Wild Draw4"))

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def deal_initial_cards(self, count):
        for player in self.players:
            player.draw(self.deck, count)

    def get_top_card(self):
        return self.discard_pile[-1] if self.discard_pile else None

    def replenish_deck(self):
        if len(self.deck) < 4:
            print("Reshuffling discard pile into deck...")
            top_card = self.discard_pile.pop()  # Keep the top card
            self.deck = self.discard_pile
            self.discard_pile = [top_card]
            self.shuffle_deck()

    def play_turn(self):
        self.replenish_deck()
        player = self.players[self.current_player_index]
        top_card = self.get_top_card()
        
        print(f"\nPlayer {player.id}'s turn {'(YOU)' if player.is_human else ''}")
        print(f"Top card: {top_card}")
        
        # Handle pending draws first
        if self.pending_draw > 0:
            self.handle_pending_draw(player)
            return
        
        playable_cards = player.find_playable_cards(top_card)
        
        if player.is_human:
            played_card = self.handle_human_turn(player, playable_cards, top_card)
        else:
            played_card = self.handle_ai_turn(player, playable_cards, top_card)
        
        if played_card:
            self.discard_pile.append(played_card)
            self.handle_card_effect(played_card)
            
            # Check for UNO
            if player.has_uno():
                player.shout_uno()
            
            # Check for win
            if len(player.hand) == 0:
                self.game_over = True
                self.winner = player
                return
        
        self.next_player()

    def handle_pending_draw(self, player):
        print(f"Player {player.id} must draw {self.pending_draw} cards")
        player.draw(self.deck, self.pending_draw)
        self.pending_draw = 0
        self.next_player()

    def handle_human_turn(self, player, playable_cards, top_card):
        print("\nYour hand:")
        for i, card in enumerate(player.hand):
            marker = "*" if card in playable_cards else " "
            print(f"{i+1}. {marker} {card}")
        
        if playable_cards:
            while True:
                choice = input("Choose card to play (1-...) or 'd' to draw: ")
                if choice.lower() == 'd':
                    return self.handle_human_draw(player, top_card)
                try:
                    card_index = int(choice) - 1
                    if 0 <= card_index < len(player.hand):
                        card = player.hand[card_index]
                        if card in playable_cards:
                            return player.play_card(card_index)
                        print("You can't play that card!")
                except ValueError:
                    print("Invalid input")
        else:
            return self.handle_human_draw(player, top_card)

    def handle_human_draw(self, player, top_card):
        print("No playable cards - drawing")
        drawn_card = player.draw(self.deck, 1)[0]
        print(f"You drew: {drawn_card}")
        
        if player.can_play(drawn_card, top_card):
            choice = input("Play this card? (y/n): ").lower()
            if choice == 'y':
                # Find the index of the drawn card (it's the last one)
                return player.play_card(len(player.hand) - 1)
        return None

    def handle_ai_turn(self, player, playable_cards, top_card):
        if playable_cards:
            # Simple AI strategy: play first playable card, preferring non-wild cards
            non_wild = [c for c in playable_cards if not c.is_wild()]
            if non_wild:
                card_to_play = non_wild[0]
            else:
                card_to_play = playable_cards[0]
            
            card_index = player.hand.index(card_to_play)
            print(f"Player {player.id} plays {player.hand[card_index]}")
            return player.play_card(card_index)
        else:
            print(f"Player {player.id} has no playable cards - drawing")
            drawn_card = player.draw(self.deck, 1)[0]
            print(f"Player {player.id} drew a card")
            
            if player.can_play(drawn_card, top_card):
                print(f"Player {player.id} plays the drawn card")
                return player.play_card(len(player.hand) - 1)
            return None

    def handle_card_effect(self, card):
        if card.value == "Skip":
            self.next_player()
            print(f"Player {self.players[self.current_player_index].id} was skipped!")
            self.next_player()
        elif card.value == "Reverse":
            self.direction *= -1
            print(f"Direction reversed! Now going {'clockwise' if self.direction > 0 else 'counter-clockwise'}")
            # In 2-player game, reverse acts like skip
            if len(self.players) == 2:
                self.next_player()
        elif card.value == "Draw2":
            self.pending_draw = 2
            print("Next player must draw 2 cards!")
        elif card.value == "Wild Draw4":
            self.pending_draw = 4
            print("Next player must draw 4 cards!")
            # Choose color for wild card
            if card.is_wild():
                self.choose_color(card)
        elif card.is_wild():
            self.choose_color(card)

    def choose_color(self, wild_card):
        if wild_card.color != "Wild":
            return  # Already has a color
        
        current_player = self.players[self.current_player_index]
        
        if current_player.is_human:
            print("Choose a color:")
            print("1. Red\n2. Blue\n3. Green\n4. Yellow")
            while True:
                choice = input("Enter choice (1-4): ")
                if choice in ["1", "2", "3", "4"]:
                    colors = ["Red", "Blue", "Green", "Yellow"]
                    wild_card.color = colors[int(choice)-1]
                    print(f"Color set to {wild_card.color}")
                    break
                print("Invalid choice")
        else:
            # AI chooses the color they have most of
            color_counts = defaultdict(int)
            for card in current_player.hand:
                if card.color != "Wild":
                    color_counts[card.color] += 1
            
            if color_counts:
                chosen_color = max(color_counts.items(), key=lambda x: x[1])[0]
            else:
                chosen_color = random.choice(["Red", "Blue", "Green", "Yellow"])
            
            wild_card.color = chosen_color
            print(f"Player {current_player.id} chose {chosen_color}")

    def next_player(self):
        self.current_player_index = (self.current_player_index + self.direction) % len(self.players)

    def print_game_state(self):
        print("\nCurrent game state:")
        print(f"Direction: {'Clockwise' if self.direction > 0 else 'Counter-clockwise'}")
        print(f"Top card: {self.get_top_card()}")
        print(f"Current player: {self.players[self.current_player_index].id}")
        print("Player hands:")
        for player in self.players:
            print(f"Player {player.id}: {len(player.hand)} cards")
            if player.is_human:
                print("Your hand:", ", ".join(str(card) for card in player.hand))

    def start_game(self):
        while not self.game_over:
            self.print_game_state()
            self.play_turn()
        
        print("\nGame Over!")
        if self.winner:
            print(f"Player {self.winner.id} wins!")
        else:
            print("Game ended unexpectedly")

def main():
    print("=== UNO Game ===")
    num_players = int(input("Number of players (2-10): "))
    human_ids = []
    human_input = input("Human player IDs (comma separated, leave empty for all AI): ")
    if human_input:
        human_ids = [int(x.strip()) for x in human_input.split(",") if x.strip().isdigit()]
    
    game = UnoGame(num_players, human_ids or None)
    game.start_game()

if __name__ == "__main__":
    main()