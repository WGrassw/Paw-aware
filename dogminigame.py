import pygame
import random
import math

# ----------------------------------
# CONSTANTS & SIZES
# ----------------------------------
FISH_SIZE = 32
CAT_SIZE = 90
DOG_SIZE = 300
THIEF_WIDTH = 80
THIEF_HEIGHT = 120

DOG_DANGER_RADIUS = 120         # Dog catches cat at this distance
CHASE_RADIUS = 260              # Dog starts chasing cat
CHASE_LOSE_RADIUS = 330         # Dog stops chasing when cat escapes

BASE_DOG_SPEED_BASE = 2.0
MAX_EXTRA_SPEED_BASE = 3.0
TIME_TO_MAX = 120000            # 2 minutes for dog to reach max speed

CHASE_MULTIPLIER = 1.6

FISH_STEAL_TIME_BASE = 8000
# FISH_ROT_TIME is no longer fixed; time limit now scales with level
FISH_ROT_TIME_BASE = 60000      # 60 seconds base (1 minute)
FISH_PICKUP_RADIUS_BASE = 50

# ----------------------------------
# HELPER FUNCTIONS
# ----------------------------------

def distance(a, b):
    ax, ay = a.center
    bx, by = b.center
    return math.hypot(ax - bx, ay - by)

def rps_result(player, cpu):
    if player == cpu:
        return "tie"
    win = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    return "win" if win[player] == cpu else "lose"


# ----------------------------------
# CLASSES
# ----------------------------------

class Cat:
    def __init__(self, x, y, speed):
        self.rect = pygame.Rect(x, y, CAT_SIZE, CAT_SIZE)
        self.speed = speed

    def update(self, keys, width, height):
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx -= self.speed
        if keys[pygame.K_RIGHT]:
            dx += self.speed
        if keys[pygame.K_UP]:
            dy -= self.speed
        if keys[pygame.K_DOWN]:
            dy += self.speed

        self.rect.x += dx
        self.rect.y += dy

        # Horizontal wrap-around
        if self.rect.right < 0:
            self.rect.left = width
        elif self.rect.left > width:
            self.rect.right = 0

        # Vertical clamp only
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > height:
            self.rect.bottom = height


class Dog:
    def __init__(self, x, y, base_speed, max_extra_speed):
        self.rect = pygame.Rect(x, y, DOG_SIZE, DOG_SIZE)
        self.mode = "wander"
        self.wander_dir = pygame.Vector2(1, 0)
        self.change_dir_timer = 0
        self.spawn_time = pygame.time.get_ticks()
        self.base_speed = base_speed
        self.max_extra_speed = max_extra_speed

    def current_base_speed(self):
        t = (pygame.time.get_ticks() - self.spawn_time) / TIME_TO_MAX
        t = max(0, min(1, t))
        return self.base_speed + t * self.max_extra_speed

    def update(self, cat_rect, width, height):
        dist = distance(self.rect, cat_rect)

        # Switch to chase mode when cat is close
        if dist < CHASE_RADIUS:
            self.mode = "chase"

        # Return to wander mode if cat escapes
        elif dist > CHASE_LOSE_RADIUS:
            self.mode = "wander"

        # Perform behavior
        if self.mode == "wander":
            self.wander(width, height)
        else:
            self.chase(cat_rect, width, height)

    def wander(self, width, height):
        speed = self.current_base_speed()
        now = pygame.time.get_ticks()

        if now > self.change_dir_timer:
            angle = random.uniform(0, math.pi * 2)
            self.wander_dir = pygame.Vector2(math.cos(angle), math.sin(angle))
            self.change_dir_timer = now + random.randint(1000, 2500)

        self.rect.x += int(self.wander_dir.x * speed)
        self.rect.y += int(self.wander_dir.y * speed)

        # Bounce from walls
        if self.rect.left < 0 or self.rect.right > width:
            self.wander_dir.x *= -1
        if self.rect.top < 0 or self.rect.bottom > height:
            self.wander_dir.y *= -1

        self.rect.clamp_ip(pygame.Rect(0, 0, width, height))

    def chase(self, cat_rect, width, height):
        speed = self.current_base_speed() * CHASE_MULTIPLIER
        dx = cat_rect.centerx - self.rect.centerx
        dy = cat_rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)

        if dist > 0:
            self.rect.x += int(speed * dx / dist)
            self.rect.y += int(speed * dy / dist)

        self.rect.clamp_ip(pygame.Rect(0, 0, width, height))


class ThiefCat:
    def __init__(self, width, height):
        x = random.randint(50, width - 50)
        y = random.randint(50, height - 50)
        self.rect = pygame.Rect(x, y, THIEF_WIDTH, THIEF_HEIGHT)
        self.active = True
        self.target_fish = None
        self.wander_dir = pygame.Vector2(1, 0)
        self.speed_wander = 1.5
        self.speed_chase = 2.5
        self.change_dir_timer = 0
        self.next_target_time = 0
        self.target_cooldown = 3000

    def set_target(self, fish):
        self.target_fish = fish
        fish.is_target = True

    def clear_target(self):
        if self.target_fish:
            self.target_fish.is_target = False
        self.target_fish = None
        self.next_target_time = pygame.time.get_ticks() + self.target_cooldown

    def defeat(self):
        self.active = False
        self.clear_target()
        self.rect.topleft = (-999, -999)

    def update(self, width, height):
        if not self.active:
            return

        if self.target_fish and self.target_fish.state != "fresh":
            self.clear_target()

        if self.target_fish:
            self.chase_target(width, height)
        else:
            self.wander(width, height)

    def wander(self, width, height):
        now = pygame.time.get_ticks()

        if now > self.change_dir_timer:
            angle = random.uniform(0, math.pi * 2)
            self.wander_dir = pygame.Vector2(math.cos(angle), math.sin(angle))
            self.change_dir_timer = now + random.randint(800, 2500)

        self.rect.x += int(self.wander_dir.x * self.speed_wander)
        self.rect.y += int(self.wander_dir.y * self.speed_wander)

        # Bounce
        if self.rect.left < 0 or self.rect.right > width:
            self.wander_dir.x *= -1
        if self.rect.top < 0 or self.rect.bottom > height:
            self.wander_dir.y *= -1

        self.rect.clamp_ip(pygame.Rect(0, 0, width, height))

    def chase_target(self, width, height):
        dx = self.target_fish.rect.centerx - self.rect.centerx
        dy = self.target_fish.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)

        if dist > 0:
            self.rect.x += int(self.speed_chase * dx / dist)
            self.rect.y += int(self.speed_chase * dy / dist)

        self.rect.clamp_ip(pygame.Rect(0, 0, width, height))


class Fish:
    def __init__(self, x, y, rot_time_ms):
        self.rect = pygame.Rect(x, y, FISH_SIZE, FISH_SIZE)
        self.state = "fresh"
        self.spawn_time = pygame.time.get_ticks()
        self.is_target = False
        self.rot_time = rot_time_ms  # per-level rot time

    def update(self):
        if (
            self.state == "fresh"
            and pygame.time.get_ticks() - self.spawn_time > self.rot_time
        ):
            self.state = "rotten"

# ----------------------------------
# MAIN FUNCTION
# ----------------------------------

def run_dog_minigame(level: int) -> str:
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((1200, 800))
    WIDTH, HEIGHT = screen.get_size()
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    # Track when the game starts (for the countdown)
    game_start_time = pygame.time.get_ticks()

    # Scaling
    cat_speed = 4 + (level - 1)
    base_dog_speed = BASE_DOG_SPEED_BASE + (level - 1) * 0.5
    max_extra_speed = MAX_EXTRA_SPEED_BASE + (level - 1) * 0.5
    fish_steal_time = max(2500, FISH_STEAL_TIME_BASE - (level - 1) * 1500)

    # 🔸 Number of fish: start at 5, then +3 per level
    num_fish = 5 + (level - 1) * 3

    pickup_radius = FISH_PICKUP_RADIUS_BASE

    # 🔸 Time limit per level:
    # Base 60 s, initial decrease from 60 → 30 s at level 1,
    # then +15 s each level:
    # L1 = 30s, L2 = 45s, L3 = 60s, L4 = 75s, ...
    time_limit_sec = 30 + (level - 1) * 15
    rot_time_ms = time_limit_sec * 1000

    # Images
    fish_img = pygame.transform.smoothscale(
        pygame.image.load("fish.png").convert_alpha(), (FISH_SIZE, FISH_SIZE)
    )
    fish_target_img = pygame.transform.smoothscale(
        pygame.image.load("targetted fish.png").convert_alpha(), (FISH_SIZE, FISH_SIZE)
    )
    cat_img = pygame.transform.smoothscale(
        pygame.image.load("cathead.png").convert_alpha(), (CAT_SIZE, CAT_SIZE)
    )
    dog_img = pygame.transform.smoothscale(
        pygame.image.load("threat minigame symbol.png").convert_alpha(), (DOG_SIZE, DOG_SIZE)
    )
    thief_img = pygame.transform.smoothscale(
        pygame.image.load("thief cat.png").convert_alpha(), (THIEF_WIDTH, THIEF_HEIGHT)
    )
    scratch_img = pygame.transform.smoothscale(
        pygame.image.load("scratch.png").convert_alpha(), (int(CAT_SIZE * 1.5), int(CAT_SIZE * 1.5))
    )
    dogminigamebackground = pygame.transform.smoothscale(
        pygame.image.load("dirtyfloor.png").convert(),
        (WIDTH, HEIGHT)
    )
    collect_sound = pygame.mixer.Sound("collect.wav")

    # Objects
    cat = Cat(100, 100, cat_speed)
    dog = Dog(WIDTH - 300, HEIGHT // 2, base_dog_speed, max_extra_speed)
    thief = ThiefCat(WIDTH, HEIGHT)

    # Safe fish spawn area
    margin_left, margin_top, margin_right, margin_bottom = 30, 30, 30, 70

    fishes = []
    for _ in range(num_fish):
        x = random.randint(margin_left, WIDTH - margin_right - FISH_SIZE)
        y = random.randint(margin_top, HEIGHT - margin_bottom - FISH_SIZE)
        fishes.append(Fish(x, y, rot_time_ms))

    # State
    state = "play"
    reason = ""
    rps_info = ""
    rps_msg = ""
    cat_damaged = False
    result = None
    waiting = False
    choices = {1: "rock", 2: "paper", 3: "scissors"}
    running = True
    while running:
        dt = clock.tick(60)

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if waiting and event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                running = False

            if state == "rps" and event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    num = 1 if event.key == pygame.K_1 else 2 if event.key == pygame.K_2 else 3
                    p = choices[num]
                    cpu = random.choice(list(choices.values()))
                    outcome = rps_result(p, cpu)

                    if outcome == "tie":
                        rps_msg = "Tie! Try again."
                    elif outcome == "win":
                        thief.defeat()
                        state = "play"
                    else:
                        reason = "You lost the fight!"
                        result = "lose"
                        state = "end"

        keys = pygame.key.get_pressed()

        # GAMEPLAY
        if state == "play":
            cat.update(keys, WIDTH, HEIGHT)
            dog.update(cat.rect, WIDTH, HEIGHT)
            thief.update(WIDTH, HEIGHT)

            now = pygame.time.get_ticks()

            # Update fish
            for f in fishes:
                f.update()

            # If any fish has rotted, end the game
            if any(f.state == "rotten" for f in fishes):
                reason = "The food has rotted!"
                result = "lose"
                state = "end"
            else:
                # Thief selects fish
                if thief.active and thief.target_fish is None and now >= thief.next_target_time:
                    candidates = [
                        f for f in fishes
                        if f.state == "fresh" and not f.is_target and now - f.spawn_time > fish_steal_time
                    ]
                    if candidates:
                        # Thief chooses *farthest* fish (easier for player)
                        target = max(candidates, key=lambda f: distance(thief.rect, f.rect))
                        thief.set_target(target)

                # Thief steals fish
                if thief.active and thief.target_fish and thief.target_fish.state == "fresh":
                    if distance(thief.rect, thief.target_fish.rect) < 12:
                        thief.target_fish.state = "stolen"
                        thief.clear_target()
                        reason = "The thief stole your fish!"
                        result = "lose_thief"
                        state = "end"

                # Cat collects fish
                for f in fishes:
                    if f.state == "fresh" and distance(cat.rect, f.rect) < pickup_radius:
                        f.state = "collected"
                        f.is_target = False
                        collect_sound.play()  
                        if f is thief.target_fish:
                            thief.clear_target()

                # Dog catches cat
                if distance(cat.rect, dog.rect) < DOG_DANGER_RADIUS:
                    cat_damaged = True
                    reason = "The dog has caught you"
                    result = "lose"
                    state = "end"

                # Cat touches thief → RPS fight
                if thief.active and cat.rect.colliderect(thief.rect):
                    state = "rps"
                    rps_info = "1=Rock 2=Paper 3=Scissors"
                    rps_msg = ""

                # Win condition
                if all(f.state == "collected" for f in fishes):
                    reason = "You collected all the food!"
                    result = "win"
                    state = "end"

        # ---------------------
        # DRAW
        # ---------------------
        screen.blit(dogminigamebackground, (0, 0))

        # Draw fish
        for f in fishes:
            if f.state == "fresh":
                if f.is_target:
                    screen.blit(fish_target_img, f.rect)
                else:
                    screen.blit(fish_img, f.rect)

        # Draw cat
        screen.blit(cat_img, cat.rect)
        if cat_damaged:
            screen.blit(scratch_img, scratch_img.get_rect(center=cat.rect.center))

        # Draw dog & thief
        screen.blit(dog_img, dog.rect)
        if thief.active:
            screen.blit(thief_img, thief.rect)

        # UI – level & food
        collected = sum(f.state == "collected" for f in fishes)
        ui = font.render(
            f"Dog Minigame | Level {level} | Food: {collected}/{len(fishes)}",
            True, (255, 255, 255)
        )
        screen.blit(ui, (10, 10))

        # Rot countdown display (per level time limit)
        elapsed_total = pygame.time.get_ticks() - game_start_time
        remaining_ms = max(0, rot_time_ms - elapsed_total)
        remaining_sec = remaining_ms // 1000
        mins = remaining_sec // 60
        secs = remaining_sec % 60
        timer_text = font.render(
            f"Time Before Fish Becomes Rotten: {mins:01d}:{secs:02d}",
            True, (255, 200, 200)
        )
        screen.blit(timer_text, (10, 30))

        if state == "rps":
            screen.blit(font.render(rps_info, True, (255, 255, 255)), (50, HEIGHT - 80))
            screen.blit(font.render(rps_msg, True, (255, 255, 0)), (50, HEIGHT - 50))

        if state == "end":
            if result == "win":
                col1, col2 = (120, 255, 120), (160, 255, 160)
            else:
                col1, col2 = (255, 80, 80), (255, 170, 170)

            if result == "win":
                screen.blit(
                    font.render("MINIGAME WON", True, col1),
                    font.render("MINIGAME WON", True, col1).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            else:
                screen.blit(
                    font.render("MINIGAME LOST", True, col1),
                    font.render("MINIGAME LOST", True, col1).get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))

            screen.blit(
                font.render(reason, True, col2),
                font.render(reason, True, col2).get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
            )

            prompt = font.render("Press ENTER to return to the lobby", True, (255, 255, 255))
            screen.blit(prompt, prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50)))
            waiting = True

        pygame.display.flip()

    return result if result else "lose"
