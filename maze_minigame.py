# maze_minigame.py
import random
import pygame
import math


def run_maze_minigame(window_size=(1200, 800), caption="Maze Minigame"):
    WINDOW_W, WINDOW_H = window_size
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption(caption)
    clock = pygame.time.Clock()

    # =========================
    # Config
    # =========================
    CELL_SIZE = 26
    FPS = 60

    def largest_odd_that_fits(pixels, cell):
        n = pixels // cell
        if n % 2 == 0:
            n -= 1
        return max(3, n)

    MAZE_W = largest_odd_that_fits(WINDOW_W, CELL_SIZE)
    MAZE_H = largest_odd_that_fits(WINDOW_H, CELL_SIZE)

    # Player light
    LIGHT_RADIUS_PX = 135
    LIGHT_SOFTNESS = 10

    DARKNESS_ALPHA = 245

    # Exit beacon
    EXIT_LIGHT_RADIUS_TILES = 2
    EXIT_LIGHT_RADIUS_PX = EXIT_LIGHT_RADIUS_TILES * CELL_SIZE
    EXIT_LIGHT_SOFTNESS = 6

    INSIDE_LIGHT_DARKNESS_ALPHA = 35

    FLOOR_BORDER = True
    FLOOR_BORDER_ALPHA = 80
    WALL_INNER_SHADE = True

    # Colors
    BG_COLOR = (12, 12, 14)

    FLOOR_COLOR = (20, 15, 15)
    FLOOR_BORDER_COLOR = (20, 15, 15)

    WALL_COLOR = (242, 235, 235)
    WALL_INNER_COLOR = (242, 235, 235)

    PLAYER_LIGHT_BLOOM_COLOR = (148, 148, 142)
    EXIT_LIGHT_BLOOM_COLOR = (119, 145, 121)

    EXIT_COLOR = (99, 97, 85)

    WALL = 1
    FLOOR = 0

    # =========================
    # Surveillance spotlight (lighthouse beam)
    # =========================
    SPOTLIGHT_RANGE_PX = 720
    SPOTLIGHT_HALF_ANGLE_DEG = 18
    SPOTLIGHT_SPEED_DEG_PER_SEC = 20
    SPOTLIGHT_COLOR = (230, 230, 200)
    SPOTLIGHT_MAX_ALPHA = 70
    SPOTLIGHT_SOFT_STEPS = 4

    # =========================
    # Helpers
    # =========================
    def in_bounds(x, y, w, h):
        return 0 <= x < w and 0 <= y < h

    def generate_maze(w, h, rng):
        grid = [[WALL for _ in range(w)] for _ in range(h)]
        sx, sy = 1, 1
        grid[sy][sx] = FLOOR

        stack = [(sx, sy)]
        dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]

        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in dirs:
                nx, ny = cx + dx, cy + dy
                if in_bounds(nx, ny, w, h) and grid[ny][nx] == WALL:
                    neighbors.append((nx, ny, dx, dy))

            if neighbors:
                nx, ny, dx, dy = rng.choice(neighbors)
                grid[cy + dy // 2][cx + dx // 2] = FLOOR
                grid[ny][nx] = FLOOR
                stack.append((nx, ny))
            else:
                stack.pop()

        return grid

    def find_farthest_floor(grid, start):
        from collections import deque
        h = len(grid)
        w = len(grid[0])
        sx, sy = start

        q = deque([(sx, sy)])
        dist = {(sx, sy): 0}
        far = (sx, sy)

        while q:
            x, y = q.popleft()
            if dist[(x, y)] > dist[far]:
                far = (x, y)
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if in_bounds(nx, ny, w, h) and grid[ny][nx] == FLOOR and (nx, ny) not in dist:
                    dist[(nx, ny)] = dist[(x, y)] + 1
                    q.append((nx, ny))
        return far

    def make_subtractive_light_mask(radius_px, softness_steps):
        size = radius_px * 2
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = radius_px, radius_px
        for i in range(softness_steps):
            t = i / max(1, softness_steps - 1)
            r = int(radius_px * (0.35 + 0.65 * t))
            alpha = int(255 * (1.0 - t))
            pygame.draw.circle(s, (0, 0, 0, alpha), (cx, cy), r)
        return s

    def make_additive_bloom_mask(radius_px, softness_steps, color, max_alpha):
        size = radius_px * 2
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = radius_px, radius_px
        for i in range(softness_steps):
            t = i / max(1, softness_steps - 1)
            r = int(radius_px * (0.30 + 0.70 * t))
            alpha = int(max_alpha * (1.0 - t))
            pygame.draw.circle(s, (*color, alpha), (cx, cy), r)
        return s

    def angle_wrap_pi(a):
        while a <= -math.pi:
            a += 2 * math.pi
        while a > math.pi:
            a -= 2 * math.pi
        return a

    def spotlight_hits_point(origin, angle_rad, half_angle_rad, max_range_px, px, py):
        dx = px - origin[0]
        dy = py - origin[1]
        dist2 = dx * dx + dy * dy
        if dist2 > max_range_px * max_range_px:
            return False

        point_ang = math.atan2(dy, dx)
        diff = angle_wrap_pi(point_ang - angle_rad)
        return abs(diff) <= half_angle_rad

    def draw_spotlight(surface, origin, angle_rad):
        cone_surf = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)

        half_angle_base = math.radians(SPOTLIGHT_HALF_ANGLE_DEG)
        layers = SPOTLIGHT_SOFT_STEPS

        for i in range(layers):
            t = i / max(1, layers - 1)
            half_angle = half_angle_base * (1.0 + 0.55 * t)
            alpha = int(SPOTLIGHT_MAX_ALPHA * (1.0 - 0.75 * t))

            points = [origin]
            steps = 22
            start_ang = angle_rad - half_angle
            end_ang = angle_rad + half_angle

            for s in range(steps + 1):
                u = s / steps
                a = start_ang + (end_ang - start_ang) * u
                x = origin[0] + math.cos(a) * SPOTLIGHT_RANGE_PX
                y = origin[1] + math.sin(a) * SPOTLIGHT_RANGE_PX
                points.append((x, y))

            pygame.draw.polygon(cone_surf, (*SPOTLIGHT_COLOR, alpha), points)

        surface.blit(cone_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    # =========================
    # Setup
    # =========================
    rng = random.Random()
    grid = generate_maze(MAZE_W, MAZE_H, rng)
    start = (1, 1)
    exit_pos = find_farthest_floor(grid, start)

    MAZE_PIXEL_W = MAZE_W * CELL_SIZE
    MAZE_PIXEL_H = MAZE_H * CELL_SIZE
    OFFSET_X = (WINDOW_W - MAZE_PIXEL_W) // 2
    OFFSET_Y = (WINDOW_H - MAZE_PIXEL_H) // 2

    def tile_rect(x, y):
        return pygame.Rect(
            x * CELL_SIZE + OFFSET_X,
            y * CELL_SIZE + OFFSET_Y,
            CELL_SIZE,
            CELL_SIZE
        )

    px, py = start
    move_cooldown = 0.0
    MOVE_DELAY = 0.09

    outside_darkness = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
    inside_darkness = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)

    player_light_mask = make_subtractive_light_mask(LIGHT_RADIUS_PX, LIGHT_SOFTNESS)
    exit_light_mask = make_subtractive_light_mask(EXIT_LIGHT_RADIUS_PX, EXIT_LIGHT_SOFTNESS)

    player_bloom_mask = make_additive_bloom_mask(
        LIGHT_RADIUS_PX, LIGHT_SOFTNESS, color=PLAYER_LIGHT_BLOOM_COLOR, max_alpha=95
    )
    exit_bloom_mask = make_additive_bloom_mask(
        EXIT_LIGHT_RADIUS_PX, EXIT_LIGHT_SOFTNESS, color=EXIT_LIGHT_BLOOM_COLOR, max_alpha=170
    )

    floor_border = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
    if FLOOR_BORDER:
        floor_border.fill((0, 0, 0, 0))
        pygame.draw.rect(
            floor_border,
            (*FLOOR_BORDER_COLOR, FLOOR_BORDER_ALPHA),
            pygame.Rect(0, 0, CELL_SIZE, CELL_SIZE),
            width=1
        )

    font = pygame.font.SysFont(None, 34)

    # Load + scale player sprite (cat head) to match old circle size
    cat_img_raw = pygame.image.load("cathead.png").convert_alpha()
    PLAYER_SPRITE_SIZE = int(CELL_SIZE * 1.2)  # roughly matches old circle diameter
    cat_img = pygame.transform.smoothscale(cat_img_raw, (PLAYER_SPRITE_SIZE, PLAYER_SPRITE_SIZE))

    def show_result_screen(lines, delay_ms=900):
        overlay = pygame.Surface((WINDOW_W, WINDOW_H))
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))

        y = 260
        for text in lines:
            surf = font.render(text, True, (245, 245, 245))
            rect = surf.get_rect(center=(WINDOW_W // 2, y))
            screen.blit(surf, rect)
            y += 48

        pygame.display.flip()
        pygame.time.delay(delay_ms)

    ex, ey = exit_pos
    exit_cx = int((ex + 0.5) * CELL_SIZE + OFFSET_X)
    exit_cy = int((ey + 0.5) * CELL_SIZE + OFFSET_Y)

    spotlight_origin = (exit_cx, exit_cy)
    spotlight_angle = rng.random() * math.tau
    spotlight_speed = math.radians(SPOTLIGHT_SPEED_DEG_PER_SEC)
    spotlight_half_angle = math.radians(SPOTLIGHT_HALF_ANGLE_DEG)

    # =========================
    # Loop
    # =========================
    while True:
        dt = clock.tick(FPS) / 1000.0
        move_cooldown = max(0.0, move_cooldown - dt)

        spotlight_angle = (spotlight_angle + spotlight_speed * dt) % (2 * math.pi)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "lose"

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            return "lose"

        moved_this_tick = False

        if move_cooldown <= 0.0:
            dx = dy = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            elif keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1

            if dx or dy:
                nx, ny = px + dx, py + dy
                if in_bounds(nx, ny, MAZE_W, MAZE_H) and grid[ny][nx] == FLOOR:
                    px, py = nx, ny
                    move_cooldown = MOVE_DELAY
                    moved_this_tick = True

        player_cx = int((px + 0.5) * CELL_SIZE + OFFSET_X)
        player_cy = int((py + 0.5) * CELL_SIZE + OFFSET_Y)

        # Caught check: moved while in spotlight
        if moved_this_tick:
            if spotlight_hits_point(
                origin=spotlight_origin,
                angle_rad=spotlight_angle,
                half_angle_rad=spotlight_half_angle,
                max_range_px=SPOTLIGHT_RANGE_PX,
                px=player_cx,
                py=player_cy,
            ):
                show_result_screen(
                    [
                        "CAUGHT BY SURVEILLANCE!",
                        "You moved while the spotlight was on you.",
                        "Returning to the lobby..."
                    ],
                    delay_ms=1100
                )
                return "lose_half"

        # Win condition
        if (px, py) == exit_pos:
            show_result_screen(
                [
                    "YOU WON!",
                    "You found the exit.",
                    "Returning to the lobby..."
                ],
                delay_ms=900
            )
            return "win"

        # Draw world
        screen.fill(BG_COLOR)
        for y in range(MAZE_H):
            for x in range(MAZE_W):
                r = tile_rect(x, y)
                if grid[y][x] == WALL:
                    pygame.draw.rect(screen, WALL_COLOR, r)
                    if WALL_INNER_SHADE:
                        pygame.draw.rect(screen, WALL_INNER_COLOR, r.inflate(-3, -3), border_radius=6)
                else:
                    pygame.draw.rect(screen, FLOOR_COLOR, r)
                    if FLOOR_BORDER:
                        screen.blit(floor_border, r.topleft)

        pygame.draw.rect(screen, EXIT_COLOR, tile_rect(ex, ey).inflate(-10, -10), border_radius=7)

        # Draw player as cat sprite (same size)
        cat_rect = cat_img.get_rect(center=(player_cx, player_cy))
        screen.blit(cat_img, cat_rect)

        # Lighting base
        outside_darkness.fill((0, 0, 0, DARKNESS_ALPHA))

        p_mask_x = player_cx - LIGHT_RADIUS_PX
        p_mask_y = player_cy - LIGHT_RADIUS_PX
        outside_darkness.blit(player_light_mask, (p_mask_x, p_mask_y), special_flags=pygame.BLEND_RGBA_SUB)

        e_mask_x = exit_cx - EXIT_LIGHT_RADIUS_PX
        e_mask_y = exit_cy - EXIT_LIGHT_RADIUS_PX
        outside_darkness.blit(exit_light_mask, (e_mask_x, e_mask_y), special_flags=pygame.BLEND_RGBA_SUB)

        screen.blit(outside_darkness, (0, 0))

        inside_darkness.fill((0, 0, 0, 0))
        pygame.draw.circle(
            inside_darkness, (0, 0, 0, INSIDE_LIGHT_DARKNESS_ALPHA),
            (player_cx, player_cy), LIGHT_RADIUS_PX
        )
        pygame.draw.circle(
            inside_darkness, (0, 0, 0, INSIDE_LIGHT_DARKNESS_ALPHA),
            (exit_cx, exit_cy), EXIT_LIGHT_RADIUS_PX
        )
        screen.blit(inside_darkness, (0, 0))

        # Spotlight beam
        draw_spotlight(screen, spotlight_origin, spotlight_angle)

        # Bloom dominance: exit overrides player in overlap
        screen.blit(player_bloom_mask, (p_mask_x, p_mask_y), special_flags=pygame.BLEND_RGBA_ADD)

        erase = pygame.Surface((EXIT_LIGHT_RADIUS_PX * 2, EXIT_LIGHT_RADIUS_PX * 2), pygame.SRCALPHA)
        erase.fill((0, 0, 0, 0))
        pygame.draw.circle(
            erase, (0, 0, 0, 255),
            (EXIT_LIGHT_RADIUS_PX, EXIT_LIGHT_RADIUS_PX), EXIT_LIGHT_RADIUS_PX
        )
        screen.blit(erase, (e_mask_x, e_mask_y), special_flags=pygame.BLEND_RGBA_SUB)

        screen.blit(exit_bloom_mask, (e_mask_x, e_mask_y), special_flags=pygame.BLEND_RGBA_ADD)

        # UI
        ui_font = pygame.font.SysFont(None, 28)
        msg = ui_font.render(
            "Get to the center of the beacon to exit. Avoid the surveillance beacon, stop moving when it hits you.",
            True, (235, 235, 235)
        )
        screen.blit(msg, (14, 14))

        pygame.display.flip()
