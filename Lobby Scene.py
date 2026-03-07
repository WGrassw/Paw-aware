# lobby.py
#
# Scenes:
# 1: lobbybackground1 + Match-3 encounter icon (20% chance on entry)
# 2: lobbybackground2 + Dog encounter icon (40% chance on entry)
# 3: lobbybackground3 + Maze encounter icon (20% chance on entry)
# 4: lobbybackground4 + Jumpers encounter icon (card.png) (40% chance on entry)
# 5: Crossroads Shelter final scene, ONLY appears when dog, maze, match3 levels are all >= 2
#
# IMPORTANT:
# - While quest_phase == 0 (Explore all available scenes), NO challenges appear at all.
# - After exploring is completed (quest_phase becomes 1), challenges can appear.

import pygame
import random
from sys import exit
import importlib.util
import os
import math

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

health = 9

dog_level = 1
maze_level = 1
match3_level = 1
jump_level = 1

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

quest_phase = 0
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

quest_box_rect = pygame.Rect(0, 0, 0, 0)

SCENE5_NAME = "Crossroads Shelter"

show_intro_overlay = True

# ---------------------------
# INVENTORY SYSTEM
# ---------------------------
inventory = {}
TOKEN_TYPES = ["match3", "dog", "maze", "jump"]

ui_font = pygame.font.SysFont(None, 24)
ui_font_small = pygame.font.SysFont(None, 20)
ui_font_big = pygame.font.SysFont(None, 30)
ui_font_title = pygame.font.SysFont(None, 38)

type_icons = {
    "match3": food_minigame,
    "dog": threat_minigame_base,
    "maze": maze_icon,
    "jump": card_icon,
}

type_labels = {
    "match3": "Match-3 Token",
    "dog": "Dog Token",
    "maze": "Maze Token",
    "jump": "Jump Token",
}

inventory_open = False
notifications_panel_open = False

INV_BTN_W, INV_BTN_H = 175, 44
NOTIF_BTN_W, NOTIF_BTN_H = 175, 44

inv_btn_rect = pygame.Rect(1200 - 18 - INV_BTN_W, 18, INV_BTN_W, INV_BTN_H)
notif_btn_rect = pygame.Rect(1200 - 18 - NOTIF_BTN_W, 18, NOTIF_BTN_W, NOTIF_BTN_H)

# ---------------------------
# NOTIFICATION SYSTEM
# ---------------------------
notifications = []
notification_history = []
DEFAULT_NOTIFICATION_MS = 4600


def push_notification(text: str, duration_ms: int = DEFAULT_NOTIFICATION_MS):
    msg = str(text)
    notifications.append({"text": msg, "until": pygame.time.get_ticks() + int(duration_ms)})
    notification_history.append(msg)
    if len(notification_history) > 120:
        del notification_history[0]


def draw_notifications(surface):
    now = pygame.time.get_ticks()
    alive = [n for n in notifications if now < n["until"]]
    notifications[:] = alive
    if not alive:
        return

    max_show = 3
    shown = alive[-max_show:]
    x_center = surface.get_width() // 2
    y = 24

    for n in shown:
        txt = ui_font.render(n["text"], True, (245, 245, 245))
        pad_x, pad_y = 16, 10
        w = txt.get_width() + pad_x * 2
        h = txt.get_height() + pad_y * 2

        box = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 185), (0, 0, w, h), border_radius=12)
        pygame.draw.rect(box, (245, 245, 245), (0, 0, w, h), 2, border_radius=12)

        surface.blit(box, (x_center - w // 2, y))
        surface.blit(txt, (x_center - txt.get_width() // 2, y + pad_y))
        y += h + 12


def draw_notification_button(surface):
    notif_btn_rect.x = surface.get_width() - QUEST_MARGIN - NOTIF_BTN_W
    notif_btn_rect.y = inv_btn_rect.bottom + 10

    pygame.draw.rect(surface, (0, 0, 0), notif_btn_rect, border_radius=10)
    pygame.draw.rect(surface, (240, 240, 240), notif_btn_rect, 2, border_radius=10)

    label = "Notifications"
    txt = ui_font.render(label, True, (245, 245, 245))
    surface.blit(txt, txt.get_rect(center=notif_btn_rect.center))


def draw_notifications_panel(surface):
    if not notifications_panel_open:
        return

    panel_w = 560
    panel_h = 340
    panel_x = surface.get_width() - panel_w - QUEST_MARGIN
    panel_y = notif_btn_rect.bottom + 10
    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    box = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    box.fill((0, 0, 0, 190))
    surface.blit(box, (panel_x, panel_y))
    pygame.draw.rect(surface, (240, 240, 240), panel_rect, 2, border_radius=14)

    title = ui_font_big.render("Past Notifications", True, (245, 245, 245))
    surface.blit(title, (panel_x + 18, panel_y + 14))

    content_rect = pygame.Rect(panel_x + 18, panel_y + 56, panel_w - 36, panel_h - 82)
    pygame.draw.rect(surface, (12, 12, 16), content_rect, border_radius=12)
    pygame.draw.rect(surface, (220, 220, 220), content_rect, 1, border_radius=12)

    if not notification_history:
        empty_txt = ui_font.render("No notifications yet.", True, (235, 235, 235))
        surface.blit(empty_txt, (content_rect.x + 14, content_rect.y + 14))
        return

    lines = notification_history[-10:]
    y = content_rect.y + 12
    for msg in reversed(lines):
        wrapped = wrap_text_lines(msg, ui_font_small, content_rect.w - 24)
        row_h = 12 + len(wrapped) * 18 + 10
        row = pygame.Rect(content_rect.x + 8, y, content_rect.w - 16, row_h)
        pygame.draw.rect(surface, (22, 22, 28), row, border_radius=10)
        pygame.draw.rect(surface, (180, 180, 180), row, 1, border_radius=10)

        ty = row.y + 10
        for ln in wrapped:
            surface.blit(ui_font_small.render(ln, True, (230, 230, 230)), (row.x + 10, ty))
            ty += 18

        y += row_h + 8
        if y > content_rect.bottom - 32:
            break


# ---------------------------
# SCENE 5 MACHINE
# ---------------------------
MACHINE_RECT = pygame.Rect(760, 165, 220, 245)
MACHINE_INTERACT_PAD_X = 140


def make_machine_icon(size=60):
    s = pygame.Surface((size, size), pygame.SRCALPHA)

    pygame.draw.rect(s, (255, 255, 255), (0, 0, size, size), border_radius=14)
    pygame.draw.rect(s, (220, 220, 220), (0, 0, size, size), 2, border_radius=14)

    body = pygame.Rect(int(size * 0.22), int(size * 0.18), int(size * 0.56), int(size * 0.68))
    pygame.draw.rect(s, (30, 30, 36), body, border_radius=10)
    pygame.draw.rect(s, (245, 245, 245), body, 2, border_radius=10)

    screen_rect = pygame.Rect(body.x + int(size * 0.07), body.y + int(size * 0.07),
                              int(size * 0.30), int(size * 0.18))
    pygame.draw.rect(s, (18, 18, 22), screen_rect, border_radius=6)
    pygame.draw.rect(s, (200, 200, 200), screen_rect, 2, border_radius=6)

    slot = pygame.Rect(body.x + int(size * 0.07), body.y + int(size * 0.40),
                       int(size * 0.42), int(size * 0.10))
    pygame.draw.rect(s, (10, 10, 12), slot, border_radius=6)
    pygame.draw.rect(s, (200, 200, 200), slot, 2, border_radius=6)

    knob_c = (body.right - int(size * 0.12), body.y + int(size * 0.16))
    pygame.draw.circle(s, (245, 245, 245), knob_c, int(size * 0.055))
    pygame.draw.circle(s, (200, 200, 200), knob_c, int(size * 0.055), 2)

    return s


MACHINE_ICON = make_machine_icon(60)


def player_is_near_machine(px: int) -> bool:
    near_rect = MACHINE_RECT.inflate(MACHINE_INTERACT_PAD_X * 2, 0)
    return near_rect.collidepoint(px, MACHINE_RECT.centery)


def draw_stylish_machine(surface, player_x: int):
    r = MACHINE_RECT

    shadow = pygame.Surface((r.w + 18, r.h + 18), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 90), (9, 9, r.w, r.h), border_radius=18)
    surface.blit(shadow, (r.x - 9, r.y - 9))

    pygame.draw.rect(surface, (14, 14, 18), r, border_radius=18)
    pygame.draw.rect(surface, (245, 245, 245), r, 2, border_radius=18)

    header = pygame.Rect(r.x + 14, r.y + 14, r.w - 28, 50)
    pygame.draw.rect(surface, (24, 24, 30), header, border_radius=14)
    pygame.draw.rect(surface, (245, 245, 245), header, 2, border_radius=14)

    light_c = (header.right - 22, header.y + 25)
    pygame.draw.circle(surface, (255, 255, 255), light_c, 8)
    pygame.draw.circle(surface, (200, 200, 200), light_c, 8, 2)

    inner = pygame.Rect(r.x + 14, r.y + 78, r.w - 28, r.h - 96)
    pygame.draw.rect(surface, (0, 0, 0), inner, border_radius=14)
    pygame.draw.rect(surface, (245, 245, 245), inner, 2, border_radius=14)

    disp = pygame.Rect(inner.x + 12, inner.y + 12, inner.w - 24, 48)
    pygame.draw.rect(surface, (18, 18, 22), disp, border_radius=12)
    pygame.draw.rect(surface, (200, 200, 200), disp, 2, border_radius=12)

    slot = pygame.Rect(inner.x + 12, inner.y + 74, inner.w - 24, 40)
    pygame.draw.rect(surface, (10, 10, 12), slot, border_radius=12)
    pygame.draw.rect(surface, (200, 200, 200), slot, 2, border_radius=12)

    tray = pygame.Rect(inner.x + 12, inner.bottom - 52, inner.w - 24, 38)
    pygame.draw.rect(surface, (18, 18, 22), tray, border_radius=12)
    pygame.draw.rect(surface, (200, 200, 200), tray, 2, border_radius=12)

    icon_rect = MACHINE_ICON.get_rect(midbottom=(r.centerx, r.y - 8))
    surface.blit(MACHINE_ICON, icon_rect)

    label = ui_font_small.render("Forge higher-tier tokens", True, (225, 225, 225))
    surface.blit(label, (r.x + 24, r.bottom + 10))

    if player_is_near_machine(player_x):
        hint = ui_font.render("Press E", True, (245, 245, 245))
        hint_bg = pygame.Surface((hint.get_width() + 18, hint.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(hint_bg, (0, 0, 0, 170), hint_bg.get_rect(), border_radius=10)
        pygame.draw.rect(hint_bg, (245, 245, 245), hint_bg.get_rect(), 2, border_radius=10)
        surface.blit(hint_bg, (r.x + (r.w - hint_bg.get_width()) // 2, r.y - 48))
        surface.blit(hint, (r.x + (r.w - hint.get_width()) // 2, r.y - 42))


# ---------------------------
# SCENE 5 SHELTER
# ---------------------------
SHELTER_RECT = pygame.Rect(120, 160, 260, 255)
SHELTER_INTERACT_PAD_X = 170


def make_shelter_icon(size=60):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(s, (255, 255, 255), (0, 0, size, size), border_radius=14)
    pygame.draw.rect(s, (220, 220, 220), (0, 0, size, size), 2, border_radius=14)

    roof = [(int(size * 0.18), int(size * 0.40)),
            (int(size * 0.50), int(size * 0.16)),
            (int(size * 0.82), int(size * 0.40))]
    pygame.draw.polygon(s, (30, 30, 36), roof)
    pygame.draw.polygon(s, (245, 245, 245), roof, 2)

    body = pygame.Rect(int(size * 0.24), int(size * 0.40), int(size * 0.52), int(size * 0.44))
    pygame.draw.rect(s, (30, 30, 36), body, border_radius=10)
    pygame.draw.rect(s, (245, 245, 245), body, 2, border_radius=10)

    door = pygame.Rect(int(size * 0.46), int(size * 0.56), int(size * 0.12), int(size * 0.28))
    pygame.draw.rect(s, (10, 10, 12), door, border_radius=6)
    pygame.draw.rect(s, (200, 200, 200), door, 2, border_radius=6)

    return s


SHELTER_ICON = make_shelter_icon(60)


def player_is_near_shelter(px: int) -> bool:
    near_rect = SHELTER_RECT.inflate(SHELTER_INTERACT_PAD_X * 2, 0)
    return near_rect.collidepoint(px, SHELTER_RECT.centery)


def draw_shelter_booth(surface, player_x: int):
    r = SHELTER_RECT

    shadow = pygame.Surface((r.w + 18, r.h + 18), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 90), (9, 9, r.w, r.h), border_radius=18)
    surface.blit(shadow, (r.x - 9, r.y - 9))

    pygame.draw.rect(surface, (14, 14, 18), r, border_radius=18)
    pygame.draw.rect(surface, (245, 245, 245), r, 2, border_radius=18)

    header = pygame.Rect(r.x + 14, r.y + 14, r.w - 28, 50)
    pygame.draw.rect(surface, (24, 24, 30), header, border_radius=14)
    pygame.draw.rect(surface, (245, 245, 245), header, 2, border_radius=14)

    light_c = (header.right - 22, header.y + 25)
    pygame.draw.circle(surface, (255, 255, 255), light_c, 8)
    pygame.draw.circle(surface, (200, 200, 200), light_c, 8, 2)

    inner = pygame.Rect(r.x + 14, r.y + 78, r.w - 28, r.h - 96)
    pygame.draw.rect(surface, (0, 0, 0), inner, border_radius=14)
    pygame.draw.rect(surface, (245, 245, 245), inner, 2, border_radius=14)

    icon_rect = SHELTER_ICON.get_rect(midbottom=(r.centerx, r.y - 8))
    surface.blit(SHELTER_ICON, icon_rect)

    label = ui_font_small.render("Rescue, recovery, adoption", True, (225, 225, 225))
    surface.blit(label, (r.x + 26, r.bottom + 10))

    if player_is_near_shelter(player_x):
        hint = ui_font.render("Press E", True, (245, 245, 245))
        hint_bg = pygame.Surface((hint.get_width() + 18, hint.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(hint_bg, (0, 0, 0, 170), hint_bg.get_rect(), border_radius=10)
        pygame.draw.rect(hint_bg, (245, 245, 245), hint_bg.get_rect(), 2, border_radius=10)
        surface.blit(hint_bg, (r.x + (r.w - hint_bg.get_width()) // 2, r.y - 48))
        surface.blit(hint, (r.x + (r.w - hint.get_width()) // 2, r.y - 42))


# ---------------------------
# INVENTORY HELPERS
# ---------------------------
def inv_get(token_type: str, tier: int) -> int:
    tiers = inventory.get(token_type, {})
    return int(tiers.get(int(tier), 0))


def inv_add(token_type: str, tier: int, amount: int):
    if amount <= 0:
        return
    tier = int(tier)
    if token_type not in inventory:
        inventory[token_type] = {}
    inventory[token_type][tier] = int(inventory[token_type].get(tier, 0)) + int(amount)


def inv_take(token_type: str, tier: int, amount: int) -> bool:
    if amount <= 0:
        return True
    tier = int(tier)
    have = inv_get(token_type, tier)
    if have < amount:
        return False
    inventory[token_type][tier] = have - amount
    if inventory[token_type][tier] <= 0:
        del inventory[token_type][tier]
    if token_type in inventory and len(inventory[token_type]) == 0:
        del inventory[token_type]
    return True


def inv_total_tokens() -> int:
    total = 0
    for t in inventory.values():
        for c in t.values():
            total += int(c)
    return total


def scaled_icon(img, size):
    return pygame.transform.smoothscale(img, (size, size))


def total_tokens_all() -> int:
    total = 0
    for token_type in TOKEN_TYPES:
        for _, count in inventory.get(token_type, {}).items():
            total += int(count)
    return total


def total_tokens_of_tier_any(tier: int) -> int:
    total = 0
    for token_type in TOKEN_TYPES:
        total += inv_get(token_type, tier)
    return total


def spend_any_tokens_of_tier(tier: int, amount: int) -> bool:
    if total_tokens_of_tier_any(tier) < amount:
        return False

    remaining = int(amount)
    for token_type in TOKEN_TYPES:
        if remaining <= 0:
            break
        have = inv_get(token_type, tier)
        take = min(have, remaining)
        if take > 0:
            inv_take(token_type, tier, take)
            remaining -= take
    return True


# ---------------------------
# TOKEN COMBINE LOGIC
# ---------------------------
def combine_success_chance(target_tier: int) -> float:
    target_tier = int(target_tier)
    if target_tier <= 3:
        return 1.0
    mapping = {
        4: 0.88,
        5: 0.74,
        6: 0.60,
        7: 0.46,
        8: 0.34
    }
    return max(0.2, mapping.get(target_tier, 0.26))


machine_open = False
machine_selected_type = "dog"
machine_selected_tier = 1


def center_machine_ui():
    panel_w, panel_h = 500, 470
    machine_ui_pos[0] = (screen.get_width() - panel_w) // 2
    machine_ui_pos[1] = (screen.get_height() - panel_h) // 2


def machine_can_combine(token_type: str, tier: int) -> bool:
    return inv_get(token_type, tier) >= 2


def machine_do_combine(token_type: str, tier: int) -> bool:
    tier = int(tier)
    target_tier = tier + 1

    if not machine_can_combine(token_type, tier):
        push_notification("Need 2 matching tokens to forge.")
        return False

    chance = combine_success_chance(target_tier)
    roll = random.random()

    ok_take = inv_take(token_type, tier, 2)
    if not ok_take:
        push_notification("Not enough tokens.")
        return False

    if roll <= chance:
        inv_add(token_type, target_tier, 1)
        push_notification(f"Forge success. Tier {target_tier} made.")
        return True

    push_notification("Forge failed. Tokens were consumed.")
    return False


# ---------------------------
# INVENTORY UI
# ---------------------------
def draw_inventory_button(surface):
    inv_btn_rect.x = surface.get_width() - QUEST_MARGIN - INV_BTN_W
    inv_btn_rect.y = quest_box_rect.bottom + 12

    pygame.draw.rect(surface, (0, 0, 0), inv_btn_rect, border_radius=10)
    pygame.draw.rect(surface, (240, 240, 240), inv_btn_rect, 2, border_radius=10)

    total = inv_total_tokens()
    label = f"Inventory ({total})"
    txt = ui_font.render(label, True, (245, 245, 245))
    surface.blit(txt, txt.get_rect(center=inv_btn_rect.center))


def draw_inventory_panel(surface):
    if not inventory_open:
        return

    types_with_items = []
    for t in TOKEN_TYPES:
        any_here = any(int(c) > 0 for c in inventory.get(t, {}).values())
        if any_here:
            types_with_items.append(t)

    panel_w = 580
    panel_h = 370
    panel_x = surface.get_width() - panel_w - QUEST_MARGIN
    panel_y = inv_btn_rect.bottom + 10
    panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    box = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    box.fill((0, 0, 0, 185))
    surface.blit(box, (panel_x, panel_y))
    pygame.draw.rect(surface, (240, 240, 240), panel_rect, 2, border_radius=14)

    title = ui_font_big.render("Inventory", True, (245, 245, 245))
    subtitle = ui_font_small.render(
        "Tokens are used for forging upgrades, rescue paths, and adoption donations.",
        True,
        (220, 220, 220)
    )
    surface.blit(title, (panel_x + 18, panel_y + 14))
    surface.blit(subtitle, (panel_x + 18, panel_y + 46))

    if not types_with_items:
        empty_txt = ui_font.render("Inventory is empty.", True, (235, 235, 235))
        surface.blit(empty_txt, (panel_x + 18, panel_y + 108))
        close_txt = ui_font_small.render("Click Inventory again to close.", True, (210, 210, 210))
        surface.blit(close_txt, (panel_x + 18, panel_y + panel_h - 300))
        return

    row_y = panel_y + 86
    row_h = 58

    for t in types_with_items[:4]:
        row = pygame.Rect(panel_x + 18, row_y, panel_w - 36, row_h)
        pygame.draw.rect(surface, (16, 16, 20), row, border_radius=12)
        pygame.draw.rect(surface, (220, 220, 220), row, 2, border_radius=12)

        icon_box = pygame.Rect(row.x + 10, row.y + 9, 40, 40)
        pygame.draw.rect(surface, (255, 255, 255), icon_box, border_radius=10)
        pygame.draw.rect(surface, (220, 220, 220), icon_box, 2, border_radius=10)

        icon_img = scaled_icon(type_icons[t], 28)
        surface.blit(icon_img, icon_img.get_rect(center=icon_box.center))

        label = ui_font.render(type_labels[t], True, (245, 245, 245))
        surface.blit(label, (row.x + 62, row.y + 7))

        tiers_sorted = sorted(int(k) for k, v in inventory.get(t, {}).items() if int(v) > 0)
        tier_texts = [f"Tier {tier} x{inv_get(t, tier)}" for tier in tiers_sorted]
        tier_line = "   |   ".join(tier_texts) if tier_texts else "No tokens"
        tier_render = ui_font_small.render(tier_line, True, (220, 220, 220))
        surface.blit(tier_render, (row.x + 62, row.y + 31))

        row_y += row_h + 12

    close_txt = ui_font_small.render("Click Inventory again to close.", True, (210, 210, 210))
    surface.blit(close_txt, (panel_x + 18, panel_y + panel_h - 300))


# ---------------------------
# MACHINE UI
# ---------------------------
machine_ui_pos = [350, 165]
machine_ui_dragging = False
machine_ui_drag_offset = (0, 0)


def draw_machine_ui(surface):
    if not machine_open:
        return None

    panel_w, panel_h = 500, 470
    panel_x, panel_y = int(machine_ui_pos[0]), int(machine_ui_pos[1])
    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    panel.x = max(0, min(surface.get_width() - panel.w, panel.x))
    panel.y = max(0, min(surface.get_height() - panel.h, panel.y))
    machine_ui_pos[0], machine_ui_pos[1] = panel.x, panel.y

    overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    surface.blit(overlay, (0, 0))

    bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    bg.fill((10, 10, 12, 230))
    surface.blit(bg, (panel_x, panel_y))
    pygame.draw.rect(surface, (245, 245, 245), panel, 2, border_radius=18)

    header = pygame.Rect(panel_x + 12, panel_y + 10, panel_w - 24, 74)
    pygame.draw.rect(surface, (0, 0, 0), header, border_radius=16)
    pygame.draw.rect(surface, (245, 245, 245), header, 2, border_radius=16)

    icon = scaled_icon(MACHINE_ICON, 44)
    surface.blit(icon, (header.x + 14, header.y + 15))
    surface.blit(ui_font.render("Token Forge", True, (245, 245, 245)), (header.x + 70, header.y + 14))
    surface.blit(
        ui_font_small.render("Spend 2 matching tokens to attempt 1 higher-tier token.", True, (220, 220, 220)),
        (header.x + 70, header.y + 38)
    )

    type_btn_rects = {}
    start_x = panel_x + 18
    start_y = panel_y + 102
    gap = 12
    btn_w = (panel_w - 18 * 2 - gap) // 2
    btn_h = 70

    positions = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for i, t in enumerate(TOKEN_TYPES):
        gx, gy = positions[i]
        x = start_x + gx * (btn_w + gap)
        y = start_y + gy * (btn_h + gap)
        r = pygame.Rect(x, y, btn_w, btn_h)
        type_btn_rects[t] = r
        pygame.draw.rect(surface, (26, 26, 32) if t == machine_selected_type else (0, 0, 0), r, border_radius=14)
        pygame.draw.rect(surface, (245, 245, 245), r, 2, border_radius=14)

        icon_box = pygame.Rect(r.x + 12, r.y + 8, 54, 54)
        pygame.draw.rect(surface, (255, 255, 255), icon_box, border_radius=12)
        pygame.draw.rect(surface, (220, 220, 220), icon_box, 2, border_radius=12)

        img = scaled_icon(type_icons[t], 40)
        surface.blit(img, img.get_rect(center=icon_box.center))
        surface.blit(ui_font_small.render(type_labels[t], True, (235, 235, 235)), (r.x + 78, r.y + 25))

    tiers = sorted(int(k) for k, v in inventory.get(machine_selected_type, {}).items() if int(v) > 0)
    if not tiers:
        tiers = [1]

    tier_area = pygame.Rect(panel_x + 18, panel_y + 268, panel_w - 36, 62)
    pygame.draw.rect(surface, (16, 16, 20), tier_area, border_radius=14)
    pygame.draw.rect(surface, (220, 220, 220), tier_area, 2, border_radius=14)
    surface.blit(ui_font.render("Select Tier", True, (245, 245, 245)), (tier_area.x + 12, tier_area.y + 8))

    tier_btn_rects = {}
    tx = tier_area.x + 110
    ty = tier_area.y + 10
    for tier in tiers[:5]:
        r = pygame.Rect(tx, ty, 62, 38)
        tier_btn_rects[tier] = r
        pygame.draw.rect(surface, (28, 28, 34) if tier == machine_selected_tier else (0, 0, 0), r, border_radius=10)
        pygame.draw.rect(surface, (245, 245, 245), r, 2, border_radius=10)
        surface.blit(ui_font.render(str(tier), True, (245, 245, 245)), (r.x + 22, r.y + 8))
        tx += 72

    own = inv_get(machine_selected_type, machine_selected_tier)
    target_tier = int(machine_selected_tier) + 1
    chance = combine_success_chance(target_tier)
    pct = int(chance * 100)

    stat_card = pygame.Rect(panel_x + 18, panel_y + 344, panel_w - 36, 74)
    pygame.draw.rect(surface, (16, 16, 20), stat_card, border_radius=14)
    pygame.draw.rect(surface, (220, 220, 220), stat_card, 2, border_radius=14)

    surface.blit(ui_font.render(f"Owned: {own}", True, (245, 245, 245)), (stat_card.x + 14, stat_card.y + 12))
    surface.blit(
        ui_font.render(f"Forge: Tier {machine_selected_tier} -> Tier {target_tier}", True, (225, 225, 225)),
        (stat_card.x + 130, stat_card.y + 12)
    )
    surface.blit(ui_font.render(f"Success: {pct}%", True, (225, 225, 225)), (stat_card.x + 14, stat_card.y + 42))

    combine_rect = pygame.Rect(panel_x + 18, panel_y + panel_h - 62, 220, 44)
    close_rect = pygame.Rect(panel_x + panel_w - 18 - 130, panel_y + panel_h - 62, 130, 44)

    pygame.draw.rect(surface, (0, 0, 0), combine_rect, border_radius=12)
    pygame.draw.rect(surface, (245, 245, 245), combine_rect, 2, border_radius=12)
    pygame.draw.rect(surface, (0, 0, 0), close_rect, border_radius=12)
    pygame.draw.rect(surface, (245, 245, 245), close_rect, 2, border_radius=12)

    can = machine_can_combine(machine_selected_type, machine_selected_tier)
    surface.blit(ui_font.render("Forge" if can else "Need 2", True, (245, 245, 245)), (combine_rect.x + 20, combine_rect.y + 10))
    surface.blit(ui_font.render("Close", True, (245, 245, 245)), (close_rect.x + 36, close_rect.y + 10))

    return {
        "panel": panel,
        "header": header,
        "type_btns": type_btn_rects,
        "tier_btns": tier_btn_rects,
        "combine_btn": combine_rect,
        "close_btn": close_rect,
    }


# ---------------------------
# ADOPTION / NEUTER STATE
# ---------------------------
neutered = False
adopted = False
adoption_points = 0
adoption_open = False

adopt_ui_pos = [320, 70]
adopt_ui_dragging = False
adopt_ui_drag_offset = (0, 0)

adopt_selected_type = "dog"
adopt_selected_tier = 1

DONATION_BONUS_BY_TIER = {
    1: 1,
    2: 3,
    3: 7,
    4: 15,
    5: 31,
}

# Dynamic neuter options
neuter_refresh_count = 0
current_neuter_batch = []
last_neuter_best_survival = 0.0


def center_adoption_ui():
    panel_w, panel_h = 580, 690
    adopt_ui_pos[0] = (screen.get_width() - panel_w) // 2
    adopt_ui_pos[1] = (screen.get_height() - panel_h) // 2


def adoption_chance_percent() -> int:
    base = 2
    if neutered:
        base += 12
    pct = base + int(adoption_points)
    return max(0, min(82, pct))


def award_adoption_progress_from_win(cleared_level: int):
    global adoption_points
    if neutered:
        adoption_points += max(1, int(cleared_level))


def donate_tokens_for_adoption(token_type: str, tier: int, amount: int) -> bool:
    global adoption_points

    tier = int(tier)
    amount = int(amount)
    bonus_each = DONATION_BONUS_BY_TIER.get(tier, 0)

    if inv_take(token_type, tier, amount):
        adoption_points += bonus_each * amount
        return True
    return False


def refresh_cost_tokens() -> int:
    return 1 + int(neuter_refresh_count)


def generate_neuter_batch(previous_best: float = 0.0):
    batch = []

    min_best = max(0.34, float(previous_best) + 0.05)

    candidate_names = [
        "Night Market Street Vet",
        "Volunteer Trap-and-Release Van",
        "Crowded Charity Clinic",
        "Rescue Partner Recovery House",
        "Underground Foster Network",
        "Rain Shelter Animal Team",
        "Late-Night Community Vet",
        "Emergency Pop-Up Shelter",
        "Neighborhood Foster Clinic",
        "Transit Rescue Medical Team"
    ]

    random.shuffle(candidate_names)

    s1_low = max(0.28, min_best - 0.18)
    s1_high = max(s1_low + 0.01, min(0.55, min_best - 0.10))

    s2_low = max(0.38, min_best - 0.08)
    s2_high = max(s2_low + 0.01, min(0.62, min_best - 0.02))

    s3_low = max(0.50, min_best + 0.00)
    s3_high = max(s3_low + 0.01, min(0.72, min_best + 0.08))

    s4_low = max(0.64, min_best + 0.08)
    s4_high = max(s4_low + 0.01, min(0.90, min_best + 0.20))

    survival_values = [
        round(random.uniform(s1_low, s1_high), 2),
        round(random.uniform(s2_low, s2_high), 2),
        round(random.uniform(s3_low, s3_high), 2),
        round(random.uniform(s4_low, s4_high), 2),
    ]

    survival_values = [max(0.20, min(0.90, s)) for s in survival_values]
    survival_values.sort()

    costs = [
        ("any", 1, 2),
        ("any", 2, 1),
        ("any", 3, 1),
        ("any", 4, 1),
    ]

    notes = [
        "cheap but risky",
        "more organized rescue",
        "better medical recovery",
        "best survival in this batch"
    ]

    reward_sets = [
        {"tier1_any": (1, 1)},
        {"mix": True},
        {"tier2_any": 1, "tier1_any": (1, 2)},
        {"tier2_any": 2, "tier1_any": (2, 3)},
    ]

    for i in range(4):
        batch.append({
            "id": i + 1,
            "name": candidate_names[i],
            "survive": survival_values[i],
            "cost": costs[i],
            "note": notes[i],
            "reward": reward_sets[i],
            "success_text": f"The cat survived through {candidate_names[i]}.",
            "fail_text": f"{candidate_names[i]} could not fully protect the cat."
        })

    return batch


def ensure_neuter_batch():
    global current_neuter_batch, last_neuter_best_survival
    if not current_neuter_batch:
        current_neuter_batch = generate_neuter_batch(0.0)
        last_neuter_best_survival = max(opt["survive"] for opt in current_neuter_batch)


def refresh_neuter_batch() -> bool:
    global neuter_refresh_count, current_neuter_batch, last_neuter_best_survival

    cost = refresh_cost_tokens()
    if total_tokens_of_tier_any(1) < cost:
        push_notification(f"Need {cost} Tier 1 token(s) to refresh rescue routes.")
        return False

    spend_any_tokens_of_tier(1, cost)
    neuter_refresh_count += 1

    current_neuter_batch = generate_neuter_batch(last_neuter_best_survival)
    last_neuter_best_survival = max(opt["survive"] for opt in current_neuter_batch)

    push_notification(f"Routes refreshed. Cost: {cost} Tier 1 token(s).")
    return True


def do_neuter_program(program_id: int) -> str:
    global neutered

    if neutered:
        return "survive"

    option = None
    for opt in current_neuter_batch:
        if int(opt["id"]) == int(program_id):
            option = opt
            break

    if option is None:
        push_notification("That rescue route is unavailable.")
        return "nope"

    want_tier = option["cost"][1]
    want_amt = option["cost"][2]

    if total_tokens_of_tier_any(want_tier) < want_amt:
        push_notification(f"Need {want_amt} token(s) of Tier {want_tier}.")
        return "nope"

    spend_any_tokens_of_tier(want_tier, want_amt)

    if random.random() <= float(option["survive"]):
        neutered = True
        push_notification(option["success_text"])

        if option["reward"].get("mix"):
            for _ in range(random.randint(2, 4)):
                rt = random.choice(TOKEN_TYPES)
                rtier = random.choice([1, 1, 2])
                inv_add(rt, rtier, 1)
            push_notification("Rescue bonus: mixed tokens.")

        if "tier2_any" in option["reward"]:
            for _ in range(int(option["reward"]["tier2_any"])):
                rt = random.choice(TOKEN_TYPES)
                inv_add(rt, 2, 1)

        if "tier1_any" in option["reward"]:
            lo, hi = option["reward"]["tier1_any"]
            for _ in range(random.randint(int(lo), int(hi))):
                rt = random.choice(TOKEN_TYPES)
                inv_add(rt, 1, 1)

        return "survive"

    push_notification(option["fail_text"])
    return "fail"


def try_adoption_roll() -> bool:
    global adopted
    pct = adoption_chance_percent()
    if random.random() <= (pct / 100.0):
        adopted = True
        return True
    return False


def draw_modern_card(surface, rect, fill=(14, 14, 18), border=(235, 235, 235), radius=16):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, 2, border_radius=radius)


def draw_adoption_ui(surface):
    if not adoption_open:
        return None

    ensure_neuter_batch()

    panel_w, panel_h = 580, 690
    panel_x, panel_y = int(adopt_ui_pos[0]), int(adopt_ui_pos[1])
    panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    panel.x = max(0, min(surface.get_width() - panel.w, panel.x))
    panel.y = max(0, min(surface.get_height() - panel.h, panel.y))
    adopt_ui_pos[0], adopt_ui_pos[1] = panel.x, panel.y

    overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    surface.blit(overlay, (0, 0))

    bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    bg.fill((10, 10, 12, 232))
    surface.blit(bg, (panel_x, panel_y))
    pygame.draw.rect(surface, (245, 245, 245), panel, 2, border_radius=18)

    header = pygame.Rect(panel_x + 12, panel_y + 10, panel_w - 24, 86)
    draw_modern_card(surface, header, fill=(0, 0, 0), border=(245, 245, 245), radius=16)

    icon = scaled_icon(SHELTER_ICON, 46)
    surface.blit(icon, (header.x + 16, header.y + 18))
    surface.blit(ui_font.render("Crossroads Shelter", True, (245, 245, 245)), (header.x + 74, header.y + 16))
    surface.blit(ui_font_small.render("Rescue paths, recovery progress, and adoption chances.", True, (220, 220, 220)),
                 (header.x + 74, header.y + 42))

    stat1 = pygame.Rect(panel_x + 18, panel_y + 112, 170, 72)
    stat2 = pygame.Rect(panel_x + 205, panel_y + 112, 170, 72)
    stat3 = pygame.Rect(panel_x + 392, panel_y + 112, 170, 72)

    for r in (stat1, stat2, stat3):
        draw_modern_card(surface, r, fill=(16, 16, 20), border=(220, 220, 220), radius=14)

    surface.blit(ui_font_small.render("Rescue Status", True, (210, 210, 210)), (stat1.x + 12, stat1.y + 10))
    surface.blit(ui_font.render("SAFE" if neutered else "AT RISK", True, (245, 245, 245)), (stat1.x + 12, stat1.y + 36))

    surface.blit(ui_font_small.render("Adoption Chance", True, (210, 210, 210)), (stat2.x + 12, stat2.y + 10))
    surface.blit(ui_font.render(f"{adoption_chance_percent()}%", True, (245, 245, 245)), (stat2.x + 12, stat2.y + 36))

    surface.blit(ui_font_small.render("Bonus Chance", True, (210, 210, 210)), (stat3.x + 12, stat3.y + 10))
    surface.blit(ui_font.render(f"+{adoption_points}%", True, (245, 245, 245)), (stat3.x + 12, stat3.y + 36))

    btns = {}

    close_rect = pygame.Rect(panel_x + panel_w - 148, panel_y + 18, 118, 38)
    pygame.draw.rect(surface, (0, 0, 0), close_rect, border_radius=12)
    pygame.draw.rect(surface, (245, 245, 245), close_rect, 2, border_radius=12)
    surface.blit(ui_font.render("Close", True, (245, 245, 245)), (close_rect.x + 28, close_rect.y + 8))
    btns["close_btn"] = close_rect

    if not neutered:
        info_card = pygame.Rect(panel_x + 18, panel_y + 200, panel_w - 36, 76)
        draw_modern_card(surface, info_card, fill=(16, 16, 20), border=(220, 220, 220), radius=14)
        lines = wrap_text_lines(
            "Choose one rescue route. Refreshing costs Tier 1 tokens, but later batches give better survival chances.",
            ui_font_small, info_card.w - 20
        )
        yy = info_card.y + 12
        for ln in lines[:3]:
            surface.blit(ui_font_small.render(ln, True, (225, 225, 225)), (info_card.x + 10, yy))
            yy += 20

        def rescue_card(y, title, cost, surv, note, key):
            r = pygame.Rect(panel_x + 18, y, panel_w - 36, 64)
            btns[key] = r
            draw_modern_card(surface, r, fill=(0, 0, 0), border=(245, 245, 245), radius=14)
            surface.blit(ui_font.render(title, True, (245, 245, 245)), (r.x + 14, r.y + 8))
            meta = f"Cost: {cost}    Survival: {surv}"
            surface.blit(ui_font_small.render(meta, True, (220, 220, 220)), (r.x + 14, r.y + 34))
            surface.blit(ui_font_small.render(note, True, (200, 200, 200)), (r.x + 300, r.y + 34))

        base_y = panel_y + 290
        gap_y = 74
        for i, opt in enumerate(current_neuter_batch):
            route_y = base_y + i * gap_y
            cost_txt = f"any Tier {opt['cost'][1]} x{opt['cost'][2]}"
            surv_txt = f"{int(opt['survive'] * 100)}%"
            rescue_card(
                route_y,
                f"{opt['id']}) {opt['name']}",
                cost_txt,
                surv_txt,
                opt["note"],
                f"prog{opt['id']}"
            )

        refresh_rect = pygame.Rect(panel_x + 18, panel_y + panel_h - 56, 240, 38)
        pygame.draw.rect(surface, (0, 0, 0), refresh_rect, border_radius=12)
        pygame.draw.rect(surface, (245, 245, 245), refresh_rect, 2, border_radius=12)
        refresh_txt = f"Refresh Routes ({refresh_cost_tokens()})"
        surface.blit(ui_font.render(refresh_txt, True, (245, 245, 245)), (refresh_rect.x + 14, refresh_rect.y + 8))
        btns["refresh_btn"] = refresh_rect

    else:
        info_card = pygame.Rect(panel_x + 18, panel_y + 200, panel_w - 36, 88)
        draw_modern_card(surface, info_card, fill=(16, 16, 20), border=(220, 220, 220), radius=14)
        lines = wrap_text_lines(
            "Now that the cat survived rescue, keep winning minigames to gain progress points, "
            "or donate tokens to improve the chance of finally being adopted.",
            ui_font_small, info_card.w - 20
        )
        yy = info_card.y + 12
        for ln in lines[:3]:
            surface.blit(ui_font_small.render(ln, True, (225, 225, 225)), (info_card.x + 10, yy))
            yy += 20

        try_rect = pygame.Rect(panel_x + 18, panel_y + 308, panel_w - 36, 58)
        draw_modern_card(surface, try_rect, fill=(0, 0, 0), border=(245, 245, 245), radius=14)
        surface.blit(ui_font.render("Try Adoption", True, (245, 245, 245)), (try_rect.x + 18, try_rect.y + 16))
        btns["try_adopt"] = try_rect

        donate_title = pygame.Rect(panel_x + 18, panel_y + 382, panel_w - 36, 50)
        draw_modern_card(surface, donate_title, fill=(16, 16, 20), border=(220, 220, 220), radius=14)
        surface.blit(ui_font.render("Donate a token: higher tiers give bigger % boosts", True, (245, 245, 245)),
                     (donate_title.x + 14, donate_title.y + 13))

        type_rects = {}
        type_y = panel_y + 446
        x = panel_x + 18
        for t in TOKEN_TYPES:
            r = pygame.Rect(x, type_y, 78, 78)
            type_rects[t] = r
            draw_modern_card(
                surface,
                r,
                fill=(26, 26, 32) if t == adopt_selected_type else (0, 0, 0),
                border=(245, 245, 245),
                radius=14
            )

            icon_box = pygame.Rect(r.x + 15, r.y + 15, 48, 48)
            pygame.draw.rect(surface, (255, 255, 255), icon_box, border_radius=12)
            pygame.draw.rect(surface, (220, 220, 220), icon_box, 2, border_radius=12)

            icon_img = scaled_icon(type_icons[t], 34)
            surface.blit(icon_img, icon_img.get_rect(center=icon_box.center))

            x += 90
        btns["type_rects"] = type_rects

        tier_rects = {}
        tier_y = panel_y + 542
        surface.blit(ui_font.render("Tier", True, (245, 245, 245)), (panel_x + 18, tier_y + 8))
        tx = panel_x + 88
        for tier in [1, 2, 3, 4, 5]:
            r = pygame.Rect(tx, tier_y, 58, 38)
            tier_rects[tier] = r
            pygame.draw.rect(surface, (28, 28, 34) if tier == adopt_selected_tier else (0, 0, 0), r, border_radius=10)
            pygame.draw.rect(surface, (245, 245, 245), r, 2, border_radius=10)
            surface.blit(ui_font.render(str(tier), True, (245, 245, 245)), (r.x + 20, r.y + 8))
            tx += 68
        btns["tier_rects"] = tier_rects

        have = inv_get(adopt_selected_type, adopt_selected_tier)
        bonus_preview = DONATION_BONUS_BY_TIER.get(adopt_selected_tier, 0)

        surface.blit(ui_font_small.render(f"Own: {have}", True, (225, 225, 225)), (panel_x + 450, tier_y + 10))
        surface.blit(
            ui_font_small.render(f"Donate Tier {adopt_selected_tier}: +{bonus_preview}%", True, (225, 225, 225)),
            (panel_x + 18, tier_y + 46)
        )

        donate_rect = pygame.Rect(panel_x + panel_w - 170, panel_y + panel_h - 56, 152, 38)
        pygame.draw.rect(surface, (0, 0, 0), donate_rect, border_radius=12)
        pygame.draw.rect(surface, (245, 245, 245), donate_rect, 2, border_radius=12)

        surface.blit(ui_font.render("Donate 1" if have >= 1 else "Need 1", True, (245, 245, 245)),
                     (donate_rect.x + 20, donate_rect.y + 8))
        btns["donate_btn"] = donate_rect

    return {"panel": panel, "header": header, "btns": btns}


# ---------------------------
# QUESTS + STORY
# ---------------------------
def clamp_health():
    global health
    health = max(0, health)


def apply_full_heart_damage():
    global health
    health -= 1
    clamp_health()


def is_final_scene_unlocked():
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
        quest_phase = 1


def grant_quest_completion_bonus(level_completed: int):
    n = int(level_completed)
    if n <= 0:
        return
    for t in TOKEN_TYPES:
        inv_add(t, tier=1, amount=n)
    push_notification(f"Quest clear: Level {n}. Bonus: +{n} of each token!")


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
        completed = quest_level
        grant_quest_completion_bonus(completed)
        quest_level += 1


def draw_quests(surface):
    global quest_box_rect

    title = "Goals"
    title_surf = quest_title_font.render(title, True, TITLE_WHITE)

    lines = []
    colors = []

    if quest_phase == 0:
        lines.append("-- Explore all available scenes")
        colors.append(WHITE)
        lines.append("-- Learn the city before taking on challenges")
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

    quest_box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

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
    box_h = 212
    box_x = (surface.get_width() - box_w) // 2
    box_y = surface.get_height() - box_h - 14

    overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))
    surface.blit(overlay, (box_x, box_y))
    pygame.draw.rect(surface, (240, 240, 240), (box_x, box_y, box_w, box_h), 2, border_radius=14)

    title = story_font.render(SCENE5_NAME, True, STORY_TEXT_COLOR)
    surface.blit(title, (box_x + 18, box_y + 14))

    info_lines = [
        "This is where the cat's street journey changes. Tokens matter here.",
        "Tokens are earned by winning minigames. A cleared level gives that many Tier 1 tokens of that minigame type.",
        "Use tokens at the machine to forge stronger tiers, use them at the shelter for risky rescue paths, or donate them to improve adoption odds.",
        "Higher-tier tokens unlock stronger choices. Without tokens, you lose access to better rescue and adoption options.",
        "Press E near the left shelter booth or the right forge machine."
    ]

    y = box_y + 50
    for line in info_lines:
        wrapped = wrap_text_lines(line, story_font_small, box_w - 36)
        for ln in wrapped:
            surface.blit(story_font_small.render(ln, True, (225, 225, 225)), (box_x + 18, y))
            y += 22


# ---------------------------
# INTRO OVERLAY
# ---------------------------
def draw_intro_overlay(surface):
    overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 215))
    surface.blit(overlay, (0, 0))

    panel = pygame.Rect(90, 60, 1020, 660)
    pygame.draw.rect(surface, (12, 12, 16), panel, border_radius=24)
    pygame.draw.rect(surface, (245, 245, 245), panel, 2, border_radius=24)

    title = pygame.font.SysFont(None, 58).render("Paw-aware", True, (245, 245, 245))
    subtitle = pygame.font.SysFont(None, 32).render("Survive the city. Earn tokens. Reach a future.", True, (225, 225, 225))

    surface.blit(title, (panel.x + 28, panel.y + 24))
    surface.blit(subtitle, (panel.x + 28, panel.y + 82))

    left = pygame.Rect(panel.x + 24, panel.y + 132, 470, 420)
    right = pygame.Rect(panel.x + 526, panel.y + 132, 470, 420)

    for r in (left, right):
        pygame.draw.rect(surface, (18, 18, 22), r, border_radius=18)
        pygame.draw.rect(surface, (230, 230, 230), r, 2, border_radius=18)

    surface.blit(ui_font_title.render("Setting + Goal", True, (245, 245, 245)), (left.x + 18, left.y + 16))
    left_lines = [
        "You are a stray cat moving through different parts of the city.",
        "At first, explore every scene to understand the world.",
        "After that, minigame encounters can appear.",
        "Clear higher levels, protect your hearts, and eventually reach Crossroads Shelter.",
        "There, your choices decide whether the cat keeps wandering, survives rescue, or finds a home."
    ]
    yy = left.y + 56
    for line in left_lines:
        wrapped = wrap_text_lines(line, ui_font, left.w - 36)
        for ln in wrapped:
            surface.blit(ui_font.render(ln, True, (225, 225, 225)), (left.x + 18, yy))
            yy += 26
        yy += 8

    surface.blit(ui_font_title.render("How Tokens Work", True, (245, 245, 245)), (right.x + 18, right.y + 16))
    right_lines = [
        "Winning a minigame gives tokens tied to that minigame type.",
        "If you clear Level 1, you get 1 Tier 1 token. If you clear Level 2, you get 2 Tier 1 tokens, and so on.",
        "Tokens are useful because they unlock stronger choices in Crossroads Shelter.",
        "Use 2 matching tokens at the forge machine to try making a higher-tier token.",
        "Use tokens for rescue paths and to donate for better adoption chances.",
        "Without tokens, the player loses access to the stronger routes."
    ]
    yy = right.y + 56
    for line in right_lines:
        wrapped = wrap_text_lines(line, ui_font, right.w - 36)
        for ln in wrapped:
            surface.blit(ui_font.render(ln, True, (225, 225, 225)), (right.x + 18, yy))
            yy += 26
        yy += 8

    footer = pygame.Rect(panel.x + 24, panel.bottom - 84, panel.w - 48, 52)
    pygame.draw.rect(surface, (0, 0, 0), footer, border_radius=14)
    pygame.draw.rect(surface, (245, 245, 245), footer, 2, border_radius=14)
    footer_text = ui_font.render(
        "Press ENTER or SPACE to begin. Press ESC anytime to close windows or quit a final screen.",
        True,
        (245, 245, 245)
    )
    surface.blit(footer_text, footer_text.get_rect(center=footer.center))


# ---------------------------
# DEATH SCREEN
# ---------------------------
def draw_fallback_dead_cat(surface, center):
    x, y = center
    body = pygame.Rect(0, 0, 160, 82)
    body.center = (x, y)
    pygame.draw.ellipse(surface, (235, 235, 235), body)
    pygame.draw.ellipse(surface, (20, 20, 20), body, 3)

    head = pygame.Rect(0, 0, 72, 62)
    head.center = (x, y - 52)
    pygame.draw.ellipse(surface, (235, 235, 235), head)
    pygame.draw.ellipse(surface, (20, 20, 20), head, 3)

    ear1 = [(head.left + 12, head.top + 12), (head.left + 24, head.top - 18), (head.left + 36, head.top + 16)]
    ear2 = [(head.right - 12, head.top + 12), (head.right - 24, head.top - 18), (head.right - 36, head.top + 16)]
    pygame.draw.polygon(surface, (235, 235, 235), ear1)
    pygame.draw.polygon(surface, (235, 235, 235), ear2)
    pygame.draw.polygon(surface, (20, 20, 20), ear1, 3)
    pygame.draw.polygon(surface, (20, 20, 20), ear2, 3)

    pygame.draw.line(surface, (20, 20, 20), (head.centerx - 18, head.centery - 5), (head.centerx - 6, head.centery + 7), 3)
    pygame.draw.line(surface, (20, 20, 20), (head.centerx - 18, head.centery + 7), (head.centerx - 6, head.centery - 5), 3)
    pygame.draw.line(surface, (20, 20, 20), (head.centerx + 6, head.centery - 5), (head.centerx + 18, head.centery + 7), 3)
    pygame.draw.line(surface, (20, 20, 20), (head.centerx + 6, head.centery + 7), (head.centerx + 18, head.centery - 5), 3)

    pygame.draw.arc(surface, (20, 20, 20), (head.centerx - 10, head.centery + 10, 20, 14), math.pi, 2 * math.pi, 2)

    for off in (-26, -10, 10, 26):
        pygame.draw.line(surface, (20, 20, 20), (x + off, y + 30), (x + off - 6, y + 52), 3)

    pygame.draw.line(surface, (20, 20, 20), (body.right - 4, body.centery + 8), (body.right + 44, body.centery + 34), 4)


def build_dead_cat_surface():
    temp = pygame.Surface((280, 240), pygame.SRCALPHA)
    draw_fallback_dead_cat(temp, (140, 120))
    return pygame.transform.rotate(temp, 180)


def draw_death_screen(surface):
    overlay = pygame.Surface((1200, 800), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    surface.blit(overlay, (0, 0))

    big = pygame.font.SysFont(None, 74)
    small = pygame.font.SysFont(None, 32)

    dead_cat = build_dead_cat_surface()
    surface.blit(dead_cat, dead_cat.get_rect(center=(600, 285)))

    t1 = big.render("The cat died.", True, (245, 245, 245))
    t2 = small.render("The streets were too cruel this time.", True, (220, 220, 220))
    t3 = small.render("Press ESC to quit.", True, (220, 220, 220))

    surface.blit(t1, t1.get_rect(center=(600, 510)))
    surface.blit(t2, t2.get_rect(center=(600, 565)))
    surface.blit(t3, t3.get_rect(center=(600, 615)))


# ---------------------------
# ADOPTED ENDING SCREEN
# ---------------------------
confetti_particles = []


def init_confetti(count=140):
    global confetti_particles
    confetti_particles = []
    for _ in range(count):
        confetti_particles.append({
            "x": random.randint(0, 1200),
            "y": random.randint(-800, 800),
            "w": random.randint(6, 12),
            "h": random.randint(10, 18),
            "vy": random.uniform(1.2, 3.6),
            "drift": random.uniform(-0.8, 0.8),
            "rot": random.randint(-25, 25),
            "color": random.choice([
                (255, 220, 120),
                (255, 170, 180),
                (180, 235, 255),
                (210, 255, 190),
                (245, 245, 245),
                (255, 205, 140)
            ])
        })


def update_confetti():
    for p in confetti_particles:
        p["y"] += p["vy"]
        p["x"] += p["drift"]

        if p["y"] > 840:
            p["y"] = random.randint(-120, -20)
            p["x"] = random.randint(0, 1200)


def draw_confetti(surface):
    for p in confetti_particles:
        rect_surf = pygame.Surface((p["w"], p["h"]), pygame.SRCALPHA)
        pygame.draw.rect(rect_surf, p["color"], (0, 0, p["w"], p["h"]), border_radius=3)
        rect_surf = pygame.transform.rotate(rect_surf, p["rot"])
        surface.blit(rect_surf, rect_surf.get_rect(center=(int(p["x"]), int(p["y"]))))


def draw_family_group(surface, center_x=600, base_y=560):
    pygame.draw.ellipse(surface, (255, 240, 210), (center_x - 250, base_y - 30, 500, 90))
    pygame.draw.ellipse(surface, (255, 255, 255), (center_x - 250, base_y - 30, 500, 90), 2)

    # left adult
    pygame.draw.circle(surface, (40, 40, 50), (center_x - 155, base_y - 150), 28)
    pygame.draw.rect(surface, (40, 40, 50), (center_x - 183, base_y - 122, 56, 105), border_radius=22)
    pygame.draw.line(surface, (40, 40, 50), (center_x - 170, base_y - 15), (center_x - 180, base_y + 55), 7)
    pygame.draw.line(surface, (40, 40, 50), (center_x - 140, base_y - 15), (center_x - 130, base_y + 55), 7)
    pygame.draw.line(surface, (40, 40, 50), (center_x - 183, base_y - 85), (center_x - 225, base_y - 25), 7)
    pygame.draw.line(surface, (40, 40, 50), (center_x - 127, base_y - 85), (center_x - 85, base_y - 15), 7)

    # right adult
    pygame.draw.circle(surface, (40, 40, 50), (center_x + 155, base_y - 150), 28)
    pygame.draw.rect(surface, (40, 40, 50), (center_x + 127, base_y - 122, 56, 105), border_radius=22)
    pygame.draw.line(surface, (40, 40, 50), (center_x + 140, base_y - 15), (center_x + 130, base_y + 55), 7)
    pygame.draw.line(surface, (40, 40, 50), (center_x + 170, base_y - 15), (center_x + 180, base_y + 55), 7)
    pygame.draw.line(surface, (40, 40, 50), (center_x + 127, base_y - 85), (center_x + 85, base_y - 15), 7)
    pygame.draw.line(surface, (40, 40, 50), (center_x + 183, base_y - 85), (center_x + 225, base_y - 25), 7)

    # child
    pygame.draw.circle(surface, (55, 55, 70), (center_x, base_y - 128), 22)
    pygame.draw.rect(surface, (55, 55, 70), (center_x - 20, base_y - 106, 40, 76), border_radius=18)
    pygame.draw.line(surface, (55, 55, 70), (center_x - 9, base_y - 30), (center_x - 20, base_y + 28), 6)
    pygame.draw.line(surface, (55, 55, 70), (center_x + 9, base_y - 30), (center_x + 20, base_y + 28), 6)
    pygame.draw.line(surface, (55, 55, 70), (center_x - 20, base_y - 80), (center_x - 55, base_y - 45), 6)
    pygame.draw.line(surface, (55, 55, 70), (center_x + 20, base_y - 80), (center_x + 55, base_y - 45), 6)

    # cat
    cat_body = pygame.Rect(0, 0, 130, 72)
    cat_body.center = (center_x, base_y - 5)
    pygame.draw.ellipse(surface, (245, 245, 245), cat_body)
    pygame.draw.ellipse(surface, (40, 40, 50), cat_body, 3)

    cat_head = pygame.Rect(0, 0, 64, 56)
    cat_head.center = (center_x, base_y - 50)
    pygame.draw.ellipse(surface, (245, 245, 245), cat_head)
    pygame.draw.ellipse(surface, (40, 40, 50), cat_head, 3)

    ear1 = [(cat_head.left + 10, cat_head.top + 10), (cat_head.left + 22, cat_head.top - 14), (cat_head.left + 32, cat_head.top + 12)]
    ear2 = [(cat_head.right - 10, cat_head.top + 10), (cat_head.right - 22, cat_head.top - 14), (cat_head.right - 32, cat_head.top + 12)]
    pygame.draw.polygon(surface, (245, 245, 245), ear1)
    pygame.draw.polygon(surface, (245, 245, 245), ear2)
    pygame.draw.polygon(surface, (40, 40, 50), ear1, 3)
    pygame.draw.polygon(surface, (40, 40, 50), ear2, 3)

    pygame.draw.circle(surface, (40, 40, 50), (center_x - 12, base_y - 56), 3)
    pygame.draw.circle(surface, (40, 40, 50), (center_x + 12, base_y - 56), 3)
    pygame.draw.arc(surface, (40, 40, 50), (center_x - 12, base_y - 44, 24, 16), math.pi, 2 * math.pi, 2)

    for off in (-22, -8, 8, 22):
        pygame.draw.line(surface, (40, 40, 50), (center_x + off, base_y + 18), (center_x + off - 4, base_y + 34), 3)

    pygame.draw.line(surface, (40, 40, 50), (cat_body.right - 6, cat_body.centery + 5), (cat_body.right + 34, cat_body.centery - 22), 4)

    pygame.draw.circle(surface, (255, 170, 190), (center_x - 10, base_y - 105), 10)
    pygame.draw.circle(surface, (255, 170, 190), (center_x + 10, base_y - 105), 10)
    pygame.draw.polygon(surface, (255, 170, 190), [
        (center_x - 22, base_y - 100),
        (center_x + 22, base_y - 100),
        (center_x, base_y - 70)
    ])


def draw_adopted_ending_screen(surface):
    for y in range(800):
        t = y / 799.0
        r = int(255 - 35 * t)
        g = int(232 - 52 * t)
        b = int(205 - 75 * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (1200, y))

    glow = pygame.Surface((1200, 800), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (255, 255, 255, 70), (180, 70, 840, 430))
    pygame.draw.ellipse(glow, (255, 240, 220, 50), (80, 120, 1040, 520))
    surface.blit(glow, (0, 0))

    update_confetti()
    draw_confetti(surface)
    draw_family_group(surface, 600, 570)

    card = pygame.Rect(250, 70, 700, 150)
    card_surf = pygame.Surface((card.w, card.h), pygame.SRCALPHA)
    card_surf.fill((255, 255, 255, 105))
    surface.blit(card_surf, card.topleft)
    pygame.draw.rect(surface, (255, 255, 255), card, 2, border_radius=20)

    title_font = pygame.font.SysFont(None, 76)
    sub_font = pygame.font.SysFont(None, 32)
    tip_font = pygame.font.SysFont(None, 28)

    t1 = title_font.render("You found a home.", True, (60, 45, 35))
    t2 = sub_font.render("No longer a stray, now part of a loving family.", True, (75, 60, 50))
    t3 = tip_font.render("Confetti falls, hearts gather, and a new life begins. Press ESC to quit.", True, (85, 70, 58))

    surface.blit(t1, t1.get_rect(center=(600, 115)))
    surface.blit(t2, t2.get_rect(center=(600, 165)))
    surface.blit(t3, t3.get_rect(center=(600, 205)))


# ---------------------------
# Encounter setup
# ---------------------------
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


def award_tokens_for_win(minigame_type: str, cleared_level: int):
    inv_add(minigame_type, tier=1, amount=int(cleared_level))
    award_adoption_progress_from_win(cleared_level)


ensure_neuter_batch()
init_confetti()

# ---------------------------
# MAIN LOOP
# ---------------------------
while True:
    now_ms = pygame.time.get_ticks()
    machine_ui_hit = None
    adopt_ui_hit = None

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

        if show_intro_overlay:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                show_intro_overlay = False
            continue

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if inv_btn_rect.collidepoint(event.pos):
                inventory_open = not inventory_open
                if inventory_open:
                    notifications_panel_open = False
                continue

            if notif_btn_rect.collidepoint(event.pos):
                notifications_panel_open = not notifications_panel_open
                if notifications_panel_open:
                    inventory_open = False
                continue

        if machine_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                machine_ui_hit = ("mouse_down", event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                machine_ui_hit = ("mouse_up", event.pos)
            elif event.type == pygame.MOUSEMOTION and machine_ui_dragging:
                mx, my = event.pos
                ox, oy = machine_ui_drag_offset
                machine_ui_pos[0] = mx - ox
                machine_ui_pos[1] = my - oy

        if adoption_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                adopt_ui_hit = ("mouse_down", event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                adopt_ui_hit = ("mouse_up", event.pos)
            elif event.type == pygame.MOUSEMOTION and adopt_ui_dragging:
                mx, my = event.pos
                ox, oy = adopt_ui_drag_offset
                adopt_ui_pos[0] = mx - ox
                adopt_ui_pos[1] = my - oy

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                if currentscene == 5:
                    if player_is_near_machine(characteranimation.player_x) and not adoption_open:
                        machine_open = not machine_open
                        machine_ui_dragging = False
                        if machine_open:
                            center_machine_ui()
                            inventory_open = False
                            notifications_panel_open = False

                    elif player_is_near_shelter(characteranimation.player_x) and not machine_open:
                        adoption_open = not adoption_open
                        adopt_ui_dragging = False
                        if adoption_open:
                            center_adoption_ui()
                            inventory_open = False
                            notifications_panel_open = False

            if event.key == pygame.K_ESCAPE:
                if machine_open:
                    machine_open = False
                    machine_ui_dragging = False
                elif adoption_open:
                    adoption_open = False
                    adopt_ui_dragging = False
                elif inventory_open:
                    inventory_open = False
                elif notifications_panel_open:
                    notifications_panel_open = False

    if show_intro_overlay:
        screen.fill((8, 8, 10))
        draw_intro_overlay(screen)
        pygame.display.update()
        clock.tick(30)
        continue

    keys = pygame.key.get_pressed()

    if not machine_open and not adoption_open:
        characteranimation.update_character_logic(keys)

    can_switch = (
        (not dog_triggered)
        and (not match3_triggered)
        and (not maze_triggered)
        and (not jump_triggered)
        and (now_ms >= scene_switch_lock_until_ms)
        and (not machine_open)
        and (not adoption_open)
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

                    cleared_level = match3_level
                    result = match3_minigame.run_match3_minigame(match3_level)

                    if result == "win":
                        award_tokens_for_win("match3", cleared_level)
                        match3_level += 1
                        push_notification(f"Match-3 win. +{cleared_level} token(s)")
                    else:
                        apply_full_heart_damage()
                        push_notification("Match-3 failed. -1 heart")

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

                    cleared_level = dog_level
                    result = dogminigame.run_dog_minigame(dog_level)

                    if result == "win":
                        award_tokens_for_win("dog", cleared_level)
                        dog_level += 1
                        push_notification(f"Dog win. +{cleared_level} token(s)")
                    else:
                        apply_full_heart_damage()
                        push_notification("Dog failed. -1 heart")

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

                    cleared_level = maze_level
                    result = maze_minigame.run_maze_minigame(
                        window_size=(1200, 800),
                        caption="Maze Minigame",
                        level=maze_level
                    )

                    if result == "win":
                        award_tokens_for_win("maze", cleared_level)
                        maze_level += 1
                        push_notification(f"Maze win. +{cleared_level} token(s)")
                    else:
                        apply_full_heart_damage()
                        push_notification("Maze failed. -1 heart")

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

                    cleared_level = jump_level
                    result = jump_charge_minigame.run_jump_minigame(level=jump_level)

                    if result == "win":
                        award_tokens_for_win("jump", cleared_level)
                        jump_level += 1
                        push_notification(f"Jumpers win. +{cleared_level} token(s)")
                    else:
                        apply_full_heart_damage()
                        push_notification("Jumpers failed. -1 heart")

                    jump_cleared_this_visit = True
                    jump_triggered = False
                    jump_started = False
                    restore_player_position_after_minigame()

                    screen = pygame.display.set_mode((1200, 800))
                    pygame.display.set_caption("Runner")

    elif currentscene == 5:
        screen.blit(background5, (0, 0))
        draw_story_overlay_bottom(screen)

        draw_shelter_booth(screen, characteranimation.player_x)
        draw_stylish_machine(screen, characteranimation.player_x)

        ui_layout = draw_machine_ui(screen)
        if machine_open and machine_ui_hit and ui_layout:
            action, pos = machine_ui_hit

            if action == "mouse_down":
                if ui_layout["header"].collidepoint(pos):
                    machine_ui_dragging = True
                    mx, my = pos
                    ox = mx - ui_layout["panel"].x
                    oy = my - ui_layout["panel"].y
                    machine_ui_drag_offset = (ox, oy)
                else:
                    if ui_layout["close_btn"].collidepoint(pos):
                        machine_open = False
                        machine_ui_dragging = False
                    elif ui_layout["combine_btn"].collidepoint(pos):
                        machine_do_combine(machine_selected_type, machine_selected_tier)
                    else:
                        for t, r in ui_layout["type_btns"].items():
                            if r.collidepoint(pos):
                                machine_selected_type = t
                                tiers = sorted(int(k) for k, v in inventory.get(machine_selected_type, {}).items() if int(v) > 0)
                                machine_selected_tier = tiers[0] if tiers else 1
                                break
                        for tier, r in ui_layout["tier_btns"].items():
                            if r.collidepoint(pos):
                                machine_selected_tier = int(tier)
                                break

            elif action == "mouse_up":
                machine_ui_dragging = False

        adopt_layout = draw_adoption_ui(screen)
        if adoption_open and adopt_ui_hit and adopt_layout:
            action, pos = adopt_ui_hit

            if action == "mouse_down":
                if adopt_layout["header"].collidepoint(pos):
                    adopt_ui_dragging = True
                    mx, my = pos
                    ox = mx - adopt_layout["panel"].x
                    oy = my - adopt_layout["panel"].y
                    adopt_ui_drag_offset = (ox, oy)
                else:
                    btns = adopt_layout["btns"]

                    if "close_btn" in btns and btns["close_btn"].collidepoint(pos):
                        adoption_open = False
                        adopt_ui_dragging = False

                    if "refresh_btn" in btns and btns["refresh_btn"].collidepoint(pos):
                        refresh_neuter_batch()

                    if "prog1" in btns and btns["prog1"].collidepoint(pos):
                        out = do_neuter_program(1)
                        if out == "fail":
                            apply_full_heart_damage()
                            push_notification("Neutering failed. -1 heart")

                    if "prog2" in btns and btns["prog2"].collidepoint(pos):
                        out = do_neuter_program(2)
                        if out == "fail":
                            apply_full_heart_damage()
                            push_notification("Neutering failed. -1 heart")

                    if "prog3" in btns and btns["prog3"].collidepoint(pos):
                        out = do_neuter_program(3)
                        if out == "fail":
                            apply_full_heart_damage()
                            push_notification("Neutering failed. -1 heart")

                    if "prog4" in btns and btns["prog4"].collidepoint(pos):
                        out = do_neuter_program(4)
                        if out == "fail":
                            apply_full_heart_damage()
                            push_notification("Neutering failed. -1 heart")

                    if "try_adopt" in btns and btns["try_adopt"].collidepoint(pos):
                        if try_adoption_roll():
                            push_notification("Adopted. You win!")
                        else:
                            apply_full_heart_damage()
                            push_notification("Not adopted yet. -1 heart")

                    if "type_rects" in btns:
                        for t, r in btns["type_rects"].items():
                            if r.collidepoint(pos):
                                adopt_selected_type = t
                                break

                    if "tier_rects" in btns:
                        for tier, r in btns["tier_rects"].items():
                            if r.collidepoint(pos):
                                adopt_selected_tier = int(tier)
                                break

                    if "donate_btn" in btns and btns["donate_btn"].collidepoint(pos):
                        ok = donate_tokens_for_adoption(adopt_selected_type, adopt_selected_tier, 1)
                        if ok:
                            bonus = DONATION_BONUS_BY_TIER.get(adopt_selected_tier, 0)
                            push_notification(f"Donation accepted. Adoption chance +{bonus}%.")
                        else:
                            push_notification("Not enough tokens to donate.")

            elif action == "mouse_up":
                adopt_ui_dragging = False

    characteranimation.draw_character(screen)
    healthbar.draw_healthbar(screen, health)

    draw_quests(screen)
    draw_inventory_button(screen)
    draw_notification_button(screen)
    draw_inventory_panel(screen)
    draw_notifications_panel(screen)
    draw_notifications(screen)

    if health <= 0:
        draw_death_screen(screen)
        pygame.display.update()

        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
            clock.tick(30)

    if adopted:
        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()

            draw_adopted_ending_screen(screen)
            pygame.display.update()
            clock.tick(30)

    pygame.display.update()
    clock.tick(characteranimation.current_FPS)
