const readline = require('readline');

// Create readline interface for console input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// =================== Card Class ===================
class Card {
  constructor(type, color = null, value = null) {
    this.type = type; // "number", "action", or "wild"
    this.color = color; // "Red", "Blue", "Green", "Yellow" or null (for wild cards)
    this.value = value; // For numbers: 0-9; for actions/wilds: string describing the card
  }

  toString() {
    if (this.type === "wild") {
      return `${this.value}${this.color ? ` (${this.color})` : ""}`;
    } else {
      return `${this.color} ${this.value}`;
    }
  }
}

// =================== Player Class ===================
class Player {
  constructor(id, isHuman = false) {
    this.id = id;
    this.hand = [];
    this.isHuman = isHuman;
  }

  draw(deck, count = 1) {
    let drawnCards = [];
    for (let i = 0; i < count; i++) {
      if (deck.length > 0) {
        const card = deck.pop();
        this.hand.push(card);
        drawnCards.push(card);
      }
    }
    return drawnCards;
  }

  findBestCard(topCard) {
    if (!topCard) return this.hand.length > 0 ? this.hand[0] : null;
    
    // Use active color if top card is wild and has one.
    const activeColor = topCard.color || null;
    
    const playableCards = this.hand.filter(card => {
      if (card.type === "wild") return true;
      if (activeColor) return card.color === activeColor || card.value === topCard.value;
      return card.color === topCard.color || card.value === topCard.value;
    });
    if (playableCards.length === 0) return null;
    
    const nonWildPlayable = playableCards.filter(card => card.type !== "wild");
    let bestScore = -Infinity;
    let bestCard = null;
    
    for (const card of playableCards) {
      let score = 0;
      if (card.type === "wild") {
        score = nonWildPlayable.length > 0 ? 0.5 : 1;
        if (card.value === "ColorRoulette") score -= 0.5;
      } else {
        if (activeColor && card.color === activeColor) {
          score += 10;
        }
        if (card.value === topCard.value) {
          score += 5;
        }
        if (card.type === "action") {
          if (card.value === "Skip") score += 3;
          else if (card.value === "Reverse") score += 2;
          else if (card.value === "DiscardColor") score += 2;
          if (card.value === "Draw2" || card.value === "Draw4") {
            score += nonWildPlayable.length > 1 ? 1 : 3;
          }
        }
        if (card.type === "number") {
          if (card.value === 0) score += this.hand.length > 5 ? 5 : 2;
          if (card.value === 7) score += this.hand.length > 5 ? 5 : 2;
        }
      }
      if (score > bestScore) {
        bestScore = score;
        bestCard = card;
      }
    }
    return bestCard;
  }

  hasPlayableCard(topCard) {
    const activeColor = topCard.color || null;
    return this.hand.some(card => {
      if (card.type === "wild") return true;
      if (activeColor) return card.color === activeColor || card.value === topCard.value;
      return card.color === topCard.color || card.value === topCard.value;
    });
  }

  hasCardWithValue(value) {
    return this.hand.some(card => card.value === value);
  }

  playCard(card) {
    if (!card) return null;
    const index = this.hand.findIndex(c =>
      c.type === card.type &&
      c.color === card.color &&
      c.value === card.value
    );
    if (index !== -1) return this.hand.splice(index, 1)[0];
    return null;
  }

  isValidCardChoice(card, topCard) {
    if (card.type === "wild") return true;
  
    if (topCard.type === "wild" && topCard.color === null) {
      return true; // Any color card can be played
    }
  
    const activeColor = topCard.color || null;
    if (activeColor) {
      return card.color === activeColor || card.value === topCard.value;
    }
    return card.color === topCard.color || card.value === topCard.value;
  }
}

// =================== UnoGame Class ===================
class UnoGame {
  constructor(numPlayers, initialCards, humanPlayerIds = [], mercyRule = true) {
    // Convert humanPlayerIds to set for easy lookup
    this.humanPlayerIds = new Set(humanPlayerIds);
    
    // Create players
    this.players = [];
    for (let i = 1; i <= numPlayers; i++) {
      this.players.push(new Player(i, this.humanPlayerIds.has(i)));
    }
    
    this.deck = this.createDeck();
    this.discardPile = [];
    this.currentPlayerIndex = 0;
    this.direction = 1;
    this.turnCount = 0;
    this.gameOver = false;
    this.pendingDraw = 0;
    this.pendingDrawType = null;
    this.winnerId = null;
    this.mercyRule = mercyRule;
    
    this.shuffleDeck();
    this.dealInitialCards(initialCards);
    
    // Start the game with a card from the deck
    const startCard = this.deck.pop();
    this.discardPile.push(startCard);
    console.log(`Game started with ${numPlayers} players, ${initialCards} cards each`);
    console.log(`Starting card: ${startCard.toString()}`);
  }

  createDeck() {
    const colors = ["Red", "Blue", "Green", "Yellow"];
    const deck = [];
    for (let color of colors) {
      for (let number = 0; number <= 9; number++) {
        deck.push(new Card("number", color, number));
        deck.push(new Card("number", color, number));
      }
      for (let i = 0; i < 3; i++) {
        deck.push(new Card("action", color, "Skip"));
      }
      for (let i = 0; i < 2; i++) {
        deck.push(new Card("action", color, "SkipAll"));
      }
      for (let i = 0; i < 3; i++) {
        deck.push(new Card("action", color, "Reverse"));
      }
      for (let i = 0; i < 3; i++) {
        deck.push(new Card("action", color, "Draw2"));
      }
      for (let i = 0; i < 2; i++) {
        deck.push(new Card("action", color, "Draw4"));
      }
      for (let i = 0; i < 3; i++) {
        deck.push(new Card("action", color, "DiscardColor"));
      }
    }
    for (let i = 0; i < 8; i++) {
      deck.push(new Card("wild", null, "ReverseDraw4"));
    }
    for (let i = 0; i < 4; i++) {
      deck.push(new Card("wild", null, "Draw6"));
    }
    for (let i = 0; i < 4; i++) {
      deck.push(new Card("wild", null, "Draw10"));
    }
    for (let i = 0; i < 8; i++) {
      deck.push(new Card("wild", null, "ColorRoulette"));
    }

    return deck;
  }

  shuffleDeck() {
    this.deck.sort(() => Math.random() - 0.5);
  }

  dealInitialCards(m) {
    this.players.forEach(player => player.draw(this.deck, m));
  }

  getTopCard() {
    return this.discardPile.length > 0 ? this.discardPile[this.discardPile.length - 1] : null;
  }

  checkAndRecycleDeck() {
    if (this.deck.length < 5) {
      console.log("Shuffling discard pile back into deck");
      const topCard = this.discardPile.pop();
      this.deck = this.discardPile;
      this.discardPile = topCard ? [topCard] : [];
      this.shuffleDeck();
    }
  }

  async playTurn() {
    this.checkAndRecycleDeck();
    
    const player = this.players[this.currentPlayerIndex];
    const topCard = this.getTopCard();
    
    console.log(`\n[TURN ${this.turnCount + 1}] Player ${player.id}'s turn ${player.isHuman ? "(YOU)" : ""}`);
    console.log(`Top card: ${topCard.toString()}`);
    
    // Handle pending draw stacking
    if (this.pendingDraw > 0) {
      console.log(`There is a pending draw of ${this.pendingDraw} cards (${this.pendingDrawType})`);
      
      const allowedStacking = {
        "Draw2": ["Draw2", "Draw4", "Draw6", "Draw10"],
        "Draw4": ["Draw4", "Draw6", "Draw10"],
        "Draw6": ["Draw6", "Draw10"],
        "Draw10": ["Draw10"]
      };
      
      const allowedResponses = allowedStacking[this.pendingDrawType] || [];
      const stackableCards = player.hand.filter(card => {
        if (
          (card.type === "action" && (card.value === "Draw2" || card.value === "Draw4")) ||
          (card.type === "wild" && (card.value === "Draw6" || card.value === "Draw10"))
        ) {
          return allowedResponses.includes(card.value);
        }
        return false;
      });
      
      let playedCard = null;
      
      if (stackableCards.length > 0) {
        if (player.isHuman) {
          console.log("Your hand:");
          player.hand.forEach((card, index) => {
            const isStackable = stackableCards.some(c => 
              c.type === card.type && c.color === card.color && c.value === card.value
            );
            console.log(`${index + 1}. ${card.toString()}${isStackable ? " (can stack)" : ""}`);
          });
          
          console.log("You can either stack a card or draw cards.");
          const choice = await this.getHumanChoice(player, topCard, true, stackableCards);
          
          if (choice === 'draw') {
            const drawnCards = player.draw(this.deck, this.pendingDraw);
            console.log(`You drew ${drawnCards.length} cards.`);
            console.log(`Cards remaining: ${player.hand.length}`);
            this.pendingDraw = 0;
            this.pendingDrawType = null;
          } else {
            playedCard = player.playCard(choice);
            this.discardPile.push(playedCard);
            console.log(`You played ${playedCard.toString()}`);

            // Add color selection for wild cards
            if (playedCard.type === "wild") {
              const color = await this.getColorChoice();
              playedCard.color = color;
              console.log(`You chose ${color}`);
            }
            
            const penaltyMapping = { "Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10 };
            this.pendingDraw += penaltyMapping[playedCard.value];
            this.pendingDrawType = playedCard.value;
            console.log(`Pending draw increased to ${this.pendingDraw}`);
          }
        } else {
          // AI player logic for stacking
          playedCard = player.playCard(stackableCards[0]);
          this.discardPile.push(playedCard);
          console.log(`Player ${player.id} stacks with ${playedCard.toString()}`);

          // Add automatic color selection for AI
          if (playedCard.type === "wild") {
            const colorCounts = player.hand.reduce((counts, card) => {
              if (card.color) counts[card.color] = (counts[card.color] || 0) + 1;
              return counts;
            }, {});
            let chosenColor = "Red";
            let maxCount = 0;
            for (const [color, count] of Object.entries(colorCounts)) {
              if (count > maxCount) {
                maxCount = count;
                chosenColor = color;
              }
            }
            playedCard.color = chosenColor;
            console.log(`Player ${player.id} chooses ${chosenColor}`);
          }
          
          const penaltyMapping = { "Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10 };
          this.pendingDraw += penaltyMapping[playedCard.value];
          this.pendingDrawType = playedCard.value;
          console.log(`Pending draw increased to ${this.pendingDraw}`);
        }
      } else {
        // No stackable cards, must draw
        const drawnCards = player.draw(this.deck, this.pendingDraw);
        console.log(`Player ${player.id} draws ${drawnCards.length} cards (hand now: ${player.hand.length} cards).`);
        this.pendingDraw = 0;
        this.pendingDrawType = null;
      }
      
      this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
      this.turnCount++;
      return false;
    }
    
    // Regular turn
    let playedCard = null;
    
    if (player.isHuman) {
      // Show the human player's hand
      console.log("Your hand:");
      player.hand.forEach((card, index) => {
        console.log(`${index + 1}. ${card.toString()}`);
      });
      
      const hasPlayable = player.hasPlayableCard(topCard);
      if (hasPlayable) {
        const cardChoice = await this.getHumanChoice(player, topCard);
        if (cardChoice) {
          playedCard = player.playCard(cardChoice);
          this.discardPile.push(playedCard);
          console.log(`You played ${playedCard.toString()}`);
          console.log(`Cards remaining: ${player.hand.length}`);
          
          // For wild cards, choose a color
          if (playedCard.type === "wild") {
            const color = await this.getColorChoice();
            playedCard.color = color;
            console.log(`You chose ${color}`);
          }
        }
      } else {
        console.log("You have no playable cards. Drawing a card...");
        const drawnCards = player.draw(this.deck, 1);
        if (drawnCards.length > 0) {
          console.log(`You drew: ${drawnCards[0].toString()}`);
          const newCard = drawnCards[0];
          
          // Check if the drawn card can be played
          if (player.isValidCardChoice(newCard, topCard)) {
            const wantToPlay = await this.getYesNoChoice("Do you want to play the card you just drew? (y/n)");
            if (wantToPlay) {
              playedCard = player.playCard(newCard);
              this.discardPile.push(playedCard);
              console.log(`You played ${playedCard.toString()}`);
              console.log(`Cards remaining: ${player.hand.length}`);
              
              // For wild cards, choose a color
              if (playedCard.type === "wild") {
                const color = await this.getColorChoice();
                playedCard.color = color;
                console.log(`You chose ${color}`);
              }
            }
          }
        } else {
          console.log("Deck is empty. No card drawn.");
        }
      }
    } else {
      // AI player
      const bestCard = player.findBestCard(topCard);
      if (bestCard) {
        playedCard = player.playCard(bestCard);
        this.discardPile.push(playedCard);
        console.log(`Player ${player.id} played ${playedCard.toString()}`);
        console.log(`Cards remaining: ${player.hand.length}`);
        
        // Choose color for wild cards
        if (playedCard.type === "wild") {
          const colorCounts = player.hand.reduce((counts, card) => {
            if (card.color) counts[card.color] = (counts[card.color] || 0) + 1;
            return counts;
          }, {});
          let chosenColor = "Red";
          let maxCount = 0;
          for (const [color, count] of Object.entries(colorCounts)) {
            if (count > maxCount) {
              maxCount = count;
              chosenColor = color;
            }
          }
          playedCard.color = chosenColor;
          console.log(`Player ${player.id} chooses ${chosenColor}`);
        }
      } else {
        const drawnCards = player.draw(this.deck, 1);
        if (drawnCards.length > 0) {
          console.log(`Player ${player.id} had no valid card and drew 1 card`);
          const newCard = drawnCards[0];
          
          // Check if the drawn card can be played
          if (player.isValidCardChoice(newCard, topCard)) {
            playedCard = player.playCard(newCard);
            this.discardPile.push(playedCard);
            console.log(`Player ${player.id} played the drawn card: ${playedCard.toString()}`);
            
            // Choose color for wild cards
            if (playedCard.type === "wild") {
              const colorCounts = player.hand.reduce((counts, card) => {
                if (card.color) counts[card.color] = (counts[card.color] || 0) + 1;
                return counts;
              }, {});
              let chosenColor = "Red";
              let maxCount = 0;
              for (const [color, count] of Object.entries(colorCounts)) {
                if (count > maxCount) {
                  maxCount = count;
                  chosenColor = color;
                }
              }
              playedCard.color = chosenColor;
              console.log(`Player ${player.id} chooses ${chosenColor}`);
            }
          } else {
            console.log(`Player ${player.id}'s cards remaining: ${player.hand.length}`);
          }
        } else {
          console.log(`Player ${player.id} had no valid card and the deck is empty`);
          console.log(`Cards remaining: ${player.hand.length}`);
        }
      }
    }
    
    if (playedCard) {
      await this.handleCardEffects(playedCard);
      if (playedCard.type === "number") {
        if (playedCard.value === 0) {
          this.switchHandsInCycle();
        } else if (playedCard.value === 7) {
          this.switchHandsWithChoice(player);
        }
      }
    }
    
    // Check for winner
    if (player.hand.length === 0) {
      console.log(`Player ${player.id} wins!`);
      this.winnerId = player.id;
      this.gameOver = true;
      return true;
    } else if (this.mercyRule && player.hand.length > 25) {
      console.log(`Player ${player.id} has too many cards (${player.hand.length}) and is eliminated!`);
      this.players = this.players.filter(p => p.id !== player.id);
      
      if (this.currentPlayerIndex >= this.players.length) {
        this.currentPlayerIndex = 0;
      }
      
      // Check if game ended
      if (this.players.length === 1) {
        this.winnerId = this.players[0].id;
        this.gameOver = true;
        return true;
      }
    }
    
    this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
    this.turnCount++;
    return false;
  }

  async getHumanChoice(player, topCard, isStackingMode = false, stackableCards = []) {
    if (isStackingMode) {
      return new Promise((resolve) => {
        const promptOptions = () => {
          rl.question("Enter the number of the card to play or 'd' to draw: ", (answer) => {
            if (answer.toLowerCase() === 'd') {
              resolve('draw');
              return;
            }
            
            const index = parseInt(answer) - 1;
            if (isNaN(index) || index < 0 || index >= player.hand.length) {
              console.log("Invalid choice. Try again.");
              promptOptions();
              return;
            }
            
            const selectedCard = player.hand[index];
            const isStackable = stackableCards.some(c => 
              c.type === selectedCard.type && c.color === selectedCard.color && c.value === selectedCard.value
            );
            
            if (!isStackable) {
              console.log("That card cannot be stacked. Try again.");
              promptOptions();
              return;
            }
            
            resolve(selectedCard);
          });
        };
        
        promptOptions();
      });
    } else {
      return new Promise((resolve) => {
        const promptCardChoice = () => {
          rl.question("Enter the number of the card to play or 'd' to draw: ", (answer) => {
            if (answer.toLowerCase() === 'd') {
              resolve(null);
              return;
            }
            
            const index = parseInt(answer) - 1;
            if (isNaN(index) || index < 0 || index >= player.hand.length) {
              console.log("Invalid choice. Try again.");
              promptCardChoice();
              return;
            }
            
            const selectedCard = player.hand[index];
            if (!player.isValidCardChoice(selectedCard, topCard)) {
              console.log("That card cannot be played on the current top card. Try again.");
              promptCardChoice();
              return;
            }
            
            resolve(selectedCard);
          });
        };
        
        promptCardChoice();
      });
    }
  }

  async getColorChoice(promptText = "Choose a color (R)ed, (B)lue, (G)reen, (Y)ellow: ") {
    return new Promise((resolve) => {
      const promptColorChoice = () => {
        rl.question(promptText, (answer) => {
          const colorMap = {
            'r': 'Red',
            'b': 'Blue',
            'g': 'Green',
            'y': 'Yellow'
          };
          
          const choice = answer.toLowerCase();
          if (colorMap[choice]) {
            resolve(colorMap[choice]);
          } else {
            console.log("Invalid color. Try again.");
            promptColorChoice();
          }
        });
      };
      
      promptColorChoice();
    });
  }

  async getYesNoChoice(prompt) {
    return new Promise((resolve) => {
      rl.question(prompt, (answer) => {
        resolve(answer.toLowerCase() === 'y');
      });
    });
  }

  async handleCardEffects(card) {
    const penaltyMapping = { "Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10 };
    if (card.type === "action") {
      switch (card.value) {
        case "Skip":
          this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
          console.log(`Player ${this.players[this.currentPlayerIndex].id} was skipped!`);
          break;
        case "SkipAll":
          console.log(`SkipAll played! All other players are skipped. You play again.`);
          this.currentPlayerIndex = (this.currentPlayerIndex - this.direction + this.players.length) % this.players.length;
          break;
        case "Reverse":
          this.direction *= -1;
          console.log(`Direction reversed! Now going ${this.direction > 0 ? "forward" : "backward"}`);
          break;
        case "Draw2":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw2"];
            this.pendingDrawType = "Draw2";
            console.log(`Draw2 played. Pending draw set to 2.`);
          }
          break;
        case "Draw4":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw4"];
            this.pendingDrawType = "Draw4";
            console.log(`Draw4 played. Pending draw set to 4.`);
          }
          break;
        case "DiscardColor":
          {
            const activePlayer = this.players[this.currentPlayerIndex];
            const discardColor = card.color;
            const discarded = activePlayer.hand.filter(c => c.color === discardColor);
            activePlayer.hand = activePlayer.hand.filter(c => c.color !== discardColor);
            discarded.forEach(c => this.discardPile.push(c));
            console.log(`Player ${activePlayer.id} discarded ${discarded.length} ${discardColor} cards.`);
          }
          break;
      }
    } else if (card.type === "wild") {
      switch (card.value) {
        case "ReverseDraw4":
          {
            let targetIndex;
            if (this.direction > 0) {
              targetIndex = (this.currentPlayerIndex - 1 + this.players.length) % this.players.length;
            } else {
              targetIndex = (this.currentPlayerIndex + 1) % this.players.length;
            }
            const targetPlayer = this.players[targetIndex];
            targetPlayer.draw(this.deck, 4);
            console.log(`Player ${targetPlayer.id} draws 4 cards due to ReverseDraw4!`);
            this.direction *= -1;
            console.log(`Direction reversed due to ReverseDraw4! Now going ${this.direction > 0 ? "forward" : "backward"}`);
          }
          break;
        case "Draw6":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw6"];
            this.pendingDrawType = "Draw6";
            console.log(`Draw6 played. Pending draw set to 6.`);
          }
          break;
        case "Draw10":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw10"];
            this.pendingDrawType = "Draw10";
            console.log(`Draw10 played. Pending draw set to 10.`);
          }
          break;
        case "ColorRoulette":
          {
            const nextPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
            const nextPlayer = this.players[nextPlayerIndex];
            
            let chosenColor = card.color;
            
            console.log(`ColorRoulette: Player ${nextPlayer.id} must draw until a ${chosenColor} card`);
            let drawCount = 0;
            while (this.deck.length > 0) {
              const drawnCards = nextPlayer.draw(this.deck, 1);
              if (drawnCards.length === 0) break; // No more cards to draw
              
              drawCount++;
              const drawnCard = drawnCards[0];
              if (drawnCard && drawnCard.color === chosenColor) {
                break;
              }
            }
            console.log(`Player ${nextPlayer.id} drew ${drawCount} cards due to ColorRoulette`);
          }
          break;
      }
    }
  }

  switchHandsInCycle() {
    const n = this.players.length;
    if (n <= 1) return;
    const tempHands = this.players.map(player => player.hand);
    for (let i = 0; i < n; i++) {
      const sourceIndex = (i - this.direction + n) % n;
      this.players[i].hand = tempHands[sourceIndex];
    }
    console.log(`All players' hands have been cycled (card 0 effect).`);
  }

  async switchHandsWithChoice(currentPlayer) {
    const currentPlayerId = currentPlayer.id;
    
    // If the current player is a human player, give them a choice
    if (currentPlayer.isHuman) {
      console.log("You played a 7! Choose a player to switch hands with:");
      
      // Show the other players and their hand sizes
      const otherPlayers = this.players.filter(p => p.id !== currentPlayerId);
      otherPlayers.forEach((player, index) => {
        console.log(`${index + 1}. Player ${player.id}: ${player.hand.length} cards`);
      });
      
      // Allow the player to choose or skip
      const choice = await new Promise((resolve) => {
        rl.question("Enter player number to switch with, or 's' to skip: ", (answer) => {
          if (answer.toLowerCase() === 's') {
            resolve(null);
          } else {
            const index = parseInt(answer) - 1;
            if (isNaN(index) || index < 0 || index >= otherPlayers.length) {
              console.log("Invalid choice. Skipping switch.");
              resolve(null);
            } else {
              resolve(otherPlayers[index]);
            }
          }
        });
      });
      
      // Perform the hand switch if a valid choice was made
      if (choice) {
        const temp = currentPlayer.hand;
        currentPlayer.hand = choice.hand;
        choice.hand = temp;
        console.log(`You switched hands with Player ${choice.id}.`);
        console.log(`Your new hand has ${currentPlayer.hand.length} cards.`);
      } else {
        console.log("You chose not to switch hands.");
      }
    } else {
      // AI player logic - same as before
      const currentCount = currentPlayer.hand.length;
      let targetPlayer = null;
      for (let player of this.players) {
        if (player.id !== currentPlayerId && player.hand.length < currentCount) {
          if (targetPlayer === null || player.hand.length < targetPlayer.hand.length) {
            targetPlayer = player;
          }
        }
      }
      if (targetPlayer) {
        const temp = currentPlayer.hand;
        currentPlayer.hand = targetPlayer.hand;
        targetPlayer.hand = temp;
        console.log(`Player ${currentPlayerId} switched hands with Player ${targetPlayer.id} (card 7 effect).`);
      } else {
        console.log(`Player ${currentPlayerId} chose not to switch hands (card 7 effect).`);
      }
    }
  }

  printGameState() {
    console.log("\nGAME STATE");
    console.log(`Turn: ${this.turnCount}`);
    console.log(`Direction: ${this.direction > 0 ? "→" : "←"}`);
    console.log(`Top card: ${this.getTopCard().toString()}`);
    console.log(`Deck size: ${this.deck.length}`);
    console.log("\nPlayers:");
    this.players.forEach((player, index) => {
      const marker = index === this.currentPlayerIndex ? "►" : " ";
      const humanIndicator = player.isHuman ? " (YOU)" : "";
      console.log(`${marker} Player ${player.id}${humanIndicator}: ${player.hand.length} cards`);
    });
  }

  async startGame() {
    console.log("Starting UNO game...");
    this.printGameState();
    
    while (!this.gameOver && this.players.length > 1) {
      await this.playTurn();
      
      if (this.turnCount % 5 === 0) {
        this.printGameState();
      }
    }
    
    // Print final standings
    console.log("\nFINAL STANDINGS");
    const sortedPlayers = [...this.players].sort((a, b) => a.hand.length - b.hand.length);
    sortedPlayers.forEach((player, index) => {
      const humanIndicator = player.isHuman ? " (YOU)" : "";
      console.log(`${index + 1}. Player ${player.id}${humanIndicator}: ${player.hand.length} cards${player.id === this.winnerId ? " 🏆" : ""}`);
    });
    
    rl.close();
    return this.winnerId;
  }
}

// Function to start a new game
async function playUnoGame() {
  console.log("Welcome to UNO!");
  
  const getNumericInput = (prompt, min, max) => {
    return new Promise((resolve) => {
      const askQuestion = () => {
        rl.question(prompt, (answer) => {
          const num = parseInt(answer);
          if (isNaN(num) || num < min || num > max) {
            console.log(`Please enter a number between ${min} and ${max}.`);
            askQuestion();
          } else {
            resolve(num);
          }
        });
      };
      askQuestion();
    });
  };
  
  const getHumanPlayerIds = (numPlayers) => {
    return new Promise((resolve) => {
      rl.question(`Which player(s) do you want to control? (e.g., "1" or "1,3" or "all"): `, (answer) => {
        if (answer.toLowerCase() === 'all') {
          resolve(Array.from({length: numPlayers}, (_, i) => i + 1));
        } else {
          const ids = answer.split(',')
            .map(id => parseInt(id.trim()))
            .filter(id => !isNaN(id) && id >= 1 && id <= numPlayers);
          if (ids.length === 0) {
            console.log("No valid player IDs entered. Defaulting to player 1.");
            resolve([1]);
          } else {
            resolve(ids);
          }
        }
      });
    });
  };
  
  const numPlayers = await getNumericInput("Enter number of players (2-8): ", 2, 8);
  const initialCards = await getNumericInput("Enter number of cards per player (5-10): ", 5, 10);
  const humanPlayerIds = await getHumanPlayerIds(numPlayers);
  const enableMercy = await new Promise((resolve) => {
    rl.question("Enable mercy rule (eliminate players with >25 cards)? (y/n): ", (answer) => {
      resolve(answer.toLowerCase() === 'y');
    });
  });
  
  console.log(`Starting game with ${numPlayers} players, ${initialCards} cards each.`);
  console.log(`You are controlling player(s): ${humanPlayerIds.join(', ')}`);
  console.log(`Mercy rule is ${enableMercy ? "enabled" : "disabled"}`);
  
  const game = new UnoGame(numPlayers, initialCards, humanPlayerIds, enableMercy);
  const winner = await game.startGame();
  
  console.log(`Game over! Player ${winner} wins!`);
  console.log("Thanks for playing UNO!");
}

// Start the game
playUnoGame().catch(err => {
  console.error("Error during game:", err);
  rl.close();
});