import pygame
import random
import sys

# --- Constants ---
SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 768
BG_COLOR = (34, 100, 34)  # Darker Felt Green
CARD_WIDTH, CARD_HEIGHT = 60, 90
FPS = 60
ANIMATION_SPEED = 0.15

# Colors
WHITE = (240, 240, 240)
BLACK = (20, 20, 20)
RED = (200, 40, 40)
GOLD = (255, 215, 0)
SCORE_BG = (20, 50, 20)
GRAY = (150, 150, 150)

SUITS = ['♠', '♥', '♣', '♦']
SUIT_COLORS = {'♠': BLACK, '♥': RED, '♣': BLACK, '♦': RED}
RANKS = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 
    10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'
}

# States
STATE_BIDDING = 0
STATE_CHOOSE_TRUMP = 1
STATE_PLAYING = 2
STATE_ANIMATING = 3
STATE_ROUND_END = 4

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)
        self.x, self.y = 0, 0
        self.target_x, self.target_y = 0, 0
        self.is_moving = False
        self.selected = False

    def set_pos(self, x, y):
        self.x, self.y = x, y
        self.target_x, self.target_y = x, y
        self.rect.topleft = (int(x), int(y))

    def move_to(self, x, y):
        self.target_x = x
        self.target_y = y
        self.is_moving = True

    def update(self):
        if self.is_moving:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            if abs(dx) < 1 and abs(dy) < 1:
                self.x, self.y = self.target_x, self.target_y
                self.is_moving = False
            else:
                self.x += dx * ANIMATION_SPEED
                self.y += dy * ANIMATION_SPEED
            self.rect.topleft = (int(self.x), int(self.y))
        return self.is_moving

    def draw(self, surface, hidden=False):
        if hidden:
            pygame.draw.rect(surface, (60, 60, 100), (self.x, self.y, CARD_WIDTH, CARD_HEIGHT), border_radius=4)
            pygame.draw.rect(surface, WHITE, (self.x, self.y, CARD_WIDTH, CARD_HEIGHT), 2, border_radius=4)
            # Simple Pattern
            pygame.draw.line(surface, (80, 80, 140), (self.x+5, self.y+5), (self.x+CARD_WIDTH-5, self.y+CARD_HEIGHT-5), 2)
            pygame.draw.line(surface, (80, 80, 140), (self.x+CARD_WIDTH-5, self.y+5), (self.x+5, self.y+CARD_HEIGHT-5), 2)
        else:
            pygame.draw.rect(surface, WHITE, (self.x, self.y, CARD_WIDTH, CARD_HEIGHT), border_radius=4)
            border_col = GOLD if self.selected else (50, 50, 50)
            thickness = 3 if self.selected else 1
            pygame.draw.rect(surface, border_col, (self.x, self.y, CARD_WIDTH, CARD_HEIGHT), thickness, border_radius=4)
            
            font_small = pygame.font.SysFont('Arial', 18, bold=True)
            font_large = pygame.font.SysFont('Arial', 32)
            col = SUIT_COLORS[self.suit]
            
            surface.blit(font_small.render(RANKS[self.rank], True, col), (self.x + 3, self.y + 2))
            surface.blit(font_small.render(self.suit, True, col), (self.x + 3, self.y + 18))
            
            center_txt = font_large.render(self.suit, True, col)
            cw, ch = center_txt.get_size()
            surface.blit(center_txt, (self.x + (CARD_WIDTH-cw)//2, self.y + (CARD_HEIGHT-ch)//2))

class Player:
    def __init__(self, name, p_id, is_bot=True):
        self.name = name
        self.id = p_id
        self.hand = []
        self.is_bot = is_bot
        self.tricks_won = 0
        self.bid_val = 0  # 0 = no bid yet
        self.status = "WAITING" # WAITING, PASS, BID: X

    def sort_hand(self):
        self.hand.sort(key=lambda c: (c.suit, c.rank))

class TarneebGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tarneeb Pro: Clean UI")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 18)
        self.font_bold = pygame.font.SysFont('Arial', 24, bold=True)
        self.font_big = pygame.font.SysFont('Arial', 36, bold=True)
        
        self.players = [
            Player("You", 0, is_bot=False),
            Player("Right Bot", 1),
            Player("Teammate", 2),
            Player("Left Bot", 3)
        ]
        
        # Positions for UI labels
        self.ui_positions = [
            (SCREEN_WIDTH//2, SCREEN_HEIGHT - 160), # Bottom (Me)
            (SCREEN_WIDTH - 100, SCREEN_HEIGHT//2), # Right
            (SCREEN_WIDTH//2, 80),                  # Top
            (100, SCREEN_HEIGHT//2)                 # Left
        ]

        self.team_a_score = 0
        self.team_b_score = 0
        self.dealer_idx = 0
        self.reset_round()

    # --- Add this helper method inside the Class ---
    def get_trick_winner(self, trick):
        if not trick: return -1
        
        # The winner is the player who played the highest card 
        # (accounting for Trump and Lead suit)
        winner_idx = trick[0][0]
        lead_suit = trick[0][1].suit
        best_card = trick[0][1]

        for p_idx, card in trick[1:]:
            # 1. Trump overrides non-trump
            if card.suit == self.trump_suit:
                if best_card.suit != self.trump_suit:
                    best_card = card
                    winner_idx = p_idx
                elif card.rank > best_card.rank: # Higher trump wins
                    best_card = card
                    winner_idx = p_idx
            # 2. Follow suit (if best card isn't trump)
            elif card.suit == lead_suit:
                if best_card.suit == lead_suit and card.rank > best_card.rank:
                    best_card = card
                    winner_idx = p_idx
        
        return winner_idx, best_card

    # --- Replace the old bot_play_card with this smart version ---
    def bot_play_card(self, player):
        lead_suit = self.current_trick[0][1].suit if self.current_trick else None
        valid = self.get_valid_moves(player.hand, lead_suit)
        
        # Sort valid cards: Index 0 is Low, Index -1 is High
        valid.sort(key=lambda c: c.rank)

        # SCENARIO 1: Bot is Leading (Trick is empty)
        if not self.current_trick:
            # Play highest card to force others to spend high cards
            return valid[-1]

        # SCENARIO 2: Analyze the table
        current_winner_idx, best_card_on_table = self.get_trick_winner(self.current_trick)
        partner_idx = (player.id + 2) % 4
        
        is_partner_winning = (current_winner_idx == partner_idx)

        if is_partner_winning:
            # SMART MOVE: If partner is winning, do NOT waste high cards.
            # Play the absolute lowest valid card (trash).
            return valid[0] 
        
        else:
            # SCENARIO 3: Partner is losing (Opponent is winning)
            # We must try to win if possible.
            
            # Check if our highest card can beat the table
            my_best = valid[-1]
            
            # Logic to check if 'my_best' actually beats 'best_card_on_table'
            can_win = False
            if my_best.suit == self.trump_suit:
                if best_card_on_table.suit != self.trump_suit:
                    can_win = True # We trumped their non-trump
                elif my_best.rank > best_card_on_table.rank:
                    can_win = True # Over-trumped
            elif my_best.suit == lead_suit:
                if best_card_on_table.suit == lead_suit and best_card_on_table.suit != self.trump_suit:
                     if my_best.rank > best_card_on_table.rank:
                         can_win = True
            
            if can_win:
                return valid[-1] # Play to win!
            else:
                # If we can't win, don't waste a medium card. Dump the lowest.
                return valid[0]

    def reset_round(self):
        # 1. Generate the deck
        self.deck = [Card(r, s) for r in RANKS for s in SUITS]
        random.shuffle(self.deck)
        
        # 2. Create 4 temporary hands from the shuffle
        temp_hands = []
        for i in range(4):
            temp_hands.append(self.deck[i*13 : (i+1)*13])

        # 3. Define a "Strength" function (Favors High Cards heavily)
        def get_hand_strength(hand):
            # Weigh face cards (11-14) exponentially higher
            score = 0
            for card in hand:
                if card.rank >= 10:
                    score += card.rank ** 2  # Exponential weight for 10, J, Q, K, A
                else:
                    score += card.rank
            return score

        # 4. Sort hands by strength (Index 0 = God Hand, Index 3 = Weakest)
        temp_hands.sort(key=get_hand_strength, reverse=True)

        # 5. Pick "Lucky" players (1 or 2 players get the best hands)
        # We start with [0, 1, 2, 3] and pick 1 or 2 to be favored
        all_indices = [0, 1, 2, 3]
        lucky_count = random.randint(1, 2)
        lucky_players = random.sample(all_indices, lucky_count)
        
        # print(f"DEBUG: Round Rigged for Players: {lucky_players}") # Console tracker

        # 6. Assign hands
        final_hands = [None] * 4
        
        # Give the best hands (0 and maybe 1) to the lucky players
        for i, p_idx in enumerate(lucky_players):
            final_hands[p_idx] = temp_hands[i]

        # Give the remaining (weaker) hands to the others
        remaining_players = [x for x in all_indices if x not in lucky_players]
        remaining_hands = temp_hands[lucky_count:]
        random.shuffle(remaining_players) # Shuffle so the worst hand isn't predictable
        
        for i, p_idx in enumerate(remaining_players):
            final_hands[p_idx] = remaining_hands[i]

        # 7. Apply to Player Objects
        for i in range(4):
            self.players[i].hand = final_hands[i]
            self.players[i].sort_hand()
            self.players[i].tricks_won = 0
            self.players[i].bid_val = 0
            self.players[i].status = "WAITING"
            
            # Reset card positions (Animation setup)
            for c in self.players[i].hand:
                if i == 0: c.set_pos(SCREEN_WIDTH//2, SCREEN_HEIGHT + 100)
                elif i == 1: c.set_pos(SCREEN_WIDTH + 50, SCREEN_HEIGHT//2)
                elif i == 2: c.set_pos(SCREEN_WIDTH//2, -100)
                elif i == 3: c.set_pos(-50, SCREEN_HEIGHT//2)
        
        self.animate_deal()
        
        # Game State Reset
        self.state = STATE_BIDDING
        self.current_bidder_idx = (self.dealer_idx + 1) % 4
        self.highest_bid = 6
        self.bid_winner = -1
        self.trump_suit = None
        self.current_trick = []
        self.trick_starter = -1
        self.turn_idx = -1
        self.message = "Bidding Phase"
        self.waiting_for_animation = False
        
        self.players[self.current_bidder_idx].status = "THINKING"

    def animate_deal(self):
        # Spacing increased to 55 for player
        hand_spacing = 55
        for i, p in enumerate(self.players):
            if i == 0: 
                start_x = (SCREEN_WIDTH - (13 * hand_spacing)) // 2
                for j, c in enumerate(p.hand):
                    c.move_to(start_x + j * hand_spacing, SCREEN_HEIGHT - 120)
            elif i == 1:
                for j, c in enumerate(p.hand):
                    c.move_to(SCREEN_WIDTH - 80, 100 + j * 15)
            elif i == 2:
                for j, c in enumerate(p.hand):
                    c.move_to(300 + j * 20, 20)
            elif i == 3:
                for j, c in enumerate(p.hand):
                    c.move_to(20, 100 + j * 15)

    def get_valid_moves(self, hand, lead_suit):
        if not lead_suit: return hand
        follows = [c for c in hand if c.suit == lead_suit]
        return follows if follows else hand

    def bot_make_bid(self, player):
        score = 0
        for suit in SUITS:
            count = sum(1 for c in player.hand if c.suit == suit)
            highs = sum(1 for c in player.hand if c.suit == suit and c.rank >= 11)
            score = max(score, count + highs)
        
        target = 0
        if score >= 9: target = 9
        elif score >= 8: target = 8
        elif score >= 6: target = 7
        
        if target > self.highest_bid: return target
        return 0
    
    def process_bidding(self):
        if all(p.status == "PASS" for p in self.players):
            self.message = "Everyone Passed! Re-shuffling..."
            self.draw_scene()       # Force a frame render so we see the message
            pygame.display.flip()
            pygame.time.delay(2000) # Wait 2 seconds so players realize what happened
            
            # Move the deal to the next player and reset
            self.dealer_idx = (self.dealer_idx + 1) % 4
            self.reset_round()
            return
        # ------------------------------------------

        curr_p = self.players[self.current_bidder_idx]
        
        # Count active bidders (players who haven't passed)
        active = [p for p in self.players if p.status != "PASS"]
        
        curr_p = self.players[self.current_bidder_idx]
        
        # Count active bidders
        active = [p for p in self.players if p.status != "PASS"]
        
        # Logic: If only one person left and bid is > 6, they win
        if len(active) == 1 and self.highest_bid > 6:
            self.bid_winner = active[0].id
            self.message = f"{active[0].name} wins bid with {self.highest_bid}!"
            
            # Clear statuses for play phase
            for p in self.players: p.status = "" 
            
            if active[0].is_bot:
                suit_counts = {s: sum(1 for c in active[0].hand if c.suit == s) for s in SUITS}
                self.trump_suit = max(suit_counts, key=suit_counts.get)
                self.start_play_phase(self.bid_winner)
            else:
                self.state = STATE_CHOOSE_TRUMP
            return

        # If Bot Turn
        if curr_p.is_bot and curr_p.status != "PASS":
            curr_p.status = "THINKING..."
            self.draw_scene() # Force redraw to show thinking
            pygame.display.flip()
            pygame.time.wait(500) 
            
            bid = self.bot_make_bid(curr_p)
            if bid > self.highest_bid:
                self.highest_bid = bid
                self.bid_winner = curr_p.id
                curr_p.bid_val = bid
                curr_p.status = f"BID: {bid}"
                self.message = f"{curr_p.name} bids {bid}"
            else:
                curr_p.status = "PASS"
                self.message = f"{curr_p.name} passes"
            
            self.current_bidder_idx = (self.current_bidder_idx + 1) % 4

        # If Player Turn (handled in input loop, just update index here if passed)
        elif curr_p.status == "PASS":
             self.current_bidder_idx = (self.current_bidder_idx + 1) % 4
        else:
            # It is human turn, set status to highlight
            if curr_p.status == "WAITING": curr_p.status = "YOUR TURN"

    def start_play_phase(self, winner_id):
        self.state = STATE_PLAYING
        self.trick_starter = winner_id
        self.turn_idx = winner_id
        self.current_trick = []

    def execute_play_card(self, p_idx, card):
        self.players[p_idx].hand.remove(card)
        cx, cy = SCREEN_WIDTH // 2 - CARD_WIDTH // 2, SCREEN_HEIGHT // 2 - CARD_HEIGHT // 2
        offsets = {0: (0, 40), 1: (50, 0), 2: (0, -40), 3: (-50, 0)}
        tx, ty = cx + offsets[p_idx][0], cy + offsets[p_idx][1]
        card.move_to(tx, ty)
        self.current_trick.append((p_idx, card))
        self.state = STATE_ANIMATING

    def evaluate_trick(self):
        winner_idx = self.current_trick[0][0]
        lead_suit = self.current_trick[0][1].suit
        best_card = self.current_trick[0][1]

        for p_idx, card in self.current_trick[1:]:
            if card.suit == self.trump_suit:
                if best_card.suit != self.trump_suit:
                    best_card = card
                    winner_idx = p_idx
                elif card.rank > best_card.rank:
                    best_card = card
                    winner_idx = p_idx
            elif card.suit == lead_suit:
                if best_card.suit == lead_suit and card.rank > best_card.rank:
                    best_card = card
                    winner_idx = p_idx

        self.players[winner_idx].tricks_won += 1
        self.trick_starter = winner_idx
        self.turn_idx = winner_idx
        self.current_trick = []
        
        if len(self.players[0].hand) == 0:
            self.calculate_scores()
            self.state = STATE_ROUND_END

    def calculate_scores(self):
        team_a_tricks = self.players[0].tricks_won + self.players[2].tricks_won
        team_b_tricks = self.players[1].tricks_won + self.players[3].tricks_won
        bidder_team = 'A' if self.bid_winner in [0, 2] else 'B'
        
        if bidder_team == 'A':
            if team_a_tricks >= self.highest_bid:
                self.team_a_score += team_a_tricks
                self.message = f"Team A Won! (+{team_a_tricks})"
            else:
                self.team_a_score -= self.highest_bid
                self.team_b_score += team_b_tricks
                self.message = f"Team A Failed! (-{self.highest_bid})"
        else:
            if team_b_tricks >= self.highest_bid:
                self.team_b_score += team_b_tricks
                self.message = f"Team B Won! (+{team_b_tricks})"
            else:
                self.team_b_score -= self.highest_bid
                self.team_a_score += team_a_tricks
                self.message = f"Team B Failed! (-{self.highest_bid})"

    def draw_ui(self):
        # Sidebar
        pygame.draw.rect(self.screen, SCORE_BG, (0, 0, 200, 150))
        title = self.font_bold.render("SCOREBOARD", True, GOLD)
        t_a = self.font.render(f"You+Mate: {self.team_a_score}", True, WHITE)
        t_b = self.font.render(f"Bots:        {self.team_b_score}", True, WHITE)
        self.screen.blit(title, (10, 10))
        self.screen.blit(t_a, (10, 40))
        self.screen.blit(t_b, (10, 65))

        # --- Player Status & Trick Counters ---
        for i, p in enumerate(self.players):
            px, py = self.ui_positions[i]
            
            # Status (Bidding)
            if self.state == STATE_BIDDING and p.status:
                s_col = GOLD if "BID" in p.status else (GRAY if "PASS" in p.status else WHITE)
                s_txt = self.font_bold.render(p.status, True, s_col)
                # Position text nicely based on player location
                sx = px - 50 if i == 1 else (px + 20 if i == 3 else px - 30)
                sy = py - 30 if i == 0 else (py + 20 if i == 2 else py)
                self.screen.blit(s_txt, (sx, sy))

            # Trick Counter (Always visible)
            t_col = (100, 255, 100) if p.tricks_won > 0 else (150, 150, 150)
            t_txt = self.font.render(f"Tricks: {p.tricks_won}", True, t_col)
            
            tx = px - 30 if i in [0, 2] else px
            ty = py + 20 if i in [0, 2] else py + 30
            self.screen.blit(t_txt, (tx, ty))


        # Center Message
        info_rect = pygame.draw.rect(self.screen, (0,0,0), (SCREEN_WIDTH//2 - 200, 10, 400, 40), border_radius=10)
        status = self.font.render(self.message, True, GOLD)
        self.screen.blit(status, (SCREEN_WIDTH//2 - status.get_width()//2, 20))
        
        # Current Trump Display
        if self.trump_suit:
            ts_rect = pygame.Rect(SCREEN_WIDTH - 60, 10, 50, 50)
            pygame.draw.rect(self.screen, WHITE, ts_rect, border_radius=5)
            col = SUIT_COLORS[self.trump_suit]
            txt = self.font_big.render(self.trump_suit, True, col)
            self.screen.blit(txt, (ts_rect.x + 10, ts_rect.y + 5))

    def draw_scene(self):
        self.screen.fill(BG_COLOR)
        
        # Hands
        hand_spacing = 55 # Matches animate_deal
        hand_start_x = (SCREEN_WIDTH - (len(self.players[0].hand) * hand_spacing)) // 2
        
        for i, card in enumerate(self.players[0].hand):
            mx, my = pygame.mouse.get_pos()
            y_off = -20 if (card.rect.collidepoint(mx, my) and self.state == STATE_PLAYING and self.turn_idx==0) else 0
            if not card.is_moving:
                card.set_pos(hand_start_x + i * hand_spacing, SCREEN_HEIGHT - 120 + y_off)
            card.draw(self.screen)

        for i in [1, 2, 3]:
            for c in self.players[i].hand:
                c.draw(self.screen, hidden=True)

        for _, card in self.current_trick:
            card.draw(self.screen)
            
        self.draw_ui()

    def run(self):
        running = True
        while running:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                
                # Bidding
                if self.state == STATE_BIDDING and self.current_bidder_idx == 0:
                    if event.type == pygame.KEYDOWN:
                        new_bid = 0
                        if event.key == pygame.K_p:
                            self.players[0].status = "PASS"
                            self.current_bidder_idx = 1
                        elif event.key == pygame.K_UP: new_bid = self.highest_bid + 1
                        elif pygame.K_7 <= event.key <= pygame.K_9: new_bid = int(pygame.key.name(event.key))

                        if new_bid > 0:
                            if new_bid > 13: new_bid = 13
                            if new_bid > self.highest_bid:
                                self.highest_bid = new_bid
                                self.bid_winner = 0
                                self.players[0].bid_val = new_bid
                                self.players[0].status = f"BID: {new_bid}"
                                self.message = f"You bid {new_bid}"
                                self.current_bidder_idx = 1

                # Trump Pick
                if self.state == STATE_CHOOSE_TRUMP:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                         mx, my = pygame.mouse.get_pos()
                         for i, suit in enumerate(SUITS):
                             r = pygame.Rect(350 + i*80, 350, 60, 60)
                             if r.collidepoint(mx, my):
                                 self.trump_suit = suit
                                 self.start_play_phase(0)

                # Play
                if self.state == STATE_PLAYING and self.turn_idx == 0:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mx, my = pygame.mouse.get_pos()
                        lead = self.current_trick[0][1].suit if self.current_trick else None
                        valid = self.get_valid_moves(self.players[0].hand, lead)
                        for card in reversed(self.players[0].hand): # Check top card first
                            if card.rect.collidepoint(mx, my) and card in valid:
                                self.execute_play_card(0, card)
                                self.turn_idx = 1
                                break
                
                # Round End
                if self.state == STATE_ROUND_END:
                    if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                        self.dealer_idx = (self.dealer_idx + 1) % 4
                        self.reset_round()

            # Logic
            any_moving = False
            for p in self.players:
                for c in p.hand:
                    if c.update(): any_moving = True
            for _, c in self.current_trick:
                if c.update(): any_moving = True
            
            if self.state == STATE_BIDDING and not any_moving:
                self.process_bidding()

            if self.state == STATE_ANIMATING and not any_moving:
                if len(self.current_trick) == 4:
                    pygame.time.delay(1000)
                    self.evaluate_trick()
                    if self.state != STATE_ROUND_END: self.state = STATE_PLAYING
                else:
                    self.state = STATE_PLAYING

            if self.state == STATE_PLAYING and not any_moving:
                if self.players[self.turn_idx].is_bot:
                    if not self.waiting_for_animation:
                        self.start_wait = pygame.time.get_ticks()
                        self.waiting_for_animation = True
                    if pygame.time.get_ticks() - self.start_wait > 800:
                        card = self.bot_play_card(self.players[self.turn_idx])
                        self.execute_play_card(self.turn_idx, card)
                        self.turn_idx = (self.turn_idx + 1) % 4
                        self.waiting_for_animation = False

            # Draw
            self.draw_scene()

            # Overlays
            if self.state == STATE_CHOOSE_TRUMP:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                self.screen.blit(overlay, (0,0))
                txt = self.font_bold.render("PICK TRUMP", True, WHITE)
                self.screen.blit(txt, (SCREEN_WIDTH//2 - 50, 300))
                for i, suit in enumerate(SUITS):
                    r = pygame.Rect(350 + i*80, 350, 60, 60)
                    pygame.draw.rect(self.screen, WHITE, r, border_radius=8)
                    col = SUIT_COLORS[suit]
                    t = self.font_big.render(suit, True, col)
                    self.screen.blit(t, (r.x + 18, r.y + 10))

            if self.state == STATE_ROUND_END:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                self.screen.blit(overlay, (0,0))
                msg = self.font_big.render(self.message, True, GOLD)
                cont = self.font.render("Click to Continue", True, WHITE)
                self.screen.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2, SCREEN_HEIGHT//2 - 50))
                self.screen.blit(cont, (SCREEN_WIDTH//2 - cont.get_width()//2, SCREEN_HEIGHT//2 + 20))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = TarneebGame()
    game.run()