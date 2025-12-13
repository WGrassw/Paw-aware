import pygame
import random
from sys import exit

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((1200, 800))
pygame.display.set_caption("Runner")

import characteranimation
import healthbar
import dogminigame
import maze_minigame

# HOW MANY SCENES TOTAL
NUM_SCENES = 3

# LOAD ASSETS
background1 = pygame.image.load("lobbybackground1.jpg").convert_alpha()
food_minigame = pygame.image.load("food or poison minigame symbol.png").convert_alpha()

background2 = pygame.image.load("lobbybackground2.jpg").convert_alpha()
threat_minigame_base = pygame.image.load("threat minigame symbol.png").convert_alpha()

background3 = pygame.image.load("lobbybackground3.jpg").convert_alpha()
maze_icon = pygame.image.load("maze_symbol.png").convert_alpha()

# GAME STATE
currentscene = 2
prev_scene = currentscene

# Health is ALWAYS int
health = 9
pending_half_damage = 0  # kept for future use if needed

dog_level = 1

# -------------------------
# Threat (Scene 2)
# -------------------------
THREAT_X = 435
THREAT_Y = 430
THREAT_W, THREAT_H = threat_minigame_base.get_size()

threat_triggered = False
threat_minigame_started = False
threat_anim_start = 0

THREAT_DELAY = 2000
THREAT_GROW_DURATION = 850
THREAT_TRIGGER_CHANCE_ON_ENTRY = 0.20

threat_rolled_this_visit = False
threat_cleared_this_visit = False

# -------------------------
# Maze (Scene 3)
# -------------------------
MAZE_X = 520
MAZE_Y = 420
MAZE_W, MAZE_H = maze_icon.get_size()

maze_triggered = False
maze_started = False
maze_anim_start = 0

MAZE_DELAY = 2000
MAZE_GROW_DURATION = 850
MAZE_TRIGGER_CHANCE_ON_ENTRY = 0.20

maze_rolled_this_visit = False
maze_cleared_this_visit = False

# -------------------------
# Return positioning
# -------------------------
return_scene = None
return_player_x = None

scene_switch_lock_until_ms = 0
SCENE_SWITCH_LOCK_MS = 220

LEFT_EDGE = 0
RIGHT_EDGE = 900
SAFE_MARGIN = 20


def clamp_health():
    global health
    if health < 0:
        health = 0


def apply_full_heart_damage():
    global health
    health -= 1
    clamp_health()


def begin_threat_sequence():
    global threat_triggered, threat_anim_start, threat_minigame_started
    global return_scene, return_player_x

    threat_triggered = True
    threat_anim_start = pygame.time.get_ticks()
    threat_minigame_started = False

    return_scene = currentscene
    return_player_x = characteranimation.player_x


def begin_maze_sequence():
    global maze_triggered, maze_anim_start, maze_started
    global return_scene, return_player_x

    maze_triggered = True
    maze_anim_start = pygame.time.get_ticks()
    maze_started = False

    return_scene = currentscene
    return_player_x = characteranimation.player_x


def restore_player_position_after_minigame():
    global currentscene, return_scene, return_player_x, prev_scene
    global scene_switch_lock_until_ms

    if return_scene is not None:
        currentscene = return_scene

    if return_player_x is not None:
        x = return_player_x
        if x <= LEFT_EDGE + SAFE_MARGIN:
            x = LEFT_EDGE + SAFE_MARGIN + 1
        elif x >= RIGHT_EDGE - SAFE_MARGIN:
            x = RIGHT_EDGE - SAFE_MARGIN - 1
        characteranimation.player_x = x

    prev_scene = currentscene
    scene_switch_lock_until_ms = pygame.time.get_ticks() + SCENE_SWITCH_LOCK_MS

    return_scene = None
    return_player_x = None


# =========================
# MAIN LOOP
# =========================
while True:
    now_ms = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    keys = pygame.key.get_pressed()
    characteranimation.update_character_logic(keys)

    # Scene switching
    can_switch = (
        not threat_triggered
        and not maze_triggered
        and now_ms >= scene_switch_lock_until_ms
    )

    if can_switch:
        if characteranimation.player_x >= RIGHT_EDGE:
            currentscene = (currentscene % NUM_SCENES) + 1
            characteranimation.player_x = LEFT_EDGE
        elif characteranimation.player_x <= LEFT_EDGE:
            currentscene = (currentscene - 2) % NUM_SCENES + 1
            characteranimation.player_x = RIGHT_EDGE

    # Scene entry logic
    if currentscene != prev_scene:
        if prev_scene == 2:
            threat_rolled_this_visit = False
            threat_cleared_this_visit = False
        if prev_scene == 3:
            maze_rolled_this_visit = False
            maze_cleared_this_visit = False

        if currentscene == 2 and not threat_rolled_this_visit and not threat_cleared_this_visit:
            threat_rolled_this_visit = True
            if random.random() < THREAT_TRIGGER_CHANCE_ON_ENTRY:
                begin_threat_sequence()

        if currentscene == 3 and not maze_rolled_this_visit and not maze_cleared_this_visit:
            maze_rolled_this_visit = True
            if random.random() < MAZE_TRIGGER_CHANCE_ON_ENTRY:
                begin_maze_sequence()

        prev_scene = currentscene

    # =========================
    # DRAW SCENES
    # =========================
    if currentscene == 1:
        screen.blit(background1, (0, 0))
        screen.blit(food_minigame, (435, 450))

    elif currentscene == 2:
        screen.blit(background2, (0, 0))

        if threat_triggered and not threat_cleared_this_visit:
            elapsed = now_ms - threat_anim_start

            if elapsed < THREAT_DELAY:
                screen.blit(threat_minigame_base, (THREAT_X, THREAT_Y))
            else:
                t = min(1.0, (elapsed - THREAT_DELAY) / THREAT_GROW_DURATION)
                t = 1 - (1 - t) ** 2

                cur_w = int(THREAT_W + (1400 - THREAT_W) * t)
                cur_h = int(THREAT_H + (1000 - THREAT_H) * t)

                scaled = pygame.transform.smoothscale(threat_minigame_base, (cur_w, cur_h))
                rect = scaled.get_rect(center=(THREAT_X + THREAT_W // 2, THREAT_Y + THREAT_H // 2))
                screen.blit(scaled, rect)

                if t >= 1.0 and not threat_minigame_started:
                    threat_minigame_started = True
                    pygame.mixer.stop()

                    result = dogminigame.run_dog_minigame(dog_level)

                    if result == "win":
                        dog_level += 1
                    else:
                        apply_full_heart_damage()

                    threat_cleared_this_visit = True
                    threat_triggered = False
                    threat_minigame_started = False
                    restore_player_position_after_minigame()

                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption("Runner")

    elif currentscene == 3:
        screen.blit(background3, (0, 0))

        if maze_triggered and not maze_cleared_this_visit:
            elapsed = now_ms - maze_anim_start

            if elapsed < MAZE_DELAY:
                screen.blit(maze_icon, (MAZE_X, MAZE_Y))
            else:
                t = min(1.0, (elapsed - MAZE_DELAY) / MAZE_GROW_DURATION)
                t = 1 - (1 - t) ** 2

                cur_w = int(MAZE_W + (1400 - MAZE_W) * t)
                cur_h = int(MAZE_H + (1000 - MAZE_H) * t)

                scaled = pygame.transform.smoothscale(maze_icon, (cur_w, cur_h))
                rect = scaled.get_rect(center=(MAZE_X + MAZE_W // 2, MAZE_Y + MAZE_H // 2))
                screen.blit(scaled, rect)

                if t >= 1.0 and not maze_started:
                    maze_started = True
                    pygame.mixer.stop()

                    result = maze_minigame.run_maze_minigame(
                        window_size=(1200, 800),
                        caption="Maze Minigame"
                    )

                    if result != "win":
                        apply_full_heart_damage()

                    maze_cleared_this_visit = True
                    maze_triggered = False
                    maze_started = False
                    restore_player_position_after_minigame()

                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption("Runner")

    # =========================
    # PLAYER + UI
    # =========================
    characteranimation.draw_character(screen)
    healthbar.draw_healthbar(screen, health)

    pygame.display.update()
    clock.tick(characteranimation.current_FPS)
