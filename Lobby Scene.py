# lobby.py
#
# Scenes:
# 1: lobbybackground1 + Match-3 encounter icon (20% chance on entry)
# 2: lobbybackground2 + Dog encounter icon (40% chance on entry)
# 3: lobbybackground3 + Maze encounter icon (20% chance on entry)
# 4: lobbybackground4 + Jumpers encounter icon (card.png) (40% chance on entry)
# 5: lobbybackground5 final scene, ONLY appears when dog, maze, match3 levels are all >= 2
#
# IMPORTANT:
# - While quest_phase == 0 (Explore all available scenes), NO challenges appear at all.
# - After exploring is completed (quest_phase becomes 1), challenges can appear.

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
import jump_charge_minigame  # Jumpers


def load_match3_module():
    filename = "candy crush minigame.py"
    path = os.path.join(os.path.dirname(__file__), filename)
    spec = importlib.util.spec_from_file_location("candy_crush_minigame", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


match3_minigame = load_match3_module()

# LOAD ASSETS
background1 = pygame.image.load("lobbybackground1.jpg").convert_alpha()
food_minigame = pygame.image.load("food or poison minigame symbol.png").convert_alpha()

background2 = pygame.image.load("lobbybackground2.jpg").convert_alpha()
threat_minigame_base = pygame.image.load("threat minigame symbol.png").convert_alpha()

background3 = pygame.image.load("lobbybackground3.jpg").convert_alpha()
maze_icon = pygame.image.load("maze_symbol.png").convert_alpha()

background4 = pygame.image.load("lobbybackground4.jpg").convert_alpha()
card_icon = pygame.image.load("card.png").convert_alpha()

background5 = pygame.image.load("lobbybackground5.jpg").convert_alpha()

# GAME STATE
currentscene = 2
prev_scene = currentscene

# Health is ALWAYS int
health = 9

dog_level = 1
maze_level = 1
match3_level = 1
jump_level = 1  # Jumpers

# QUEST SYSTEM
quest_font = pygame.font.SysFont(None, 26)
quest_title_font = pygame.font.SysFont(None, 28)

QUEST_MARGIN = 18
QUEST_BOX_PAD_X = 14
QUEST_BOX_PAD_Y = 12
QUEST_LINE_GAP = 8

WHITE = (235, 235, 235)
TITLE_WHITE = (245, 245, 245)
GREEN = (120, 255, 120)

quest_phase = 0  # 0 = explore, 1 = challenges allowed + level quests
quest_level = 1

visited_scenes = set()
visited_scenes.add(currentscene)

# Final scene story text
story_font = pygame.font.SysFont(None, 30)
story_font_small = pygame.font.SysFont(None, 24)
STORY_TEXT_COLOR = (245, 245, 245)

LEFT_EDGE = 0
RIGHT_EDGE = 900
SAFE_MARGIN = 20

scene_switch_lock_until_ms = 0
SCENE_SWITCH_LOCK_MS = 220


def clamp_health():
    global health
    health = max(0, health)


def apply_full_heart_damage():
    global health
    health -= 1
    clamp_health()


def is_final_scene_unlocked():
    # Scene 5 unlock condition as requested (only these three)
    return (dog_level >= 2) and (maze_level >= 2) and (match3_level >= 2)


def available_scene_count():
    return 5 if is_final_scene_unlocked() else 4


def next_scene(scene_id: int) -> int:
    n = available_scene_count()
    return (scene_id % n) + 1


def prev_scene_id(scene_id: int) -> int:
    n = available_scene_count()
    return ((scene_id - 2) % n) + 1


def maze_cleared_level():
    return max(0, int(maze_level) - 1)


def dog_cleared_level():
    return max(0, int(dog_level) - 1)


def match3_cleared_level():
    return max(0, int(match3_level) - 1)


def jump_cleared_level():
    return max(0, int(jump_level) - 1)


def update_explore_all_scenes_quest():
    global quest_phase
    if quest_phase != 0:
        return

    needed = set(range(1, available_scene_count() + 1))
    if needed.issubset(visited_scenes):
        quest_phase = 1  # challenges allowed now


def sync_dual_quest_progress():
    global quest_level
    if quest_phase != 1:
        return

    while quest_level <= min(
        maze_cleared_level(),
        dog_cleared_level(),
        match3_cleared_level(),
        jump_cleared_level(),
    ):
        quest_level += 1


def draw_quests(surface):
    title = "Quests"
    title_surf = quest_title_font.render(title, True, TITLE_WHITE)

    lines = []
    colors = []

    if quest_phase == 0:
        lines.append("-- Explore all available scenes")
        colors.append(WHITE)
    else:
        m_done = (maze_cleared_level() >= quest_level)
        d_done = (dog_cleared_level() >= quest_level)
        c_done = (match3_cleared_level() >= quest_level)
        j_done = (jump_cleared_level() >= quest_level)

        lines.append(f"-- Complete Level {quest_level} of Maze")
        colors.append(GREEN if m_done else WHITE)

        lines.append(f"-- Complete Level {quest_level} of Dog")
        colors.append(GREEN if d_done else WHITE)

        lines.append(f"-- Complete Level {quest_level} of Match-Three")
        colors.append(GREEN if c_done else WHITE)

        lines.append(f"-- Complete Level {quest_level} of Jumpers")
        colors.append(GREEN if j_done else WHITE)

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


def wrap_text_lines(text, font, max_width):
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_story_overlay_bottom(surface):
    box_w = 1120
    box_h = 160
    box_x = (surface.get_width() - box_w) // 2
    box_y = surface.get_height() - box_h - 24

    overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (box_x, box_y))
    pygame.draw.rect(surface, (240, 240, 240), (box_x, box_y, box_w, box_h), 2, border_radius=14)

    main_text = (
        "After surviving the streets, the cat can choose to continue to wander the streets "
        "or become a rescue. The choice is yours."
    )

    hint_text = (
        "Progress makes it easier to seek a home. "
        "Complete more levels to weaken the final challenge."
    )

    lines_main = wrap_text_lines(main_text, story_font, box_w - 36)

    y = box_y + 16
    for ln in lines_main[:3]:
        surface.blit(story_font.render(ln, True, STORY_TEXT_COLOR), (box_x + 18, y))
        y += 32

    y += 4
    surface.blit(story_font_small.render(hint_text, True, (220, 220, 220)), (box_x + 18, y))


# Encounter setup

# Scene 1: Match-Three (20%)
MATCH3_X = 435
MATCH3_Y = 450
match3_icon = food_minigame
MATCH3_W, MATCH3_H = match3_icon.get_size()

match3_triggered = False
match3_started = False
match3_anim_start = 0

MATCH3_DELAY = 2000
MATCH3_GROW_DURATION = 850
MATCH3_TRIGGER_CHANCE_ON_ENTRY = 0.20

match3_rolled_this_visit = False
match3_cleared_this_visit = False

# Scene 2: Dog (40%)
DOG_X = 435
DOG_Y = 430
DOG_W, DOG_H = threat_minigame_base.get_size()

dog_triggered = False
dog_started = False
dog_anim_start = 0

DOG_DELAY = 2000
DOG_GROW_DURATION = 850
DOG_TRIGGER_CHANCE_ON_ENTRY = 0.40

dog_rolled_this_visit = False
dog_cleared_this_visit = False

# Scene 3: Maze (20%)
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

# Scene 4: Jumpers (40%) using card.png
JUMP_X = 430
JUMP_Y = 350
JUMP_W, JUMP_H = card_icon.get_size()

jump_triggered = False
jump_started = False
jump_anim_start = 0

JUMP_DELAY = 2000
JUMP_GROW_DURATION = 850
JUMP_TRIGGER_CHANCE_ON_ENTRY = 0.40

jump_rolled_this_visit = False
jump_cleared_this_visit = False

# Return positioning
return_scene = None
return_player_x = None


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


def begin_jump_sequence():
    global jump_triggered, jump_anim_start, jump_started
    global return_scene, return_player_x

    jump_triggered = True
    jump_started = False
    jump_anim_start = pygame.time.get_ticks()

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


# MAIN LOOP
while True:
    now_ms = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    keys = pygame.key.get_pressed()
    characteranimation.update_character_logic(keys)

    can_switch = (
        not dog_triggered
        and not match3_triggered
        and not maze_triggered
        and not jump_triggered
        and now_ms >= scene_switch_lock_until_ms
    )

    if can_switch:
        if characteranimation.player_x >= RIGHT_EDGE:
            currentscene = next_scene(currentscene)
            characteranimation.player_x = LEFT_EDGE
        elif characteranimation.player_x <= LEFT_EDGE:
            currentscene = prev_scene_id(currentscene)
            characteranimation.player_x = RIGHT_EDGE

    if currentscene == 5 and not is_final_scene_unlocked():
        currentscene = 4
        prev_scene = 4
        characteranimation.player_x = RIGHT_EDGE - 1

    if currentscene != prev_scene:
        visited_scenes.add(currentscene)
        update_explore_all_scenes_quest()

        if prev_scene == 1:
            match3_rolled_this_visit = False
            match3_cleared_this_visit = False
        if prev_scene == 2:
            dog_rolled_this_visit = False
            dog_cleared_this_visit = False
        if prev_scene == 3:
            maze_rolled_this_visit = False
            maze_cleared_this_visit = False
        if prev_scene == 4:
            jump_rolled_this_visit = False
            jump_cleared_this_visit = False

        # No challenges during explore phase
        if quest_phase == 1:
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

            if currentscene == 4 and not jump_rolled_this_visit and not jump_cleared_this_visit:
                jump_rolled_this_visit = True
                if random.random() < JUMP_TRIGGER_CHANCE_ON_ENTRY:
                    begin_jump_sequence()

        prev_scene = currentscene

    sync_dual_quest_progress()

    # DRAW SCENES
    if currentscene == 1:
        screen.blit(background1, (0, 0))

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

    elif currentscene == 4:
        screen.blit(background4, (0, 0))

        if jump_triggered and not jump_cleared_this_visit:
            elapsed = now_ms - jump_anim_start

            if elapsed < JUMP_DELAY:
                screen.blit(card_icon, (JUMP_X, JUMP_Y))

            elif elapsed < JUMP_DELAY + JUMP_GROW_DURATION:
                t = (elapsed - JUMP_DELAY) / JUMP_GROW_DURATION
                t = max(0.0, min(1.0, t))
                t = 1 - (1 - t) ** 2

                cur_w = int(JUMP_W + (1400 - JUMP_W) * t)
                cur_h = int(JUMP_H + (1000 - JUMP_H) * t)

                scaled = pygame.transform.smoothscale(card_icon, (cur_w, cur_h))
                rect = scaled.get_rect(center=(JUMP_X + JUMP_W // 2, JUMP_Y + JUMP_H // 2))
                screen.blit(scaled, rect)

            else:
                if not jump_started:
                    jump_started = True
                    pygame.mixer.stop()

                    result = jump_charge_minigame.run_jump_minigame(level=jump_level)

                    if result == "win":
                        jump_level += 1
                    else:
                        # fall, esc, quit all count as lose and cost 1 heart
                        apply_full_heart_damage()

                    jump_cleared_this_visit = True
                    jump_triggered = False
                    jump_started = False
                    restore_player_position_after_minigame()

                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption("Runner")

    elif currentscene == 5:
        screen.blit(background5, (0, 0))
        draw_story_overlay_bottom(screen)

    characteranimation.draw_character(screen)
    healthbar.draw_healthbar(screen, health)
    draw_quests(screen)

    pygame.display.update()
    clock.tick(characteranimation.current_FPS)
