import random
import pygame
import math
from collections import deque

# ============================================================
# Match-3 Fish Minigame
# Entry point: run_match3_minigame(level=1) -> "win" or "lose"
#
# Needs files (same folder):
#   fish blue.png
#   fish green.png
#   fish pink.png
#   fish purple.png
#   fish white.png
#   fish yellow.png
#   trash bag.png
#
# Level rules:
#   level 1: score >= 500, clear 20 of target fish color, dispose 3 trash
#   level 2+: score >= 700+, clear 20 of target fish color, dispose 3 trash
# ============================================================

GRID_W, GRID_H = 8, 8
TILE = 64
TOP_BAR = 120
SIDE_PANEL_W = 360

BOARD_W = GRID_W * TILE
BOARD_H = GRID_H * TILE

WIDTH = BOARD_W + SIDE_PANEL_W
HEIGHT = TOP_BAR + BOARD_H
FPS = 60

CANDY_TYPES = 6

BG = (16, 18, 24)
PANEL = (12, 14, 18)
GRID_BG = (20, 22, 30)
GRID_LINE = (36, 40, 52)

TEXT = (240, 240, 240)
SUBTEXT = (190, 190, 190)
DONE_GREEN = (80, 220, 120)

SWAP_DURATION = 0.16
DROP_SPEED_PX = 1200.0
DROP_STEP_DELAY = 0.06
CLEAR_PAUSE = 0.12
DROP_EASING = "smooth"

# Idle help: show a hint after 5 seconds without player input
IDLE_HELP_SECONDS = 5.0
HINT_SWAP_DURATION = 0.30         # slower hint swap
HINT_COOLDOWN_SECONDS = 2.0

# Five-in-a-row skill (rainbow ball) effect
RAINBOW_CONVERT_RATIO = 0.30      # 30% of board
RAINBOW_STEP_SECONDS = 1.0        # stop 1 second per tile conversion

ARROW_COLOR = (255, 255, 255)

BOARD_RECT = pygame.Rect(0, TOP_BAR, BOARD_W, BOARD_H)
SIDE_RECT = pygame.Rect(BOARD_W, 0, SIDE_PANEL_W, HEIGHT)


# -----------------------------
# Tile helpers
# -----------------------------
def make_tile(kind, color=None, extra=None):
    return (kind, color, extra)

def tile_kind(t): return t[0]
def tile_color(t): return t[1]
def tile_extra(t): return t[2]

def in_bounds(x, y):
    return 0 <= x < GRID_W and 0 <= y < GRID_H

def are_adjacent(a, b):
    ax, ay = a
    bx, by = b
    return abs(ax - bx) + abs(ay - by) == 1

def rand_color():
    return random.randrange(CANDY_TYPES)

def rand_normal():
    return make_tile("normal", rand_color(), None)

def cell_to_px(x, y):
    return x * TILE, TOP_BAR + y * TILE

def screen_to_cell(mx, my):
    if mx < 0 or mx >= BOARD_W:
        return None
    my -= TOP_BAR
    if my < 0 or my >= BOARD_H:
        return None
    x = mx // TILE
    y = my // TILE
    if in_bounds(x, y):
        return (x, y)
    return None

def striped_mode(extra):
    if not extra:
        return "row"
    dx, dy = extra
    if dy != 0 and dx == 0:
        return "col"
    return "row"

def base_match_color(tile):
    if tile is None:
        return None
    k = tile_kind(tile)
    if k in ("rainbow", "trash"):
        return None
    return tile_color(tile)

def swap_in_grid(grid, a, b):
    ax, ay = a
    bx, by = b
    grid[ay][ax], grid[by][bx] = grid[by][bx], grid[ay][ax]


# -----------------------------
# Animator (neat drop, no overlap)
# -----------------------------
class Animator:
    def __init__(self):
        self.active = []

    def add(self, tile, start_xy, end_xy, duration, easing, delay=0.0, dest_cell=None):
        self.active.append({
            "tile": tile,
            "start": start_xy,
            "end": end_xy,
            "t": 0.0,
            "dur": max(0.001, duration),
            "easing": easing,
            "delay": max(0.0, delay),
            "dest_cell": dest_cell
        })

    def add_swap(self, tile, start_xy, end_xy, duration):
        self.add(tile, start_xy, end_xy, duration, "smooth", delay=0.0, dest_cell=None)

    def add_drop(self, tile, start_xy, end_xy, speed_px, delay=0.0, dest_cell=None, easing="linear"):
        sx, sy = start_xy
        ex, ey = end_xy
        dist = math.hypot(ex - sx, ey - sy)
        dur = dist / max(1.0, speed_px)
        self.add(tile, start_xy, end_xy, dur, easing, delay=delay, dest_cell=dest_cell)

    def update(self, dt):
        done = []
        for i, a in enumerate(self.active):
            if a["delay"] > 0:
                a["delay"] -= dt
                continue
            a["t"] += dt
            if a["t"] >= a["dur"]:
                done.append(i)
        for i in reversed(done):
            self.active.pop(i)

    def is_busy(self):
        return len(self.active) > 0

    def dest_cells_in_flight(self):
        out = set()
        for a in self.active:
            if a["dest_cell"] is not None:
                out.add(a["dest_cell"])
        return out

    def draw_overrides(self):
        out = []
        for a in self.active:
            if a["delay"] > 0:
                continue
            p = min(1.0, a["t"] / a["dur"])
            if a["easing"] == "smooth":
                p = p * p * (3 - 2 * p)
            sx, sy = a["start"]
            ex, ey = a["end"]
            x = sx + (ex - sx) * p
            y = sy + (ey - sy) * p
            out.append((a["tile"], x, y))
        return out


# -----------------------------
# Loading sprites
# -----------------------------
def load_sprite(path):
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(img, (TILE - 16, TILE - 16))

def load_assets():
    fish = [
        load_sprite("fish blue.png"),
        load_sprite("fish green.png"),
        load_sprite("fish pink.png"),
        load_sprite("fish purple.png"),
        load_sprite("fish white.png"),
        load_sprite("fish yellow.png"),
    ]
    trash = load_sprite("trash bag.png")
    return fish, trash


# -----------------------------
# Matching / specials / clears
# -----------------------------
def find_runs(grid):
    matched = set()
    horiz_runs = []
    vert_runs = []

    for y in range(GRID_H):
        run = [(0, y)]
        for x in range(1, GRID_W):
            c1 = base_match_color(grid[y][x])
            c0 = base_match_color(grid[y][x - 1])
            if c1 is not None and c1 == c0:
                run.append((x, y))
            else:
                if len(run) >= 3:
                    horiz_runs.append(run[:])
                    matched.update(run)
                run = [(x, y)]
        if len(run) >= 3:
            horiz_runs.append(run[:])
            matched.update(run)

    for x in range(GRID_W):
        run = [(x, 0)]
        for y in range(1, GRID_H):
            c1 = base_match_color(grid[y][x])
            c0 = base_match_color(grid[y - 1][x])
            if c1 is not None and c1 == c0:
                run.append((x, y))
            else:
                if len(run) >= 3:
                    vert_runs.append(run[:])
                    matched.update(run)
                run = [(x, y)]
        if len(run) >= 3:
            vert_runs.append(run[:])
            matched.update(run)

    return matched, horiz_runs, vert_runs

def make_grid_no_initial_matches():
    g = [[rand_normal() for _ in range(GRID_W)] for _ in range(GRID_H)]
    while True:
        m, _, _ = find_runs(g)
        if not m:
            break
        for (x, y) in m:
            g[y][x] = rand_normal()
    return g

def place_three_trash_at_top(grid):
    cols = list(range(GRID_W))
    random.shuffle(cols)
    for x in cols[:3]:
        grid[0][x] = make_tile("trash", None, None)

def trash_in_bottom_positions(grid):
    y = GRID_H - 1
    out = []
    for x in range(GRID_W):
        t = grid[y][x]
        if t is not None and tile_kind(t) == "trash":
            out.append((x, y))
    return out

def has_holes(grid):
    for y in range(GRID_H):
        for x in range(GRID_W):
            if grid[y][x] is None:
                return True
    return False

def special_expansion_cells_for_one_tile(grid, pos):
    x, y = pos
    t = grid[y][x]
    if t is None:
        return set()
    k = tile_kind(t)
    if k == "trash":
        return set()

    if k == "striped":
        out = set()
        mode = striped_mode(tile_extra(t))
        if mode == "row":
            for xx in range(GRID_W):
                if grid[y][xx] is not None and tile_kind(grid[y][xx]) != "trash":
                    out.add((xx, y))
        else:
            for yy in range(GRID_H):
                if grid[yy][x] is not None and tile_kind(grid[yy][x]) != "trash":
                    out.add((x, yy))
        return out

    if k == "bomb":
        out = set()
        for yy in range(y - 1, y + 2):
            for xx in range(x - 1, x + 2):
                if in_bounds(xx, yy):
                    if grid[yy][xx] is not None and tile_kind(grid[yy][xx]) != "trash":
                        out.add((xx, yy))
        return out

    return {pos}

def compute_clear_set_with_specials_chain(grid, initial_cells):
    to_clear = set()
    q = deque()

    for pos in initial_cells:
        x, y = pos
        t = grid[y][x]
        if t is None or tile_kind(t) == "trash":
            continue
        to_clear.add(pos)
        q.append(pos)

    while q:
        x, y = q.popleft()
        t = grid[y][x]
        if t is None or tile_kind(t) == "trash":
            continue
        k = tile_kind(t)
        if k in ("striped", "bomb"):
            extra = special_expansion_cells_for_one_tile(grid, (x, y))
            for p in extra:
                px, py = p
                tt = grid[py][px]
                if tt is None or tile_kind(tt) == "trash":
                    continue
                if p not in to_clear:
                    to_clear.add(p)
                    q.append(p)
    return to_clear

def clear_cells(grid, cells):
    for (x, y) in cells:
        t = grid[y][x]
        if t is None:
            continue
        if tile_kind(t) == "trash":
            continue
        grid[y][x] = None

def choose_specials_from_matches_for_cascade(grid, horiz_runs, vert_runs):
    special_map = {}
    protected = set()

    horiz_set, vert_set = set(), set()
    for run in horiz_runs:
        horiz_set.update(run)
    for run in vert_runs:
        vert_set.update(run)

    intersections = list(horiz_set & vert_set)
    random.shuffle(intersections)
    for (x, y) in intersections:
        t = grid[y][x]
        if t is None or tile_kind(t) == "trash":
            continue
        c = base_match_color(t) or rand_color()
        special_map[(x, y)] = make_tile("bomb", c, None)
        protected.add((x, y))
        break

    runs = [("h", r) for r in horiz_runs] + [("v", r) for r in vert_runs]
    runs.sort(key=lambda it: len(it[1]), reverse=True)

    placed_rainbow = False
    for orient, run in runs:
        cand = [p for p in run if p not in protected]
        if not cand:
            continue
        cx, cy = cand[len(cand) // 2]
        t = grid[cy][cx]
        if t is None or tile_kind(t) == "trash":
            continue

        if len(run) >= 5 and not placed_rainbow:
            # Five-in-a-row generates a rainbow ball
            special_map[(cx, cy)] = make_tile("rainbow", None, None)
            protected.add((cx, cy))
            placed_rainbow = True

        elif len(run) == 4:
            c = base_match_color(t) or rand_color()
            if orient == "h":
                special_map[(cx, cy)] = make_tile("striped", c, (1, 0))
            else:
                special_map[(cx, cy)] = make_tile("striped", c, (0, 1))
            protected.add((cx, cy))

    return special_map, protected


# -----------------------------
# Gravity: clear first, then drop one-by-one
# -----------------------------
def build_drop_plan(grid):
    moves = []
    new_grid = [[None for _ in range(GRID_W)] for _ in range(GRID_H)]

    for x in range(GRID_W):
        existing = []
        for y in range(GRID_H - 1, -1, -1):
            if grid[y][x] is not None:
                existing.append((grid[y][x], y))

        write_y = GRID_H - 1
        started = 0

        for t, old_y in existing:
            new_grid[write_y][x] = t
            if old_y != write_y:
                sx, sy = cell_to_px(x, old_y)
                ex, ey = cell_to_px(x, write_y)
                delay = started * DROP_STEP_DELAY
                moves.append((t, (sx, sy), (ex, ey), delay, (x, write_y)))
                started += 1
            write_y -= 1

        spawn_count = write_y + 1
        for i in range(spawn_count):
            target_y = write_y - i
            t = rand_normal()
            new_grid[target_y][x] = t

            ex, ey = cell_to_px(x, target_y)
            start_y = TOP_BAR - (spawn_count - i) * TILE
            sx = x * TILE
            delay = started * DROP_STEP_DELAY
            moves.append((t, (sx, start_y), (ex, ey), delay, (x, target_y)))
            started += 1

    return new_grid, moves

def drop_with_animation(grid, animator):
    new_grid, moves = build_drop_plan(grid)
    for y in range(GRID_H):
        for x in range(GRID_W):
            grid[y][x] = new_grid[y][x]
    for t, start_xy, end_xy, delay, dest_cell in moves:
        animator.add_drop(t, start_xy, end_xy, DROP_SPEED_PX, delay=delay, dest_cell=dest_cell, easing=DROP_EASING)


# -----------------------------
# Trash disposal when reaching bottom
# -----------------------------
def dispose_bottom_trash(grid, animator):
    disposed = 0
    bottoms = trash_in_bottom_positions(grid)
    if not bottoms:
        return 0
    bottoms.sort(key=lambda p: p[0])

    for (x, y) in bottoms:
        t = grid[y][x]
        if t is None or tile_kind(t) != "trash":
            continue
        start_px = cell_to_px(x, y)
        end_px = (start_px[0], TOP_BAR + GRID_H * TILE + TILE)
        animator.add_drop(t, start_px, end_px, speed_px=1600.0, delay=0.0, dest_cell=None, easing="smooth")
        grid[y][x] = None
        disposed += 1
    return disposed


# -----------------------------
# Move availability + shuffle (keeps trash fixed)
# -----------------------------
def is_match_after_swap(grid, a, b):
    swap_in_grid(grid, a, b)
    matched, _, _ = find_runs(grid)
    swap_in_grid(grid, a, b)
    return bool(matched)

def find_any_valid_move(grid):
    for y in range(GRID_H):
        for x in range(GRID_W):
            a = (x, y)
            t = grid[y][x]
            if t is None:
                continue
            if tile_kind(t) in ("trash", "rainbow"):
                continue

            if x + 1 < GRID_W:
                b = (x + 1, y)
                tb = grid[y][x + 1]
                if tb is not None and tile_kind(tb) not in ("trash", "rainbow"):
                    if is_match_after_swap(grid, a, b):
                        return (a, b)

            if y + 1 < GRID_H:
                b = (x, y + 1)
                tb = grid[y + 1][x]
                if tb is not None and tile_kind(tb) not in ("trash", "rainbow"):
                    if is_match_after_swap(grid, a, b):
                        return (a, b)
    return None

def has_any_valid_move(grid):
    return find_any_valid_move(grid) is not None

def shuffle_board_keep_trash(grid):
    trash_positions = {}
    pool = []

    for y in range(GRID_H):
        for x in range(GRID_W):
            t = grid[y][x]
            if t is None:
                continue
            if tile_kind(t) == "trash":
                trash_positions[(x, y)] = t
            else:
                pool.append(t)

    for _ in range(120):
        random.shuffle(pool)
        idx = 0
        for y in range(GRID_H):
            for x in range(GRID_W):
                if (x, y) in trash_positions:
                    grid[y][x] = trash_positions[(x, y)]
                else:
                    grid[y][x] = pool[idx]
                    idx += 1

        matched, _, _ = find_runs(grid)
        if matched:
            continue
        if has_any_valid_move(grid):
            return True
    return False


# -----------------------------
# Idle-help hint animation
# -----------------------------
def play_hint_swap_animation(grid, animator, move):
    """Visual hint only. Does not change grid."""
    if move is None:
        return
    a, b = move
    ax, ay = a
    bx, by = b
    ta = grid[ay][ax]
    tb = grid[by][bx]
    if ta is None or tb is None:
        return
    a_px = cell_to_px(ax, ay)
    b_px = cell_to_px(bx, by)
    animator.add_swap(ta, a_px, b_px, HINT_SWAP_DURATION)
    animator.add_swap(tb, b_px, a_px, HINT_SWAP_DURATION)
    animator.add_swap(ta, b_px, a_px, HINT_SWAP_DURATION)
    animator.add_swap(tb, a_px, b_px, HINT_SWAP_DURATION)


# -----------------------------
# Rainbow ball (five-in-a-row) staged effect
# -----------------------------
def clone_tile_as_template(template_tile):
    k = tile_kind(template_tile)
    if k == "normal":
        return make_tile("normal", tile_color(template_tile), None)
    if k == "striped":
        return make_tile("striped", tile_color(template_tile), tile_extra(template_tile))
    if k == "bomb":
        return make_tile("bomb", tile_color(template_tile), None)
    return None

def build_rainbow_plan(grid, rainbow_pos, other_pos):
    """
    Returns a dict describing a staged plan:
      - template tile (from other_pos)
      - chosen positions (30% of board, excluding trash/rainbow)
      - mode: 'normal' or 'special'
    Does not mutate the grid.
    """
    ox, oy = other_pos
    template = grid[oy][ox]
    if template is None or tile_kind(template) in ("trash", "rainbow"):
        return None

    candidates = []
    for y in range(GRID_H):
        for x in range(GRID_W):
            t = grid[y][x]
            if t is None:
                continue
            k = tile_kind(t)
            if k in ("trash", "rainbow"):
                continue
            candidates.append((x, y))

    if not candidates:
        return None

    n = int(len(candidates) * RAINBOW_CONVERT_RATIO)
    if n < 1:
        n = 1
    n = min(n, len(candidates))
    chosen = random.sample(candidates, n)

    templ_k = tile_kind(template)
    mode = "normal" if templ_k == "normal" else ("special" if templ_k in ("striped", "bomb") else "unsupported")
    if mode == "unsupported":
        return None

    # We also want to clear the rainbow and the swapped-with tile at the end
    return {
        "rainbow_pos": rainbow_pos,
        "other_pos": other_pos,
        "template": template,
        "chosen": chosen,
        "mode": mode,
    }


# -----------------------------
# UI helpers
# -----------------------------
def wrap_text(text, max_width, fnt):
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if fnt.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def task_color(done):
    return DONE_GREEN if done else SUBTEXT

def draw_special_overlay(surf, tile, rect):
    k = tile_kind(tile)
    if k == "striped":
        dx, dy = tile_extra(tile) if tile_extra(tile) else (1, 0)
        cx, cy = rect.center
        pygame.draw.line(surf, ARROW_COLOR, (cx - dx * 14, cy - dy * 14), (cx + dx * 14, cy + dy * 14), 6)
        hx, hy = (cx + dx * 18, cy + dy * 18)
        left = (hx - dy * 9 - dx * 7, hy + dx * 9 - dy * 7)
        right = (hx + dy * 9 - dx * 7, hy - dx * 9 - dy * 7)
        pygame.draw.polygon(surf, ARROW_COLOR, [(hx, hy), left, right])
        pygame.draw.line(surf, (0, 0, 0), (cx - dx * 14, cy - dy * 14), (cx + dx * 14, cy + dy * 14), 2)

    elif k == "bomb":
        cx, cy = rect.center
        pygame.draw.circle(surf, (20, 20, 20), (cx, cy), rect.w // 6)
        pygame.draw.circle(surf, (255, 170, 0), (cx + 10, cy - 10), 5)

def draw_rainbow_ball(surf, rect):
    """
    Draw a rainbow ball inside rect.
    Uses 6 colored arcs to look like a rainbow sphere.
    """
    cx, cy = rect.center
    r = min(rect.w, rect.h) // 2 - 2

    # base shadow
    pygame.draw.circle(surf, (18, 20, 26), (cx, cy), r + 2)

    colors = [
        (255, 80, 80),    # red
        (255, 170, 60),   # orange
        (255, 240, 90),   # yellow
        (80, 220, 120),   # green
        (90, 160, 255),   # blue
        (190, 120, 255),  # purple
    ]

    thickness = max(3, r // 3)
    arc_rect = pygame.Rect(cx - r, cy - r, 2 * r, 2 * r)

    # Draw arcs in different angle ranges
    step = (2 * math.pi) / len(colors)
    for i, col in enumerate(colors):
        start = i * step
        end = (i + 1) * step
        pygame.draw.arc(surf, col, arc_rect, start, end, thickness)

    # inner highlight
    pygame.draw.circle(surf, (255, 255, 255), (cx - r // 3, cy - r // 3), max(2, r // 6))
    # outline
    pygame.draw.circle(surf, (0, 0, 0), (cx, cy), r, 2)

def draw_tile(surf, fish_sprites, trash_sprite, tile, px, py):
    rect = pygame.Rect(px + 8, py + 8, TILE - 16, TILE - 16)
    k = tile_kind(tile)

    if k == "trash":
        surf.blit(trash_sprite, rect.topleft)
        pygame.draw.rect(surf, (0, 0, 0), rect, 2, border_radius=10)
        return

    if k == "rainbow":
        draw_rainbow_ball(surf, rect)
        return

    surf.blit(fish_sprites[tile_color(tile)], rect.topleft)
    if k in ("striped", "bomb"):
        draw_special_overlay(surf, tile, rect)
    pygame.draw.rect(surf, (0, 0, 0), rect, 2, border_radius=10)

def draw_tasks_panel(surface, font, score, score_goal, cleared_color_count, color_goal, color_name, trash_disposed, trash_total=3):
    panel_x = BOARD_W + 14
    panel_y = 14
    panel_w = SIDE_PANEL_W - 28
    panel_h = HEIGHT - 28
    rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    pygame.draw.rect(surface, (18, 20, 28), rect, border_radius=14)
    pygame.draw.rect(surface, (0, 0, 0), rect, 2, border_radius=14)

    surface.blit(font.render("Tasks", True, TEXT), (rect.x + 12, rect.y + 10))

    t1 = score >= score_goal
    t2 = cleared_color_count >= color_goal
    t3 = trash_disposed >= trash_total

    lines = [
        (f"Task 1: Reach {score_goal} score", f"({min(score, score_goal)}/{score_goal})", t1),
        (f"Task 2: Clear {color_goal} {color_name}", f"({min(cleared_color_count, color_goal)}/{color_goal})", t2),
        ("Task 3: Move trash bags to bottom", f"({min(trash_disposed, trash_total)}/{trash_total})", t3),
    ]

    y = rect.y + 42
    for left, right, done in lines:
        col = DONE_GREEN if done else SUBTEXT
        surface.blit(font.render(left, True, col), (rect.x + 12, y))
        surface.blit(font.render(right, True, col), (rect.right - 12 - font.size(right)[0], y))
        y += 26

    y += 10
    tip = "No moves => shuffle. Press ESC to exit."
    surface.blit(font.render(tip, True, SUBTEXT), (rect.x + 12, y))

def draw_all(screen, fish_sprites, trash_sprite, font, big, grid, selected, score, message,
             animator, cleared_set, score_goal, cleared_color_count, color_goal, color_name,
             trash_disposed):
    screen.fill(BG)

    pygame.draw.rect(screen, PANEL, (0, 0, BOARD_W, TOP_BAR))
    screen.blit(big.render(f"Score: {score}", True, TEXT), (16, 16))

    msg_area_w = BOARD_W - 32
    lines = wrap_text(message, msg_area_w, font)
    y = 62
    for ln in lines[:2]:
        screen.blit(font.render(ln, True, SUBTEXT), (16, y))
        y += 24

    pygame.draw.rect(screen, (10, 12, 16), SIDE_RECT)
    draw_tasks_panel(screen, font, score, score_goal, cleared_color_count, color_goal, color_name, trash_disposed, trash_total=3)

    prev_clip = screen.get_clip()
    screen.set_clip(BOARD_RECT)
    pygame.draw.rect(screen, GRID_BG, BOARD_RECT)

    hidden = animator.dest_cells_in_flight()

    for yy in range(GRID_H):
        for xx in range(GRID_W):
            px, py = cell_to_px(xx, yy)
            pygame.draw.rect(screen, GRID_LINE, (px, py, TILE, TILE), 1)

            if (xx, yy) in cleared_set:
                continue
            if (xx, yy) in hidden:
                continue

            t = grid[yy][xx]
            if t is None:
                continue
            draw_tile(screen, fish_sprites, trash_sprite, t, px, py)

    for t, ax, ay in animator.draw_overrides():
        draw_tile(screen, fish_sprites, trash_sprite, t, ax, ay)

    if selected:
        sx, sy = selected
        px, py = cell_to_px(sx, sy)
        pygame.draw.rect(screen, (255, 255, 255), (px + 3, py + 3, TILE - 6, TILE - 6), 3, border_radius=10)

    screen.set_clip(prev_clip)
    pygame.display.flip()


# -----------------------------
# Public entry point
# -----------------------------
def run_match3_minigame(level=1):
    score_goal = 500 + (max(0, level - 1) * 200)
    color_goal = 20

    if level <= 1:
        target_color = 5  # Yellow
    else:
        choices = [0, 1, 2, 3, 4, 5]
        if 5 in choices:
            choices.remove(5)
        target_color = random.choice(choices)

    color_names = ["Blue", "Green", "Pink", "Purple", "White", "Yellow"]
    color_name = color_names[target_color]

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Match-Three (Level {level})")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    big = pygame.font.SysFont(None, 38)

    fish_sprites, trash_sprite = load_assets()

    grid = make_grid_no_initial_matches()
    place_three_trash_at_top(grid)

    animator = Animator()

    selected = None
    score = 0
    cleared_target_color = 0
    trash_disposed = 0

    message = f"Level {level}: Clear {color_goal} {color_name}, reach {score_goal}, dispose 3 trash."
    cleared_set = set()

    state = "idle"
    swap_a = None
    swap_b = None

    pause_timer = 0.0

    # idle help timers
    idle_seconds = 0.0
    hint_cooldown = 0.0

    # rainbow staged plan state
    rainbow_plan = None
    rainbow_queue = []
    rainbow_step_timer = 0.0
    rainbow_converted = []  # positions converted (for final clear)
    rainbow_message_prefix = ""

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        animator.update(dt)

        # Win condition
        if score >= score_goal and cleared_target_color >= color_goal and trash_disposed >= 3:
            return "win"

        # Idle tracking (no input, no animations, and we are idle)
        if state == "idle" and (not animator.is_busy()):
            idle_seconds += dt
        else:
            idle_seconds = 0.0

        if hint_cooldown > 0.0:
            hint_cooldown -= dt

        # Auto hint after 5 seconds of no input
        if state == "idle" and (not animator.is_busy()) and hint_cooldown <= 0.0:
            if idle_seconds >= IDLE_HELP_SECONDS:
                mv = find_any_valid_move(grid)
                if mv is not None:
                    play_hint_swap_animation(grid, animator, mv)
                    message = "Hint: try swapping the highlighted pair."
                    idle_seconds = 0.0
                    hint_cooldown = HINT_COOLDOWN_SECONDS

        # Input
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "lose"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "lose"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Any click resets idle timers
                idle_seconds = 0.0
                hint_cooldown = 0.0

                if state != "idle" or animator.is_busy():
                    continue
                cell = screen_to_cell(*event.pos)
                if cell is None:
                    continue

                if selected is None:
                    selected = cell
                else:
                    if cell == selected:
                        selected = None
                    elif are_adjacent(selected, cell):
                        swap_a, swap_b = selected, cell
                        ax, ay = swap_a
                        bx, by = swap_b

                        ta = grid[ay][ax]
                        tb = grid[by][bx]

                        # Disallow swapping trash
                        if ta is None or tb is None or tile_kind(ta) == "trash" or tile_kind(tb) == "trash":
                            selected = None
                            message = "Cannot swap trash."
                            continue

                        a_px = cell_to_px(ax, ay)
                        b_px = cell_to_px(bx, by)

                        animator.add_swap(ta, a_px, b_px, SWAP_DURATION)
                        animator.add_swap(tb, b_px, a_px, SWAP_DURATION)
                        swap_in_grid(grid, swap_a, swap_b)

                        state = "swapping"
                        selected = None
                    else:
                        selected = cell

        # Swap finished
        if state == "swapping" and not animator.is_busy():
            ax, ay = swap_a
            bx, by = swap_b
            ta = grid[ay][ax]
            tb = grid[by][bx]

            # 1) rainbow ball swap effect has highest priority
            if (ta is not None and tile_kind(ta) == "rainbow") or (tb is not None and tile_kind(tb) == "rainbow"):
                if ta is not None and tile_kind(ta) == "rainbow":
                    rainbow_pos = (ax, ay)
                    other_pos = (bx, by)
                else:
                    rainbow_pos = (bx, by)
                    other_pos = (ax, ay)

                plan = build_rainbow_plan(grid, rainbow_pos, other_pos)
                if plan is None:
                    # fallback: treat as normal swap resolution
                    matched, _, _ = find_runs(grid)
                    if matched:
                        state = "resolving"
                        pause_timer = 0.0
                        message = "Good move."
                    else:
                        # revert swap
                        a_px = cell_to_px(ax, ay)
                        b_px = cell_to_px(bx, by)
                        animator.add_swap(grid[ay][ax], a_px, b_px, SWAP_DURATION)
                        animator.add_swap(grid[by][bx], b_px, a_px, SWAP_DURATION)
                        swap_in_grid(grid, swap_a, swap_b)
                        state = "idle"
                        message = "No match. Swap reverted."
                else:
                    # start staged conversion
                    rainbow_plan = plan
                    rainbow_queue = plan["chosen"][:]
                    random.shuffle(rainbow_queue)  # optional: random order
                    rainbow_step_timer = 0.0
                    rainbow_converted = []
                    templ = plan["template"]
                    k = tile_kind(templ)
                    if k == "normal":
                        rainbow_message_prefix = "Rainbow: converting tiles to a fish..."
                    else:
                        rainbow_message_prefix = "Rainbow: converting tiles to a skill..."
                    message = rainbow_message_prefix
                    state = "rainbow_converting"

            else:
                # 2) normal match flow
                matched, _, _ = find_runs(grid)
                if matched:
                    state = "resolving"
                    pause_timer = 0.0
                    message = "Good move."
                else:
                    # revert swap
                    a_px = cell_to_px(ax, ay)
                    b_px = cell_to_px(bx, by)
                    animator.add_swap(grid[ay][ax], a_px, b_px, SWAP_DURATION)
                    animator.add_swap(grid[by][bx], b_px, a_px, SWAP_DURATION)
                    swap_in_grid(grid, swap_a, swap_b)
                    state = "idle"
                    message = "No match. Swap reverted."

        # Staged rainbow conversion: convert one tile, then pause 1 second
        if state == "rainbow_converting":
            if animator.is_busy():
                pass
            else:
                rainbow_step_timer += dt
                if rainbow_step_timer >= RAINBOW_STEP_SECONDS:
                    rainbow_step_timer = 0.0

                    if rainbow_queue:
                        x, y = rainbow_queue.pop(0)
                        templ = rainbow_plan["template"]

                        # Convert this tile now
                        if tile_kind(templ) == "normal":
                            grid[y][x] = make_tile("normal", tile_color(templ), None)
                        else:
                            grid[y][x] = clone_tile_as_template(templ)

                        rainbow_converted.append((x, y))
                        message = f"{rainbow_message_prefix} ({len(rainbow_converted)}/{len(rainbow_plan['chosen'])})"
                    else:
                        # Conversion finished, now apply elimination/activation
                        templ = rainbow_plan["template"]
                        rainbow_pos = rainbow_plan["rainbow_pos"]
                        other_pos = rainbow_plan["other_pos"]

                        if tile_kind(templ) == "normal":
                            # Clear converted set plus rainbow and other
                            clear_set = set(rainbow_converted)
                            clear_set.add(rainbow_pos)
                            clear_set.add(other_pos)

                        else:
                            # For special tiles, activate via chain expansion starting from converted set
                            clear_set = compute_clear_set_with_specials_chain(grid, set(rainbow_converted))
                            clear_set.add(rainbow_pos)
                            clear_set.add(other_pos)

                        # Count target hits BEFORE clearing
                        target_hits = 0
                        for (cx, cy) in clear_set:
                            t = grid[cy][cx]
                            if t is None:
                                continue
                            if tile_kind(t) in ("trash", "rainbow"):
                                continue
                            if tile_color(t) == target_color:
                                target_hits += 1

                        clear_cells(grid, clear_set)

                        score_delta = len(clear_set) * 10
                        score += score_delta
                        cleared_target_color += target_hits

                        cleared_set = set(clear_set)
                        message = f"Rainbow activated: cleared {len(clear_set)} (+{score_delta})"
                        pause_timer = CLEAR_PAUSE

                        # reset rainbow state
                        rainbow_plan = None
                        rainbow_queue = []
                        rainbow_converted = []
                        rainbow_step_timer = 0.0

                        state = "resolving"

        # Resolving
        if state == "resolving":
            if pause_timer > 0.0:
                pause_timer -= dt
                if pause_timer <= 0:
                    cleared_set = set()
            elif animator.is_busy():
                pass
            else:
                # 1) dispose trash at bottom
                disposed_now = dispose_bottom_trash(grid, animator)
                if disposed_now > 0:
                    trash_disposed += disposed_now
                    message = f"Trash disposed: {trash_disposed}/3"
                else:
                    # 2) clear matches (count target BEFORE clearing)
                    matched, horiz_runs, vert_runs = find_runs(grid)
                    if matched:
                        special_map, protected = choose_specials_from_matches_for_cascade(grid, horiz_runs, vert_runs)
                        matched_to_clear = set(matched) - set(protected)
                        expanded = compute_clear_set_with_specials_chain(grid, matched_to_clear)

                        # Count target color before clearing
                        target_hits = 0
                        for (x, y) in expanded:
                            t = grid[y][x]
                            if t is None:
                                continue
                            if tile_kind(t) in ("trash", "rainbow"):
                                continue
                            if tile_color(t) == target_color:
                                target_hits += 1

                        # Place specials, then clear
                        for (x, y), new_tile in special_map.items():
                            if grid[y][x] is not None and tile_kind(grid[y][x]) == "trash":
                                continue
                            grid[y][x] = new_tile

                        clear_cells(grid, expanded)

                        score_delta = len(expanded) * 10
                        score += score_delta
                        cleared_target_color += target_hits

                        cleared_set = set(expanded)
                        message = f"Cleared {len(expanded)} (+{score_delta})"
                        pause_timer = CLEAR_PAUSE

                    else:
                        # 3) gravity if holes exist
                        if has_holes(grid):
                            drop_with_animation(grid, animator)
                        else:
                            # 4) no matches and no holes => check moves or shuffle
                            if not has_any_valid_move(grid):
                                message = "No moves available. Shuffling..."
                                ok = shuffle_board_keep_trash(grid)
                                if not ok:
                                    message = "Shuffled, but still no moves. Exiting."
                                    return "lose"
                            state = "idle"

        draw_all(
            screen=screen,
            fish_sprites=fish_sprites,
            trash_sprite=trash_sprite,
            font=font,
            big=big,
            grid=grid,
            selected=selected,
            score=score,
            message=message,
            animator=animator,
            cleared_set=cleared_set,
            score_goal=score_goal,
            cleared_color_count=cleared_target_color,
            color_goal=color_goal,
            color_name=color_name,
            trash_disposed=trash_disposed
        )

    return "lose"


# Optional quick test runner:
if __name__ == "__main__":
    pygame.init()
    try:
        result = run_match3_minigame(level=1)
        print("Result:", result)
    finally:
        pygame.quit()
