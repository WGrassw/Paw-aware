import pygame
import random
from sys import exit
import importlib.util
import os

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((1200, 800))
pygame.display.set_caption("Runner")

import characteranimation
import healthbar
import dogminigame
import maze_minigame

# =========================
# LOAD Match-Three minigame module
# =========================
def load_match3_module():
    filename = "candy crush minigame.py"
    path = os.path.join(os.path.dirname(__file__), filename)
    spec = importlib.util.spec_from_file_location("candy_crush_minigame", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

match3_minigame = load_match3_module()

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

dog_level = 1
maze_level = 1
match3_level = 1

# -------------------------
# QUEST SYSTEM
# -------------------------
quest_font = pygame.font.SysFont(None, 26)
quest_title_font = pygame.font.SysFont(None, 28)

QUEST_MARGIN = 18
QUEST_BOX_PAD_X = 14
QUEST_BOX_PAD_Y = 12
QUEST_LINE_GAP = 8

WHITE = (235, 235, 235)
TITLE_WHITE = (245, 245, 245)
GREEN = (120, 255, 120)

quest_phase = 0
quest_level = 1

visited_scenes = set()
visited_scenes.add(currentscene)

def maze_cleared_level():
    return max(0, int(maze_level) - 1)

def dog_cleared_level():
    return max(0, int(dog_level) - 1)

def match3_cleared_level():
    return max(0, int(match3_level) - 1)

def update_explore_all_scenes_quest():
    global quest_phase
    if quest_phase == 0 and len(visited_scenes) >= NUM_SCENES:
        quest_phase = 1

def sync_dual_quest_progress():
    global quest_level
    if quest_phase != 1:
        return
    while quest_level <= min(maze_cleared_level(), dog_cleared_level(), match3_cleared_level()):
        quest_level += 1

def draw_quests(surface):
    title = "Quests"
    title_surf = quest_title_font.render(title, True, TITLE_WHITE)

    lines = []
    colors = []

    if quest_phase == 0:
        lines.append("-- Explore all scenes")
        colors.append(WHITE)
    else:
        m_done = (maze_cleared_level() >= quest_level)
        d_done = (dog_cleared_level() >= quest_level)
        c_done = (match3_cleared_level() >= quest_level)

        lines.append(f"-- Complete Level {quest_level} of Maze")
        colors.append(GREEN if m_done else WHITE)

        lines.append(f"-- Complete Level {quest_level} of Dog")
        colors.append(GREEN if d_done else WHITE)

        lines.append(f"-- Complete Level {quest_level} of Match-Three")
        colors.append(GREEN if c_done else WHITE)

    line_surfs = [quest_font.render(lines[i], True, colors[i]) for i in range(len(lines))]

    max_w = title_surf.get_width()
    for s in line_surfs:
        if s.get_width() > max_w:
            max_w = s.get_width()

    box_w = max_w + QUEST_BOX_PAD_X * 2
    box_h = QUEST_BOX_PAD_Y * 2 + title_surf.get_height() + 10
    for s in line_surfs:
        box_h += s.get_height() + QUEST_LINE_GAP
    box_h -= QUEST_LINE_GAP

    box_x = surface.get_width() - QUEST_MARGIN - box_w
    box_y = QUEST_MARGIN

    box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    box.fill((0, 0, 0, 120))
    surface.blit(box, (box_x, box_y))

    pygame.draw.line(surface, (240, 240, 240), (box_x, box_y), (box_x + box_w, box_y), 2)

    x = box_x + QUEST_BOX_PAD_X
    y = box_y + QUEST_BOX_PAD_Y
    surface.blit(title_surf, (x, y))
    y += title_surf.get_height() + 10

    for s in line_surfs:
        surface.blit(s, (x, y))
        y += s.get_height() + QUEST_LINE_GAP


# ============================================================
# SWITCHED SCENES:
# - Scene 1 now triggers Match-Three (food icon)
# - Scene 2 now triggers Dog (threat icon)
# - Scene 3 stays Maze
# ============================================================

# -------------------------
# Match-Three encounter (Scene 1 ONLY) - uses food icon
# -------------------------
MATCH3_X = 435
MATCH3_Y = 450
match3_icon = food_minigame
MATCH3_W, MATCH3_H = match3_icon.get_size()

match3_triggered = False
match3_started = False
match3_anim_start = 0

MATCH3_DELAY = 2000
MATCH3_GROW_DURATION = 850
MATCH3_TRIGGER_CHANCE_ON_ENTRY = 0.30

match3_rolled_this_visit = False
match3_cleared_this_visit = False

# -------------------------
# DOG encounter (Scene 2 ONLY) - uses threat icon
# -------------------------
DOG_X = 435
DOG_Y = 430
DOG_W, DOG_H = threat_minigame_base.get_size()

dog_triggered = False
dog_started = False
dog_anim_start = 0

DOG_DELAY = 2000
DOG_GROW_DURATION = 850
DOG_TRIGGER_CHANCE_ON_ENTRY = 0.20

dog_rolled_this_visit = False
dog_cleared_this_visit = False

# -------------------------
# Maze (Scene 3 ONLY)
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
    health = max(0, health)

def apply_full_heart_damage():
    global health
    health -= 1
    clamp_health()

def begin_match3_sequence():
    global match3_triggered, match3_anim_start, match3_started
    global return_scene, return_player_x

    match3_triggered = True
    match3_started = False
    match3_anim_start = pygame.time.get_ticks()

    return_scene = currentscene
    return_player_x = characteranimation.player_x

def begin_dog_sequence():
    global dog_triggered, dog_anim_start, dog_started
    global return_scene, return_player_x

    dog_triggered = True
    dog_started = False
    dog_anim_start = pygame.time.get_ticks()

    return_scene = currentscene
    return_player_x = characteranimation.player_x

def begin_maze_sequence():
    global maze_triggered, maze_anim_start, maze_started
    global return_scene, return_player_x

    maze_triggered = True
    maze_started = False
    maze_anim_start = pygame.time.get_ticks()

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

    # Scene switching is LOCKED while any encounter is active/enlarging
    can_switch = (
        not dog_triggered
        and not match3_triggered
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
        visited_scenes.add(currentscene)
        update_explore_all_scenes_quest()

        # Reset per-visit flags on leaving scenes
        if prev_scene == 1:
            match3_rolled_this_visit = False
            match3_cleared_this_visit = False

        if prev_scene == 2:
            dog_rolled_this_visit = False
            dog_cleared_this_visit = False

        if prev_scene == 3:
            maze_rolled_this_visit = False
            maze_cleared_this_visit = False

        # Roll encounters ONLY in their intended scene
        if currentscene == 1 and not match3_rolled_this_visit and not match3_cleared_this_visit:
            match3_rolled_this_visit = True
            if random.random() < MATCH3_TRIGGER_CHANCE_ON_ENTRY:
                begin_match3_sequence()

        if currentscene == 2 and not dog_rolled_this_visit and not dog_cleared_this_visit:
            dog_rolled_this_visit = True
            if random.random() < DOG_TRIGGER_CHANCE_ON_ENTRY:
                begin_dog_sequence()

        if currentscene == 3 and not maze_rolled_this_visit and not maze_cleared_this_visit:
            maze_rolled_this_visit = True
            if random.random() < MAZE_TRIGGER_CHANCE_ON_ENTRY:
                begin_maze_sequence()

        prev_scene = currentscene

    sync_dual_quest_progress()

    # =========================
    # DRAW SCENES
    # =========================
    if currentscene == 1:
        screen.blit(background1, (0, 0))

        # Match-Three encounter appears/enlarges ONLY in background1 now
        if match3_triggered and not match3_cleared_this_visit:
            elapsed = now_ms - match3_anim_start

            if elapsed < MATCH3_DELAY:
                screen.blit(match3_icon, (MATCH3_X, MATCH3_Y))

            elif elapsed < MATCH3_DELAY + MATCH3_GROW_DURATION:
                t = (elapsed - MATCH3_DELAY) / MATCH3_GROW_DURATION
                t = max(0.0, min(1.0, t))
                t = 1 - (1 - t) ** 2

                cur_w = int(MATCH3_W + (1400 - MATCH3_W) * t)
                cur_h = int(MATCH3_H + (1000 - MATCH3_H) * t)

                scaled = pygame.transform.smoothscale(match3_icon, (cur_w, cur_h))
                rect = scaled.get_rect(center=(MATCH3_X + MATCH3_W // 2, MATCH3_Y + MATCH3_H // 2))
                screen.blit(scaled, rect)

            else:
                if not match3_started:
                    match3_started = True
                    pygame.mixer.stop()

                    result = match3_minigame.run_match3_minigame(match3_level)

                    if result == "win":
                        match3_level += 1
                    else:
                        apply_full_heart_damage()

                    match3_cleared_this_visit = True
                    match3_triggered = False
                    match3_started = False
                    restore_player_position_after_minigame()

                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption("Runner")

    elif currentscene == 2:
        screen.blit(background2, (0, 0))

        # Dog encounter appears/enlarges ONLY in background2 now
        if dog_triggered and not dog_cleared_this_visit:
            elapsed = now_ms - dog_anim_start

            if elapsed < DOG_DELAY:
                screen.blit(threat_minigame_base, (DOG_X, DOG_Y))

            elif elapsed < DOG_DELAY + DOG_GROW_DURATION:
                t = (elapsed - DOG_DELAY) / DOG_GROW_DURATION
                t = max(0.0, min(1.0, t))
                t = 1 - (1 - t) ** 2

                cur_w = int(DOG_W + (1400 - DOG_W) * t)
                cur_h = int(DOG_H + (1000 - DOG_H) * t)

                scaled = pygame.transform.smoothscale(threat_minigame_base, (cur_w, cur_h))
                rect = scaled.get_rect(center=(DOG_X + DOG_W // 2, DOG_Y + DOG_H // 2))
                screen.blit(scaled, rect)

            else:
                if not dog_started:
                    dog_started = True
                    pygame.mixer.stop()

                    result = dogminigame.run_dog_minigame(dog_level)

                    if result == "win":
                        dog_level += 1
                    else:
                        apply_full_heart_damage()

                    dog_cleared_this_visit = True
                    dog_triggered = False
                    dog_started = False
                    restore_player_position_after_minigame()

                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption("Runner")

    elif currentscene == 3:
        screen.blit(background3, (0, 0))

        if maze_triggered and not maze_cleared_this_visit:
            elapsed = now_ms - maze_anim_start

            if elapsed < MAZE_DELAY:
                screen.blit(maze_icon, (MAZE_X, MAZE_Y))

            elif elapsed < MAZE_DELAY + MAZE_GROW_DURATION:
                t = (elapsed - MAZE_DELAY) / MAZE_GROW_DURATION
                t = max(0.0, min(1.0, t))
                t = 1 - (1 - t) ** 2

                cur_w = int(MAZE_W + (1400 - MAZE_W) * t)
                cur_h = int(MAZE_H + (1000 - MAZE_H) * t)

                scaled = pygame.transform.smoothscale(maze_icon, (cur_w, cur_h))
                rect = scaled.get_rect(center=(MAZE_X + MAZE_W // 2, MAZE_Y + MAZE_H // 2))
                screen.blit(scaled, rect)

            else:
                if not maze_started:
                    maze_started = True
                    pygame.mixer.stop()

                    result = maze_minigame.run_maze_minigame(
                        window_size=(1200, 800),
                        caption="Maze Minigame",
                        level=maze_level
                    )

                    if result == "win":
                        maze_level += 1
                    else:
                        apply_full_heart_damage()

                    maze_cleared_this_visit = True
                    maze_triggered = False
                    maze_started = False
                    restore_player_position_after_minigame()

                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption("Runner")

    sync_dual_quest_progress()

    characteranimation.draw_character(screen)
    healthbar.draw_healthbar(screen, health)
    draw_quests(screen)

    pygame.display.update()
    clock.tick(characteranimation.current_FPS)
