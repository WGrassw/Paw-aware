import pygame
import time
import random
from sys import exit

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((1200, 800))
pygame.display.set_caption('Runner')

import characteranimation
import healthbar
import dogminigame

print('hello')

# HOW MANY SCENES TOTAL (EASY TO EXPAND)
NUM_SCENES = 3   # scenes: 1, 2, 3 looping in a circle

# LOAD ASSETS
background1 = pygame.image.load('lobbybackground1.jpg').convert_alpha()
food_minigame = pygame.image.load('food or poison minigame symbol.png').convert_alpha()

background2 = pygame.image.load('lobbybackground2.jpg').convert_alpha()
threat_minigame_base = pygame.image.load('threat minigame symbol.png').convert_alpha()

background3 = pygame.image.load('lobbybackground3.jpg').convert_alpha()

# GAME STATE
currentscene = 2
health = 9                 # can now be float (half-hearts supported)
dog_level = 1

last_player_x = characteranimation.player_x

# Threat mini-game trigger settings
THREAT_X = 435
THREAT_Y = 430
THREAT_W, THREAT_H = threat_minigame_base.get_size()

threat_available = True        # allowed to trigger again
threat_triggered = False       # currently running suspense/animation
threat_minigame_started = False
threat_anim_start = 0          # timestamp for suspense & growth

# Animation timing
THREAT_DELAY = 2000            # 2 seconds before enlarging
THREAT_GROW_DURATION = 850     # animation length (ms)


# MAIN LOOP
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    keys = pygame.key.get_pressed()

    # Player can always move (even during suspense), but cannot change scenes mid-animation
    characteranimation.update_character_logic(keys)

    # ----------------------------------------
    # SCENE DRAW
    # ----------------------------------------
    if currentscene == 1:
        screen.blit(background1, (0, 0))
        screen.blit(food_minigame, (435, 450))

    elif currentscene == 2:
        screen.blit(background2, (0, 0))

        # If minigame sequence is triggered
        if threat_triggered:
            now = pygame.time.get_ticks()
            elapsed = now - threat_anim_start

            # Phase 1: Suspense for 2 seconds
            if elapsed < THREAT_DELAY:
                screen.blit(threat_minigame_base, (THREAT_X, THREAT_Y))

            # Phase 2: Grow animation
            else:
                t = min(1.0, (elapsed - THREAT_DELAY) / THREAT_GROW_DURATION)
                eased_t = 1 - (1 - t) ** 2

                target_w, target_h = 1400, 1000
                start_w, start_h = THREAT_W, THREAT_H

                cur_w = int(start_w + (target_w - start_w) * eased_t)
                cur_h = int(start_h + (target_h - start_h) * eased_t)

                scaled = pygame.transform.smoothscale(threat_minigame_base, (cur_w, cur_h))

                center_x = THREAT_X + THREAT_W // 2
                center_y = THREAT_Y + THREAT_H // 2

                rect = scaled.get_rect(center=(center_x, center_y))
                screen.blit(scaled, rect)

                # When animation finishes → start minigame
                if t >= 1.0 and not threat_minigame_started:
                    threat_minigame_started = True

                    # stop walking sounds
                    pygame.mixer.stop()

                    result = dogminigame.run_dog_minigame(dog_level)

                    # HANDLE RESULTS
                    if result == "win":
                        dog_level += 1

                    elif result == "lose_thief":
                        health -= 0.5
                        if health < 0:
                            health = 0

                    elif result == "lose":
                        health -= 1
                        if health < 0:
                            health = 0

                    # RETURN TO LOBBY NORMAL STATE
                    threat_triggered = False
                    threat_anim_start = 0
                    # allow trigger only after moving away
                    threat_available = False

                    # recreate screen surface (pygame requirement after sub-game)
                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption('Runner')

    elif currentscene == 3:
        # 🔸 New scene after the first one (you can add more props here later)
        screen.blit(background3, (0, 0))
        # e.g. later: screen.blit(some_icon, (x, y))

    # ----------------------------------------
    # SCENE SWITCHING (BLOCKED DURING THREAT SEQUENCE)
    # ----------------------------------------
    if not threat_triggered:     # only allow normal scene transitions
        # Move to the next scene when crossing the right edge
        if characteranimation.player_x >= 900:
            # scenes: 1..NUM_SCENES, loop around
            currentscene = (currentscene % NUM_SCENES) + 1
            characteranimation.player_x = 0

        # Move to the previous scene when crossing the left edge
        elif characteranimation.player_x <= 0:
            # Python modulo trick to wrap backward:
            # e.g., from 1 goes to NUM_SCENES
            currentscene = (currentscene - 2) % NUM_SCENES + 1
            characteranimation.player_x = 900

    # ----------------------------------------
    # THREAT MINIGAME TRIGGER (BIDIRECTIONAL)
    # ----------------------------------------
    player_x = characteranimation.player_x

    if currentscene == 2 and not threat_triggered and threat_available:
        zone_left = THREAT_X
        zone_right = THREAT_X + THREAT_W

        # Crossing detection from left → right or right → left
        crossed = (
            (last_player_x < zone_left and player_x >= zone_left) or
            (last_player_x > zone_right and player_x <= zone_right)
        )

        if crossed:
            if random.random() < 0.20:    # 20% chance
                threat_triggered = True
                threat_anim_start = pygame.time.get_ticks()
                threat_minigame_started = False

    # ----------------------------------------
    # RE-ENABLE THREAT TRIGGER ONLY AFTER LEAVING THE AREA
    # ----------------------------------------
    if not threat_available and not threat_triggered:
        if abs(player_x - THREAT_X) > 220:
            threat_available = True

    last_player_x = player_x

    # ----------------------------------------
    # DRAW PLAYER & HEALTHBAR
    # ----------------------------------------
    characteranimation.draw_character(screen)
    healthbar.draw_healthbar(screen, health)

    pygame.display.update()
    clock.tick(characteranimation.current_FPS)
