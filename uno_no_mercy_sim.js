// =================== Setup: Import Modules & Create Data Folder ===================
const fs = require('fs');
const path = require('path');

// Define the directory to store simulation data
const DATA_DIR = path.join(__dirname, 'simulation_data');

// Create the directory if it does not exist
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  console.log(`Created folder: ${DATA_DIR}`);
}

// =================== Card & Player Classes ===================
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

class Player {
  constructor(id) {
    this.id = id;
    this.hand = [];
  }

  draw(deck, count = 1) {
    let drawnCards = [];
    for (let i = 0; i < count; i++) {
      if (deck.length > 0) {
        const card = deck.pop();
        this.hand.push(card);
        drawnCards.push(card);
        SimulationStats.incrementDrawCount(1);
        SimulationStats.drawEvents++;
      }
    }
    return drawnCards;
  }

  // Improved decision-making: Evaluate each playable card using a heuristic score.
  findBestCard(topCard) {
    if (!topCard) return this.hand.length > 0 ? this.hand[0] : null;
    
    // Use active color if top card is wild and has one.
    const isWildWithNoColor = topCard.type === "wild" && !topCard.color;
    const activeColor = topCard.color || null;
    
    const playableCards = this.hand.filter(card => {
      if (card.type === "wild") return true;
      if (isWildWithNoColor) return true; // Allow any color card on colorless wild
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

  hasMatchingCard(topCard) {
    return this.hand.some(card =>
      card.color === topCard.color ||
      (card.type === "number" && card.value === topCard.value)
    );
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
}

// =================== UnoGame Class with Enhanced Logging ===================
class UnoGame {
  /**
   * @param {number} n - Number of players.
   * @param {number} m - Initial cards per player.
   * @param {number} k - Maximum allowed turns.
   * @param {boolean} mercyRule - If true, players with 25+ cards are eliminated.
   * @param {boolean} verbose - If true, prints game logs.
   * @param {function} metricsCollector - Callback to record card plays.
   * @param {boolean} trackOneRoundDetail - If true, store detailed log for one-round games.
   */
  constructor(n, m, k, mercyRule = true, verbose = false, metricsCollector = null, trackOneRoundDetail = false) {
    this.players = Array.from({ length: n }, (_, i) => new Player(i + 1));
    this.deck = this.createDeck();
    this.discardPile = [];
    this.currentPlayerIndex = 0;
    this.direction = 1;
    this.maxTurns = k;
    this.mercyRule = mercyRule;
    this.turnCount = 0;
    this.verbose = verbose;
    this.metricsCollector = metricsCollector;
    this.winnerId = null;
    this.pendingDraw = 0;
    this.pendingDrawType = null;
    this.trackOneRoundDetail = trackOneRoundDetail;
    this.gameLog = trackOneRoundDetail ? [] : null;
    this.shuffleDeck();
    this.dealInitialCards(m);

    const startCard = this.deck.pop();
    this.discardPile.push(startCard);
    this.logMsg(`Game started with ${n} players, ${m} cards each, max ${k} turns`);
    this.logMsg(`Starting card: ${startCard.toString()}`);
  }

  logMsg(message) {
    if (this.trackOneRoundDetail && this.gameLog) {
      this.gameLog.push(message);
    }
    if (this.verbose) {
      console.log(message);
    }
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

  playTurn() {
    let turnDrawCount = 0;
    const currentMaxHandSize = Math.max(...this.players.map(p => p.hand.length));
    if (currentMaxHandSize > SimulationStats.maxHandSizeEver) {
      SimulationStats.maxHandSizeEver = currentMaxHandSize;
    }

    const player = this.players[this.currentPlayerIndex];
    const preTurnHand = player.hand.map(card => card.toString());

    // Handle pending draw stacking.
    if (this.pendingDraw > 0) {
      const allowedStacking = {
        "Draw2": ["Draw2", "Draw4", "Draw6", "Draw10"],
        "Draw4": ["Draw4", "Draw6", "Draw10"],
        "Draw6": ["Draw6", "Draw10"],
        "Draw10": ["Draw10"]
      };
      const penaltyMapping = { "Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10 };
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
      if (stackableCards.length > 0) {
        const cardToPlay = stackableCards[0];
        const playedCard = player.playCard(cardToPlay);
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
        }
        this.discardPile.push(playedCard);
        this.pendingDraw += penaltyMapping[playedCard.value];
        this.pendingDrawType = playedCard.value;
        SimulationStats.totalStackingEvents++;
        SimulationStats.totalStackedPenalty += penaltyMapping[playedCard.value];
        this.logMsg(`► Player ${player.id} stacks with ${playedCard.toString()}, new pending draw: ${this.pendingDraw}`);
        if (this.metricsCollector) {
          this.metricsCollector(playedCard);
        }
        this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
        this.turnCount++;
        SimulationStats.totalCardsDrawnInTurns += turnDrawCount;
        if (turnDrawCount > SimulationStats.maxCardsDrawnInTurn) {
          SimulationStats.maxCardsDrawnInTurn = turnDrawCount;
        }
        return false;
      } else {
        const drawnCards = player.draw(this.deck, this.pendingDraw);
        turnDrawCount += drawnCards.length;
        SimulationStats.totalPendingDrawResolved += this.pendingDraw;
        this.logMsg(`► Player ${player.id} cannot stack and draws ${this.pendingDraw} cards (hand now: ${player.hand.length} cards).`);
        this.pendingDraw = 0;
        this.pendingDrawType = null;
        this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
        this.turnCount++;
        SimulationStats.totalCardsDrawnInTurns += turnDrawCount;
        if (turnDrawCount > SimulationStats.maxCardsDrawnInTurn) {
          SimulationStats.maxCardsDrawnInTurn = turnDrawCount;
        }
        return false;
      }
    }
    // End pending draw handling.

    const topCard = this.getTopCard();
    this.logMsg(`\n[TURN ${this.turnCount + 1}] Player ${player.id}'s turn`);
    this.logMsg(`Top card: ${topCard.toString()}`);
    const bestCard = player.findBestCard(topCard);
    if (bestCard) {
      let playedCard;
      if (bestCard.type === "wild") {
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
        playedCard = player.playCard(bestCard);
        playedCard.color = chosenColor;
        this.discardPile.push(playedCard);
        this.logMsg(`► Player ${player.id} played ${playedCard.toString()}`);
        this.logMsg(`► Chosen color: ${chosenColor}`);
        this.logMsg(`► Cards remaining: ${player.hand.length}`);
      } else {
        playedCard = player.playCard(bestCard);
        this.discardPile.push(playedCard);
        this.logMsg(`► Player ${player.id} played ${playedCard.toString()}`);
        this.logMsg(`► Cards remaining: ${player.hand.length}`);
      }
      if (this.metricsCollector) {
        this.metricsCollector(playedCard);
      }
      this.handleCardEffects(bestCard);
      if (bestCard.type === "number") {
        if (bestCard.value === 0) {
          this.switchHandsInCycle();
        } else if (bestCard.value === 7) {
          this.switchHandsWithChoice(player);
        }
      }
    } else {
      const drawnCards = player.draw(this.deck, 1);
      turnDrawCount += drawnCards.length;
      if (drawnCards.length > 0) {
        this.logMsg(`► Player ${player.id} had no valid card and drew 1 card`);
        this.logMsg(`► Cards remaining: ${player.hand.length}`);
      } else {
        this.logMsg(`► Player ${player.id} had no valid card and deck is empty`);
        this.logMsg(`► Cards remaining: ${player.hand.length}`);
      }
    }
    if (this.mercyRule && player.hand.length >= 25) {
      this.logMsg(`⚠️ Player ${player.id} is eliminated with ${player.hand.length} cards due to mercy!`);
      SimulationStats.totalMercyEliminations++;
      this.players.splice(this.currentPlayerIndex, 1);
      if (this.currentPlayerIndex >= this.players.length) {
        this.currentPlayerIndex = 0;
      }
    } else {
      this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
    }
    this.turnCount++;
    SimulationStats.totalCardsDrawnInTurns += turnDrawCount;
    if (turnDrawCount > SimulationStats.maxCardsDrawnInTurn) {
      SimulationStats.maxCardsDrawnInTurn = turnDrawCount;
    }
    if (player.hand.length === 0) {
      this.logMsg(`🏆 Player ${player.id} wins!`);
      this.winnerHandSnapshot = preTurnHand;
      this.winnerId = player.id;
      return true;
    }
    return false;
  }

  handleCardEffects(card) {
    const penaltyMapping = { "Draw2": 2, "Draw4": 4, "Draw6": 6, "Draw10": 10 };
    if (card.type === "action") {
      switch (card.value) {
        case "Skip":
          this.currentPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
          this.logMsg(`⚡ Player ${this.players[this.currentPlayerIndex].id} was skipped!`);
          break;
        case "SkipAll":
          this.logMsg(`⚡ SkipAll played! All other players are skipped. Player ${this.players[this.currentPlayerIndex].id} goes again.`);
          this.currentPlayerIndex = (this.currentPlayerIndex - this.direction + this.players.length) % this.players.length;
          break;
        case "Reverse":
          this.direction *= -1;
          this.logMsg(`⚡ Direction reversed! Now going ${this.direction > 0 ? "forward" : "backward"}`);
          break;
        case "Draw2":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw2"];
            this.pendingDrawType = "Draw2";
            this.logMsg(`⚡ Draw2 played. Pending draw set to 2.`);
          }
          break;
        case "Draw4":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw4"];
            this.pendingDrawType = "Draw4";
            this.logMsg(`⚡ Draw4 played. Pending draw set to 4.`);
          }
          break;
        case "DiscardColor":
          {
            const activePlayer = this.players[this.currentPlayerIndex];
            const discardColor = card.color;
            const discarded = activePlayer.hand.filter(c => c.color === discardColor);
            activePlayer.hand = activePlayer.hand.filter(c => c.color !== discardColor);
            discarded.forEach(c => this.discardPile.push(c));
            this.logMsg(`⚡ Player ${activePlayer.id} discarded ${discarded.length} ${discardColor} cards (hand now: ${activePlayer.hand.length}).`);
          }
          break;
        default:
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
            this.logMsg(`⚡ Player ${targetPlayer.id} draws 4 cards due to ReverseDraw4!`);
            this.direction *= -1;
            this.logMsg(`⚡ Direction reversed due to ReverseDraw4! Now going ${this.direction > 0 ? "forward" : "backward"}`);
          }
          break;
        case "Draw6":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw6"];
            this.pendingDrawType = "Draw6";
            this.logMsg(`⚡ Draw6 played. Pending draw set to 6.`);
          }
          break;
        case "Draw10":
          if (this.pendingDraw === 0) {
            this.pendingDraw = penaltyMapping["Draw10"];
            this.pendingDrawType = "Draw10";
            this.logMsg(`⚡ Draw10 played. Pending draw set to 10.`);
          }
          break;
        case "ColorRoulette":
          {
            const nextPlayerIndex = (this.currentPlayerIndex + this.direction + this.players.length) % this.players.length;
            const nextPlayer = this.players[nextPlayerIndex];
            let chosenColor = card.color;

            this.logMsg(`⚡ ColorRoulette: Player ${nextPlayer.id} chooses ${chosenColor}`);
            let drawCount = 0;
            while (this.deck.length > 0) {
              const drawnCards = nextPlayer.draw(this.deck, 1);
              drawCount += drawnCards.length;
              const drawnCard = drawnCards[0];
              if (drawnCard && drawnCard.color === chosenColor) {
                break;
              }
            }
            this.logMsg(`⚡ Player ${nextPlayer.id} had to draw ${drawCount} cards due to ColorRoulette`);
          }
          break;
        default:
          break;
      }
    }
  }

  // Card 0: Cycle all players' hands.
  switchHandsInCycle() {
    const n = this.players.length;
    if (n <= 1) return;
    const tempHands = this.players.map(player => player.hand);
    for (let i = 0; i < n; i++) {
      const sourceIndex = (i - this.direction + n) % n;
      this.players[i].hand = tempHands[sourceIndex];
    }
    this.logMsg(`⚡ All players' hands have been cycled (card 0 effect).`);
    SimulationStats.totalCyclesOn0++;
  }

  // Card 7: Swap hands if beneficial.
  switchHandsWithChoice(currentPlayer) {
    const currentCount = currentPlayer.hand.length;
    let targetPlayer = null;
    for (let player of this.players) {
      if (player.id !== currentPlayer.id && player.hand.length < currentCount) {
        if (targetPlayer === null || player.hand.length < targetPlayer.hand.length) {
          targetPlayer = player;
        }
      }
    }
    if (targetPlayer) {
      const temp = currentPlayer.hand;
      currentPlayer.hand = targetPlayer.hand;
      targetPlayer.hand = temp;
      this.logMsg(`⚡ Player ${currentPlayer.id} switched hands with Player ${targetPlayer.id} (card 7 effect).`);
      SimulationStats.totalSwitchesOn7++;
    } else {
      this.logMsg(`⚡ Player ${currentPlayer.id} chose not to switch hands (card 7 effect) because no opponent had fewer cards.`);
    }
  }

  checkAndRecycleDeck() {
    if (this.deck.length < 5) {
      this.logMsg("♻️ Shuffling discard pile back into deck");
      const topCard = this.discardPile.pop();
      this.deck = this.discardPile;
      this.discardPile = topCard ? [topCard] : [];
      this.shuffleDeck();
    }
  }

  printGameState() {
    this.logMsg("GAME STATE");
    this.logMsg(`Turn: ${this.turnCount}`);
    this.logMsg(`Direction: ${this.direction > 0 ? "→" : "←"}`);
    this.logMsg(`Top card: ${this.getTopCard().toString()}`);
    this.logMsg(`Deck size: ${this.deck.length}`);
    this.logMsg(`Discard pile: ${this.discardPile.length}`);
    this.logMsg("\nPlayers:");
    this.players.forEach((player, index) => {
      const marker = index === this.currentPlayerIndex ? "►" : " ";
      this.logMsg(`${marker} Player ${player.id}: ${player.hand.length} cards`);
    });
  }

  startGame() {
    let gameOver = false;
    while (!gameOver && this.turnCount < this.maxTurns && this.players.length > 1) {
      this.checkAndRecycleDeck();
      if (this.turnCount % 10 === 0) {
        this.printGameState();
      }
      gameOver = this.playTurn();
    }
    if (!gameOver) {
      let winnerIndex = 0;
      let minCards = Infinity;
      this.players.forEach((player, index) => {
        if (player.hand.length < minCards) {
          minCards = player.hand.length;
          winnerIndex = index;
        }
      });
      this.logMsg(`🏁 Game Over after ${this.turnCount} turns!`);
      this.logMsg(`🏆 Player ${this.players[winnerIndex].id} wins with ${minCards} cards!`);
    }
    this.logMsg("FINAL STANDINGS");
    const sortedPlayers = [...this.players].sort((a, b) => a.hand.length - b.hand.length);
    sortedPlayers.forEach((player, index) => {
      this.logMsg(`${index + 1}. Player ${player.id}: ${player.hand.length} cards${index === 0 ? " 🏆" : ""}`);
    });
    if (sortedPlayers.length < this.players.length) {
      this.logMsg(`ELIMINATED PLAYERS: ${this.players.length - sortedPlayers.length} players were eliminated`);
    }
    this.logMsg("GAME STATISTICS");
    this.logMsg(`Total turns played: ${this.turnCount}`);
    this.logMsg(`Cards remaining in deck: ${this.deck.length}`);
    this.logMsg(`Cards in discard pile: ${this.discardPile.length}`);
    this.logMsg(`Final top card: ${this.getTopCard().toString()}`);
  }
}

// =================== Simulation Metrics and Runner ===================
const SimulationStats = {
  totalGames: 0,
  totalTurns: 0,
  turnCounts: {}, // Object mapping game duration (turn count) to frequency.
  cardPlayCounts: {},
  specialCardCounts: { Draw2: 0, Draw4: 0, Draw6: 0, Draw10: 0, ReverseDraw4: 0, ColorRoulette: 0 },
  totalNonNumberedCards: 0,
  actionCardCount: 0,
  wildCardCount: 0,
  totalDraws: 0,
  drawEvents: 0,
  totalCardsDrawnInTurns: 0,
  maxCardsDrawnInTurn: 0,
  oneRoundGameCount: 0,
  oneRoundGameExamples: [], // Limited to a few examples.
  maxExamplesToStore: 5,
  totalStackingEvents: 0,
  totalStackedPenalty: 0,
  totalPendingDrawResolved: 0,
  totalSwitchesOn7: 0,
  totalCyclesOn0: 0,
  totalMercyEliminations: 0,
  maxHandSizeEver: 0,
  
  updateCardPlay(card) {
    const key = (card.type === "wild") ? card.value : card.toString();
    this.cardPlayCounts[key] = (this.cardPlayCounts[key] || 0) + 1;
    
    if (["Draw2", "Draw4", "Draw6", "Draw10", "ReverseDraw4", "ColorRoulette"].includes(card.value)) {
      this.specialCardCounts[card.value] = (this.specialCardCounts[card.value] || 0) + 1;
    }
    if (card.type !== "number") {
      this.totalNonNumberedCards++;
      if (card.type === "action") {
        this.actionCardCount++;
      } else if (card.type === "wild") {
        this.wildCardCount++;
      }
    }
  },
  
  incrementDrawCount(num) {
    this.totalDraws += num;
  },
  
  recordGameTurnCount(turns) {
    this.turnCounts[turns] = (this.turnCounts[turns] || 0) + 1;
  },
  
  // Write stats and examples to files in the DATA_DIR folder.
  writeStatsToDisk(batchNumber) {
    const stats = {
      totalGames: this.totalGames,
      totalTurns: this.totalTurns,
      avgTurns: this.totalTurns / this.totalGames,
      cardPlayCounts: this.cardPlayCounts,
      specialCardCounts: this.specialCardCounts,
      stackingMetrics: {
        totalStackingEvents: this.totalStackingEvents,
        totalStackedPenalty: this.totalStackedPenalty,
        totalPendingDrawResolved: this.totalPendingDrawResolved
      },
      drawMetrics: {
        totalDraws: this.totalDraws,
        drawEvents: this.drawEvents,
        maxCardsDrawnInTurn: this.maxCardsDrawnInTurn,
        avgDrawsPerTurn: this.totalCardsDrawnInTurns / this.totalTurns
      },
      handSwitchingMetrics: {
        totalSwitchesOn7: this.totalSwitchesOn7,
        totalCyclesOn0: this.totalCyclesOn0
      },
      mercyMetrics: {
        totalMercyEliminations: this.totalMercyEliminations,
        avgMercyLosses: this.totalMercyEliminations / this.totalGames
      },
      additionalMetrics: {
        totalNonNumberedCards: this.totalNonNumberedCards,
        actionCardCount: this.actionCardCount,
        wildCardCount: this.wildCardCount,
        nonNumberedRatio: ((this.totalNonNumberedCards / Object.values(this.cardPlayCounts).reduce((a, b) => a + b, 0)) * 100),
        maxHandSizeEver: this.maxHandSizeEver,
        oneRoundGameCount: this.oneRoundGameCount
      },
      turnCounts: this.turnCounts
    };
    
    const statsFile = path.join(DATA_DIR, `uno_stats_batch_${batchNumber}.json`);
    fs.writeFileSync(statsFile, JSON.stringify(stats, null, 2));
    
    if (this.oneRoundGameExamples.length > 0) {
      const examplesFile = path.join(DATA_DIR, `one_round_examples_batch_${batchNumber}.json`);
      fs.writeFileSync(examplesFile, JSON.stringify(this.oneRoundGameExamples, null, 2));
    }
    
    console.log(`Stats written to disk for batch ${batchNumber}`);
  },
  
  resetForNewBatch() {
    // Clear only the arrays that are large.
    this.oneRoundGameExamples = [];
  }
};

// =================== Simulation Runner ===================
function runSimulationsInBatches(totalSimulations, batchSize) {
  console.log(`Starting ${totalSimulations} simulations in batches of ${batchSize}...`);
  
  let completedSimulations = 0;
  let batchNumber = 1;
  
  while (completedSimulations < totalSimulations) {
    const currentBatchSize = Math.min(batchSize, totalSimulations - completedSimulations);
    console.log(`Running batch ${batchNumber}: ${currentBatchSize} simulations`);
    
    for (let i = 0; i < currentBatchSize; i++) {
      const shouldTrackDetail = SimulationStats.oneRoundGameExamples.length < SimulationStats.maxExamplesToStore;
      
      const game = new UnoGame(6, 7, 100000, true, false, 
        (card) => SimulationStats.updateCardPlay(card), 
        false);
      
      game.startGame();
      
      SimulationStats.totalGames++;
      SimulationStats.totalTurns += game.turnCount;
      SimulationStats.recordGameTurnCount(game.turnCount);
      
      if (game.turnCount === 1) {
        SimulationStats.oneRoundGameCount++;
        if (shouldTrackDetail) {
          SimulationStats.oneRoundGameExamples.push({
            gameNumber: completedSimulations + i + 1,
            winnerId: game.winnerId,
            winningPlayerHand: game.winnerHandSnapshot,
            gameLog: game.gameLog ? game.gameLog.slice() : []
          });
        }
      }
      
      if ((i + 1) % (batchSize / 10) === 0 || i === currentBatchSize - 1) {
        console.log(`Completed ${i + 1}/${currentBatchSize} simulations in batch ${batchNumber}`);
      }
    }
    
    SimulationStats.writeStatsToDisk(batchNumber);
    SimulationStats.resetForNewBatch();
    
    completedSimulations += currentBatchSize;
    batchNumber++;
    
    if (global.gc) {
      global.gc();
    } else {
      console.log("Garbage collection not available. Run with --expose-gc flag for better memory management.");
    }
  }
  
  // Write final summary and metrics.
  printSimulationSummary();
  printSimulationMetrics();
}

function printSimulationSummary() {
  console.log("\n======= Simulation Summary =======");
  console.log(`Total games simulated: ${SimulationStats.totalGames}`);
  console.log(`Total turns played: ${SimulationStats.totalTurns}`);
  const avgTurns = SimulationStats.totalTurns / SimulationStats.totalGames;
  console.log(`Average game duration (turns): ${avgTurns.toFixed(2)}`);
  
  // Compute longest and shortest game durations.
  const gameTurnDurations = Object.keys(SimulationStats.turnCounts).map(Number);
  const longestGame = Math.max(...gameTurnDurations);
  const shortestGame = Math.min(...gameTurnDurations);
  console.log(`Longest game (turns): ${longestGame}`);
  console.log(`Shortest game (turns): ${shortestGame}`);
  
  console.log(`One-round games: ${SimulationStats.oneRoundGameCount} (${(SimulationStats.oneRoundGameCount / SimulationStats.totalGames * 100).toFixed(2)}%)`);
  console.log(`Total mercy eliminations: ${SimulationStats.totalMercyEliminations}`);
  console.log("Check output files for detailed statistics.");
  console.log("==================================\n");
}

function printSimulationMetrics() {
  console.log("\n======= Simulation Metrics =======");
  console.log(`Total games simulated: ${SimulationStats.totalGames}`);
  console.log(`Total turns played: ${SimulationStats.totalTurns}`);
  const avgTurns = SimulationStats.totalTurns / SimulationStats.totalGames;
  console.log(`Average game duration (turns): ${avgTurns.toFixed(2)}`);
  
  const gameTurnDurations = Object.keys(SimulationStats.turnCounts).map(Number);
  const longestGame = Math.max(...gameTurnDurations);
  const shortestGame = Math.min(...gameTurnDurations);
  console.log(`Longest game (turns): ${longestGame}`);
  console.log(`Shortest game (turns): ${shortestGame}`);

  // Top 15 most played cards:
  const cardEntries = Object.entries(SimulationStats.cardPlayCounts);
  cardEntries.sort((a, b) => b[1] - a[1]);
  console.log("\nTop 15 most played cards:");
  cardEntries.slice(0, 15).forEach(([card, count]) => {
    console.log(`  ${card}: ${count} times`);
  });
  if (cardEntries.length > 0) {
    const leastPlayed = cardEntries.reduce((min, cur) => cur[1] < min[1] ? cur : min, cardEntries[0]);
    console.log(`\nLeast played card: ${leastPlayed[0]} played ${leastPlayed[1]} times`);
  }

  console.log("\nFrequency of special draw cards played:");
  for (let special of ["Draw2", "Draw4", "Draw6", "Draw10", "ReverseDraw4", "ColorRoulette"]) {
    console.log(`  ${special}: ${SimulationStats.specialCardCounts[special] || 0} times`);
  }

  console.log("\nStackable Draw Metrics:");
  console.log(`Total stacking events: ${SimulationStats.totalStackingEvents}`);
  console.log(`Total penalty added via stacking: ${SimulationStats.totalStackedPenalty}`);
  console.log(`Total pending draw penalty resolved: ${SimulationStats.totalPendingDrawResolved}`);

  console.log("\nDraw Metrics:");
  console.log(`Total cards drawn: ${SimulationStats.totalDraws}`);
  console.log(`Total draw events: ${SimulationStats.drawEvents}`);
  console.log(`Most cards drawn in a single turn: ${SimulationStats.maxCardsDrawnInTurn}`);
  const avgDrawsPerTurn = SimulationStats.totalCardsDrawnInTurns / SimulationStats.totalTurns;
  console.log(`Average cards drawn per turn: ${avgDrawsPerTurn.toFixed(2)}`);

  console.log("\nHand Switching Metrics:");
  console.log(`Total switches on card 7: ${SimulationStats.totalSwitchesOn7}`);
  console.log(`Total cycles on card 0: ${SimulationStats.totalCyclesOn0}`);

  console.log("\nMercy Metrics:");
  console.log(`Total mercy eliminations: ${SimulationStats.totalMercyEliminations}`);
  const avgMercyLosses = SimulationStats.totalMercyEliminations / SimulationStats.totalGames;
  console.log(`Average mercy losses per game: ${avgMercyLosses.toFixed(2)}`);

  console.log("\nAdditional Metrics:");
  console.log(`Total non-numbered cards played: ${SimulationStats.totalNonNumberedCards}`);
  console.log(`  (Action cards: ${SimulationStats.actionCardCount}, Wild cards: ${SimulationStats.wildCardCount})`);
  const totalCardPlays = Object.values(SimulationStats.cardPlayCounts).reduce((a, b) => a + b, 0);
  const nonNumberedRatio = ((SimulationStats.totalNonNumberedCards / totalCardPlays) * 100).toFixed(2);
  console.log(`Non-numbered cards constitute ${nonNumberedRatio}% of all plays.`);
  console.log(`Maximum hand size observed: ${SimulationStats.maxHandSizeEver}`);
  console.log(`Games lasting only 1 round: ${SimulationStats.oneRoundGameCount}`);
  if (SimulationStats.oneRoundGameCount > 0 && SimulationStats.oneRoundGameExamples.length > 0) {
    console.log("Example of a 1-round game (detailed log):");
    const example = SimulationStats.oneRoundGameExamples[0];
    console.log(`  Game #${example.gameNumber}: Winner: Player ${example.winnerId}`);
    console.log(`  Winning player's hand (pre-winning turn): [${example.winningPlayerHand.join(", ")}]`);
    console.log("  Move Log:");
    example.gameLog.forEach(msg => console.log(`    ${msg}`));
  }
  console.log("==================================\n");
}

// Run simulations with the desired batch size.
// Adjust BATCH_SIZE based on available memory.
const BATCH_SIZE = 10000;
runSimulationsInBatches(10000000, BATCH_SIZE);

// const game = new UnoGame(4, 7, 100000, false, true);
// game.startGame();
