# jump_charge_minigame.py
#
# Jumpers (Level-based)
#
# Rules:
# - Level 1: 5 platforms total (including start), big and easy.
# - Level 2: 10 platforms total, the extra 5 are smaller.
# - Level 3: 15 platforms total, etc.
# - Distances are random but always reachable.
# - If you miss a platform: cat falls down fully, then game ends ("lose").
# - Win: land on the final platform, show win message, return "win".
#
# Controls:
#   Hold SPACE / Left Mouse = aim (45° line oscillates)
#   Release = jump
#   ESC = quit (lose)

import pygame
import random
import math

WIDTH, HEIGHT = 1200, 800
FPS = 60

GROUND_Y = 620

BG = (16, 18, 24)
TEXT = (240, 240, 240)
SUBTEXT = (200, 200, 200)

# Street palette
ROAD_DARK = (42, 44, 48)
ROAD_MID = (56, 58, 64)
ROAD_LIGHT = (76, 78, 84)
GRIME_1 = (34, 36, 40)
GRIME_2 = (66, 60, 54)
LINE_PAINT = (170, 160, 90)
SHADOW = (0, 0, 0)

# Jump feel (floaty)
MIN_ARC_H = 120
MAX_ARC_H = 320

JUMP_DUR_MIN = 0.75
JUMP_DUR_MAX = 1.05
ARC_POWER = 0.70

# Oscillating aim line (controls jump)
PREVIEW_MIN = 80
PREVIEW_MAX = 420
PREVIEW_SPEED = 0.60
PREVIEW_ANGLE_RAD = math.radians(45)
COS_45 = math.cos(PREVIEW_ANGLE_RAD)

MOUSE_AIM_ENABLED = True

# Camera
CAM_SMOOTH = 7.5
CAM_TARGET_LEFT_PADDING = 170

# Level platform rules
BASE_PLATFORMS = 5
EXTRA_PER_LEVEL = 5

# Platform widths: big to small by tier
PLAT_W_BIG_MIN = 240
PLAT_W_BIG_MAX = 340

PLAT_W_MIN_CAP = 90
PLAT_W_DECAY_PER_TIER = 28
PLAT_H = 34

# Gap control
REACH_MARGIN = 55
GAP_MIN = 120
GAP_MAX_CAP = 520

# Minimap
MINIMAP_H = 70
MINIMAP_MARGIN = 14
MINIMAP_BG = (0, 0, 0, 120)
MINIMAP_PLATFORM = (120, 150, 210)
MINIMAP_GOAL = (255, 120, 160)
MINIMAP_PLAYER = (255, 220, 140)

# Cat sprite
CAT_SIZE = 72

# End message pause
END_MSG_SECONDS = 1.2

# Falling animation
FALL_GRAVITY = 1800.0  # px/s^2
FALL_DRAG_X = 0.0      # keep 0 unless you want drift


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def exp_smooth(current, target, dt, speed):
    k = 1.0 - math.exp(-speed * dt)
    return current + (target - current) * k


def length_to_jump_distance(line_length):
    return COS_45 * line_length


def length_to_arc_height(line_length):
    t = (line_length - PREVIEW_MIN) / max(1.0, (PREVIEW_MAX - PREVIEW_MIN))
    t = clamp(t, 0.0, 1.0)
    t = t ** 0.9
    return lerp(MIN_ARC_H, MAX_ARC_H, t)


def length_to_jump_duration(line_length):
    t = (line_length - PREVIEW_MIN) / max(1.0, (PREVIEW_MAX - PREVIEW_MIN))
    t = clamp(t, 0.0, 1.0)
    t = t ** 0.9
    return lerp(JUMP_DUR_MIN, JUMP_DUR_MAX, t)


def landing_platform_index(platforms, px_world):
    """
    EDGES ARE SAFE:
    Any x in [left, right] counts as landed.
    """
    for i, r in enumerate(platforms):
        if r.left <= px_world <= r.right:
            return i
    return None


def platform_count_for_level(level):
    level = max(1, int(level))
    return BASE_PLATFORMS + (level - 1) * EXTRA_PER_LEVEL


def width_range_for_index(i):
    tier = i // EXTRA_PER_LEVEL
    shrink = tier * PLAT_W_DECAY_PER_TIER

    w_min = max(PLAT_W_MIN_CAP, PLAT_W_BIG_MIN - shrink)
    w_max = max(w_min + 20, PLAT_W_BIG_MAX - shrink)
    return int(w_min), int(w_max)


def generate_next_platform(rng, prev_rect, i):
    d_min = length_to_jump_distance(PREVIEW_MIN)
    d_max = length_to_jump_distance(PREVIEW_MAX)

    reachable_min = d_min + 25
    reachable_max = d_max - REACH_MARGIN
    if reachable_max <= reachable_min + 40:
        reachable_max = reachable_min + 40

    w_min, w_max = width_range_for_index(i)
    w = rng.randint(w_min, w_max)

    takeoff_x = prev_rect.right - 18

    target_dist = rng.randint(int(reachable_min), int(reachable_max))
    target_dist = int(clamp(target_dist, GAP_MIN, GAP_MAX_CAP))

    target_x = takeoff_x + target_dist

    left = int(target_x - w * rng.uniform(0.35, 0.65))

    min_left = prev_rect.right + GAP_MIN
    if left < min_left:
        left = min_left

    max_left = prev_rect.right + GAP_MAX_CAP
    if left > max_left:
        left = max_left

    return pygame.Rect(left, GROUND_Y, w, PLAT_H)


def draw_trashy_platform(screen, rr, seed_key):
    pygame.draw.rect(screen, ROAD_MID, rr, border_radius=10)
    pygame.draw.rect(screen, SHADOW, rr, 2, border_radius=10)

    inner = rr.inflate(-6, -6)
    pygame.draw.rect(screen, ROAD_DARK, inner, border_radius=9)

    local = random.Random(seed_key)

    if local.random() < 0.55:
        stripe_w = max(10, rr.w // 10)
        stripe = pygame.Rect(rr.x + rr.w // 2 - stripe_w // 2, rr.y + 6, stripe_w, rr.h - 12)
        for _ in range(3):
            off = local.randint(-3, 3)
            sw = max(6, stripe.w + local.randint(-4, 4))
            faded = pygame.Rect(stripe.x + off, stripe.y + local.randint(-2, 2), sw, stripe.h)
            pygame.draw.rect(screen, LINE_PAINT, faded, border_radius=6)

    crack_count = 4 + local.randint(0, 4)
    for _ in range(crack_count):
        x0 = local.randint(rr.x + 10, rr.right - 10)
        y0 = local.randint(rr.y + 8, rr.bottom - 8)
        points = [(x0, y0)]
        segs = local.randint(3, 6)
        for __ in range(segs):
            x0 += local.randint(-18, 18)
            y0 += local.randint(-8, 8)
            x0 = clamp(x0, rr.x + 6, rr.right - 6)
            y0 = clamp(y0, rr.y + 6, rr.bottom - 6)
            points.append((x0, y0))
        pygame.draw.lines(screen, GRIME_1, False, points, 2)

    stain_count = 2 + local.randint(0, 3)
    for _ in range(stain_count):
        cx = local.randint(rr.x + 16, rr.right - 16)
        cy = local.randint(rr.y + 10, rr.bottom - 10)
        rad = local.randint(10, 22)
        col = GRIME_2 if local.random() < 0.5 else GRIME_1
        pygame.draw.circle(screen, col, (cx, cy), rad)

    litter = 3 + local.randint(0, 5)
    for _ in range(litter):
        lx = local.randint(rr.x + 10, rr.right - 10)
        ly = local.randint(rr.y + 10, rr.bottom - 10)
        if local.random() < 0.5:
            pygame.draw.circle(screen, ROAD_LIGHT, (lx, ly), local.randint(2, 4))
        else:
            tri = [
                (lx, ly),
                (lx + local.randint(-6, 6), ly + local.randint(4, 10)),
                (lx + local.randint(4, 10), ly + local.randint(-4, 6)),
            ]
            pygame.draw.polygon(screen, ROAD_LIGHT, tri)


def draw_platforms_main_view(screen, platforms, camera_x, goal_i):
    for i, r in enumerate(platforms):
        rr = pygame.Rect(r.x - camera_x, r.y, r.w, r.h)
        draw_trashy_platform(screen, rr, seed_key=(r.x * 92821 + r.w * 193 + i * 991))

        if i == goal_i:
            gx, gy = rr.centerx, rr.y - 16
            pygame.draw.circle(screen, MINIMAP_GOAL, (gx, gy), 9)
            pygame.draw.line(screen, MINIMAP_GOAL, (gx, gy + 9), (gx, rr.y + 3), 4)


def draw_minimap(screen, platforms, px_world, goal_i):
    world_left = platforms[0].left
    world_right = max(r.right for r in platforms)
    world_w = max(1, world_right - world_left)

    mm_x = MINIMAP_MARGIN
    mm_y = MINIMAP_MARGIN
    mm_w = WIDTH - MINIMAP_MARGIN * 2
    mm_h = MINIMAP_H

    panel = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
    panel.fill(MINIMAP_BG)
    screen.blit(panel, (mm_x, mm_y))
    pygame.draw.rect(screen, (255, 255, 255), (mm_x, mm_y, mm_w, mm_h), 1, border_radius=10)

    def wx_to_mx(wx):
        t = (wx - world_left) / world_w
        return mm_x + int(t * mm_w)

    for i, r in enumerate(platforms):
        x1 = wx_to_mx(r.left)
        x2 = wx_to_mx(r.right)
        y = mm_y + 22
        h = 22
        col = MINIMAP_GOAL if i == goal_i else MINIMAP_PLATFORM
        pygame.draw.rect(screen, col, (x1, y, max(3, x2 - x1), h), border_radius=6)

    p_mx = wx_to_mx(px_world)
    base_y = mm_y + 54
    pygame.draw.polygon(
        screen,
        MINIMAP_PLAYER,
        [(p_mx, base_y - 12), (p_mx - 8, base_y), (p_mx + 8, base_y)],
    )


def show_end_message(screen, clock, big_font, msg, color):
    end_start = pygame.time.get_ticks()
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        text_surf = big_font.render(msg, True, color)
        rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(text_surf, rect)

        pygame.display.flip()

        if (pygame.time.get_ticks() - end_start) >= int(END_MSG_SECONDS * 1000):
            return


def run_jump_minigame(level=1):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Jumpers (Level {level})")
    clock = pygame.time.Clock()

    cat_img = pygame.image.load("cathead.png").convert_alpha()
    cat_img = pygame.transform.smoothscale(cat_img, (CAT_SIZE, CAT_SIZE))

    font = pygame.font.SysFont(None, 28)
    big = pygame.font.SysFont(None, 48)

    rng = random.Random()

    total_platforms = platform_count_for_level(level)
    goal_i = total_platforms - 1

    platforms = []
    start_rect = pygame.Rect(120, GROUND_Y, 320, PLAT_H)
    platforms.append(start_rect)

    while len(platforms) < total_platforms:
        platforms.append(generate_next_platform(rng, platforms[-1], len(platforms)))

    px = start_rect.right - 60
    py = start_rect.y - CAT_SIZE

    camera_x = max(0.0, px - CAM_TARGET_LEFT_PADDING)

    state = "idle"  # idle, aiming, jumping, falling
    jump_t = 0.0
    jump_dur = 0.9
    jump_from_x = px
    jump_to_x = px
    arc_h = 200

    # Falling physics
    fall_vy = 0.0
    fall_vx = 0.0

    landed_index = 0

    t_osc = 0.0
    line_len = PREVIEW_MIN

    msg = "Hold SPACE to aim. Release to jump."
    tip = f"Level {int(level)}: {total_platforms} platforms. Falling ends the run."

    while True:
        dt = clock.tick(FPS) / 1000.0
        t_osc += dt

        osc01 = (math.sin(t_osc * PREVIEW_SPEED * math.pi * 2) + 1.0) / 2.0
        current_len = lerp(PREVIEW_MIN, PREVIEW_MAX, osc01)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                show_end_message(screen, clock, big, "You've fallen.", (255, 140, 140))
                return "lose"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    show_end_message(screen, clock, big, "You've fallen.", (255, 140, 140))
                    return "lose"
                if event.key == pygame.K_SPACE and state == "idle":
                    state = "aiming"

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE and state == "aiming":
                    line_len = current_len
                    dist = length_to_jump_distance(line_len)

                    arc_h = length_to_arc_height(line_len)
                    jump_dur = length_to_jump_duration(line_len)

                    jump_from_x = px
                    jump_to_x = px + dist
                    jump_t = 0.0
                    state = "jumping"

            if MOUSE_AIM_ENABLED:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if state == "idle":
                        state = "aiming"
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if state == "aiming":
                        line_len = current_len
                        dist = length_to_jump_distance(line_len)

                        arc_h = length_to_arc_height(line_len)
                        jump_dur = length_to_jump_duration(line_len)

                        jump_from_x = px
                        jump_to_x = px + dist
                        jump_t = 0.0
                        state = "jumping"

        if state == "aiming":
            line_len = current_len

        elif state == "jumping":
            jump_t += dt / max(0.001, jump_dur)
            t = clamp(jump_t, 0.0, 1.0)

            px = lerp(jump_from_x, jump_to_x, ease_out_cubic(t))

            t_shaped = t ** ARC_POWER
            arc = 4 * t_shaped * (1 - t_shaped)
            py = (GROUND_Y - CAT_SIZE) - arc_h * arc

            if t >= 1.0:
                idx = landing_platform_index(platforms, px)
                if idx is None:
                    # Start falling (do NOT show message yet)
                    state = "falling"
                    fall_vy = 0.0
                    fall_vx = 0.0
                else:
                    r = platforms[idx]
                    # edges still safe, but keep player inside visually
                    px = clamp(px, r.left, r.right)
                    py = r.y - CAT_SIZE
                    landed_index = max(landed_index, idx)

                    if landed_index >= goal_i:
                        show_end_message(screen, clock, big, "You made it!", (140, 255, 160))
                        return "win"

                    state = "idle"

        elif state == "falling":
            # Let the cat fall all the way down before message appears
            fall_vy += FALL_GRAVITY * dt
            py += fall_vy * dt

            if FALL_DRAG_X != 0.0:
                # optional tiny drift
                fall_vx = exp_smooth(fall_vx, 0.0, dt, FALL_DRAG_X)
                px += fall_vx * dt

            if py > HEIGHT + CAT_SIZE + 40:
                show_end_message(screen, clock, big, "You've fallen.", (255, 140, 140))
                return "lose"

        cam_target = max(0.0, px - CAM_TARGET_LEFT_PADDING)
        camera_x = exp_smooth(camera_x, cam_target, dt, CAM_SMOOTH)

        # DRAW
        screen.fill(BG)

        draw_minimap(screen, platforms, px, goal_i)

        screen.blit(big.render("Jumpers", True, TEXT), (18, 96))
        screen.blit(font.render(msg, True, SUBTEXT), (20, 150))
        screen.blit(font.render(tip, True, (180, 180, 180)), (20, 176))

        prog = f"Platform: {min(landed_index + 1, total_platforms)}/{total_platforms}"
        screen.blit(font.render(prog, True, (210, 210, 210)), (20, 206))

        draw_platforms_main_view(screen, platforms, camera_x, goal_i)

        if state == "aiming":
            length = line_len
            dx = math.cos(PREVIEW_ANGLE_RAD) * length
            dy = -math.sin(PREVIEW_ANGLE_RAD) * length

            sx_world, sy_world = px, py + 12
            ex_world, ey_world = px + dx, sy_world + dy

            sx = int(sx_world - camera_x)
            sy = int(sy_world)
            ex = int(ex_world - camera_x)
            ey = int(ey_world)

            pygame.draw.line(screen, (255, 255, 255), (sx, sy), (ex, ey), 3)
            pygame.draw.circle(screen, (255, 255, 255), (ex, ey), 6, 2)

        cat_x = int(px - camera_x - CAT_SIZE // 2)
        cat_y = int(py)
        screen.blit(cat_img, (cat_x, cat_y))

        pygame.display.flip()


if __name__ == "__main__":
    print(run_jump_minigame(level=1))
