import pygame
import time
import random
from sys import exit

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((1200,800))
pygame.display.set_caption('Runner')
def play_catch_fish(screen, duration=60, *, sprinter=False, sprint_multiplier=1.8):
    """
    Mini-game: Catch Fish, Avoid Trash/Poison.
    Returns: dict summary after the game ends or ESC pressed.
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()

    # ---------- Tunables ----------
    BASE_SPEED = 360
    PLAYER_W, PLAYER_H = 80, 24
    ITEM_W, ITEM_H = 36, 28
    START_SPAWN_EVERY = 650
    MIN_SPAWN_EVERY   = 260
    SPEED_UP_EVERY    = 7.0
    FALL_SPEED        = (160, 260)
    HEALTH_MAX        = 100
    TRASH_DAMAGE      = 15
    POISON_DAMAGE     = 28
    FISH_SCORE        = 10
    POISON_COLOR      = (120, 30, 180)
    TRASH_COLOR       = (90, 90, 90)
    FISH_COLOR        = (30, 160, 210)
    BG_TOP            = (223, 242, 255)
    BG_BOTTOM         = (183, 219, 255)
    HUD_COLOR         = (20, 35, 50)

    EDU_FACTS = [
        "Stray cats often eat discarded food. Spoilage and toxins can cause severe illness.",
        "Food scarcity increases risk of starvation, especially for young or injured strays.",
        "Feeding street cats safe, fresh food reduces poisoning incidents and malnutrition.",
    ]

    # ---------- Helpers ----------
    def vgradient(surf, c0, c1):
        w, h = surf.get_size()
        for y in range(h):
            t = y / (h - 1 if h > 1 else 1)
            r = int(c0[0]*(1-t) + c1[0]*t)
            g = int(c0[1]*(1-t) + c1[1]*t)
            b = int(c0[2]*(1-t) + c1[2]*t)
            pygame.draw.line(surf, (r,g,b), (0,y), (w,y))

    def draw_health_bar(surf, x, y, w, h, pct):
        pct = max(0, min(1, pct))
        bg = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surf, (220, 232, 240), bg, border_radius=8)
        inner = pygame.Rect(x+2, y+2, int((w-4)*pct), h-4)
        col = (50, 200, 90) if pct > 0.5 else (240, 185, 40) if pct > 0.25 else (220, 60, 60)
        pygame.draw.rect(surf, col, inner, border_radius=6)
        pygame.draw.rect(surf, (40, 60, 80), bg, 2, border_radius=8)

    class Player:
        def __init__(self):
            self.rect = pygame.Rect((W//2 - PLAYER_W//2, H-64), (PLAYER_W, PLAYER_H))
            self.speed = BASE_SPEED
            self.sprint_multiplier = sprint_multiplier if sprinter else 1.0

        def update(self, dt, keys):
            spd = self.speed * (self.sprint_multiplier if keys[pygame.K_LSHIFT] else 1.0)
            dx = ((1 if keys[pygame.K_RIGHT] or keys[pygame.K_d] else 0) -
                  (1 if keys[pygame.K_LEFT]  or keys[pygame.K_a] else 0)) * spd * dt
            self.rect.x += int(dx)
            self.rect.clamp_ip(pygame.Rect(0, 0, W, H))

        def draw(self, surf):
            pygame.draw.rect(surf, (30, 30, 30), self.rect, border_radius=12)
            inner = self.rect.inflate(-8, -8)
            pygame.draw.rect(surf, (240, 240, 240), inner, border_radius=10)

    class Item:
        def __init__(self, kind):
            self.kind = kind
            self.rect = pygame.Rect(random.randint(16, W-16-ITEM_W), -ITEM_H, ITEM_W, ITEM_H)
            if kind == "fish":
                self.vy = random.randint(*FALL_SPEED)
            elif kind == "trash":
                self.vy = random.randint(FALL_SPEED[0]+20, FALL_SPEED[1]+40)
            else:
                self.vy = random.randint(FALL_SPEED[0]+40, FALL_SPEED[1]+70)

        def update(self, dt):
            self.rect.y += int(self.vy * dt)

        def offscreen(self):
            return self.rect.top > H + 20

        def draw(self, surf):
            if self.kind == "fish":
                body = self.rect.copy()
                pygame.draw.ellipse(surf, FISH_COLOR, body)
                tail = pygame.Rect(self.rect.right-10, self.rect.y+6, 16, self.rect.h-12)
                pygame.draw.polygon(surf, FISH_COLOR, [
                    (tail.left, tail.centery),
                    (tail.right, tail.top),
                    (tail.right, tail.bottom)
                ])
                eye = pygame.Rect(self.rect.x+8, self.rect.y+8, 5, 5)
                pygame.draw.ellipse(surf, (250,250,250), eye)
                pygame.draw.circle(surf, (20,20,20), eye.center, 2)
            elif self.kind == "trash":
                pygame.draw.rect(surf, TRASH_COLOR, self.rect, border_radius=6)
                pygame.draw.rect(surf, (200,200,200), self.rect.inflate(-10,-10), 2, border_radius=6)
            else:
                pygame.draw.rect(surf, POISON_COLOR, self.rect, border_radius=8)
                skull = self.rect.inflate(-14, -10)
                pygame.draw.ellipse(surf, (240,240,240), skull.move(0, -4))
                pygame.draw.rect(surf, (240,240,240), skull.move(0, 4))
                pygame.draw.circle(surf, (20,20,20), (skull.centerx-6, skull.centery-6), 3)
                pygame.draw.circle(surf, (20,20,20), (skull.centerx+6, skull.centery-6), 3)

    # ---------- State ----------
    player = Player()
    items = []
    score = 0
    health = HEALTH_MAX
    fish_caught = 0
    trash_hit = 0
    poison_hit = 0

    start_ms = pygame.time.get_ticks()
    next_spawn_ms = start_ms + START_SPAWN_EVERY
    spawn_every = START_SPAWN_EVERY
    last_speedup_t = 0.0

    title_font = pygame.font.Font(None, 38)
    hud_font   = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 22)

    # ---------- Loop ----------
    running = True
    game_over = False
    fact_alpha = 0
    chosen_fact = random.choice(EDU_FACTS)
    return_button = None

    while running:
        dt = clock.tick(60) / 1000.0
        now = pygame.time.get_ticks()
        elapsed = (now - start_ms) / 1000.0
        remaining = max(0, duration - elapsed)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

            # handle Return button click
            if game_over and return_button and event.type == pygame.MOUSEBUTTONDOWN:
                if return_button.collidepoint(event.pos):
                    running = False

        vgradient(screen, BG_TOP, BG_BOTTOM)

        if not game_over:
            if elapsed - last_speedup_t >= SPEED_UP_EVERY:
                last_speedup_t = elapsed
                spawn_every = max(MIN_SPAWN_EVERY, int(spawn_every * 0.9))

            if now >= next_spawn_ms:
                r = random.random()
                kind = "fish" if r < 0.60 else ("trash" if r < 0.88 else "poison")
                items.append(Item(kind))
                next_spawn_ms = now + spawn_every

            keys = pygame.key.get_pressed()
            player.update(dt, keys)

            for it in items:
                it.update(dt)

            keep = []
            for it in items:
                if player.rect.colliderect(it.rect):
                    if it.kind == "fish":
                        score += FISH_SCORE
                        fish_caught += 1
                    elif it.kind == "trash":
                        health -= TRASH_DAMAGE
                        trash_hit += 1
                    else:
                        health -= POISON_DAMAGE
                        poison_hit += 1
                else:
                    if not it.offscreen():
                        keep.append(it)
            items = keep

            if health <= 0 or remaining <= 0:
                game_over = True

        for it in items: it.draw(screen)
        player.draw(screen)

        draw_health_bar(screen, 18, 16, 200, 18, health/HEALTH_MAX)
        score_label = hud_font.render(f"Score: {score}", True, HUD_COLOR)
        time_label  = hud_font.render(f"Time: {int(remaining) if not game_over else 0}s", True, HUD_COLOR)
        screen.blit(score_label, (W - score_label.get_width() - 18, 14))
        screen.blit(time_label, (W - time_label.get_width() - 18, 40))

        # Game over overlay
        if game_over:
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))

            box = pygame.Rect(W//2 - 320, H//2 - 160, 640, 320)
            pygame.draw.rect(screen, (245, 248, 252), box, border_radius=16)
            pygame.draw.rect(screen, (40, 60, 90), box, 3, border_radius=16)

            title = title_font.render("Round Complete!", True, (25, 40, 70))
            screen.blit(title, title.get_rect(center=(W//2, box.top + 36)))

            s1 = hud_font.render(f"Fish caught: {fish_caught}", True, (40,50,70))
            s2 = hud_font.render(f"Trash hit: {trash_hit}", True, (40,50,70))
            s3 = hud_font.render(f"Poison hit: {poison_hit}", True, (40,50,70))
            s4 = hud_font.render(f"Score: {score}", True, (40,50,70))
            screen.blit(s1, s1.get_rect(center=(W//2, box.top + 88)))
            screen.blit(s2, s2.get_rect(center=(W//2, box.top + 118)))
            screen.blit(s3, s3.get_rect(center=(W//2, box.top + 148)))
            screen.blit(s4, s4.get_rect(center=(W//2, box.top + 178)))

            fact_alpha = min(255, fact_alpha + int(255 * dt * 1.8))
            fact_surf = small_font.render(chosen_fact, True, (20,30,50))
            fact_bg = pygame.Surface((fact_surf.get_width()+24, fact_surf.get_height()+16), pygame.SRCALPHA)
            fact_bg.fill((255,255,255, 230))
            fact_bg.set_alpha(fact_alpha)
            screen.blit(fact_bg, fact_bg.get_rect(center=(W//2, box.bottom - 60)))
            fact_surf.set_alpha(fact_alpha)
            screen.blit(fact_surf, fact_surf.get_rect(center=(W//2, box.bottom - 60)))

            # --- Return Button ---
            return_button = pygame.Rect(W//2 - 100, box.bottom - 50, 200, 40)
            mouse = pygame.mouse.get_pos()
            color = (90, 150, 255) if return_button.collidepoint(mouse) else (60, 110, 200)
            pygame.draw.rect(screen, color, return_button, border_radius=12)
            pygame.draw.rect(screen, (255,255,255), return_button, 2, border_radius=12)
            btn_text = small_font.render("Return", True, (255,255,255))
            screen.blit(btn_text, btn_text.get_rect(center=return_button.center))

        pygame.display.flip()

    return {
        "score": score,
        "fish_caught": fish_caught,
        "trash_hit": trash_hit,
        "poison_hit": poison_hit,
        "duration": min(duration, int(elapsed)),
        "fact": chosen_fact
    }
