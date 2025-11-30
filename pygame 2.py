import pygame
import time
import random
from sys import exit

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((600,400))
pygame.display.set_caption('Runner')

Scenes=[pygame.image.load('background test.jpg').convert(), pygame.image.load('Scene1.jpg').convert()]
Bubble=pygame.image.load('Bubble.png').convert_alpha()
notice=pygame.image.load('notice.png').convert_alpha()
speech=pygame.image.load('speech.png').convert_alpha()

char_pos=[300,200]
char_pos1=0  # (left as-is)

# keep obstacle fully on-screen (25x25)
obstacle_rect = pygame.Rect(random.randint(0, 575), random.randint(0, 375), 25, 25)

# bubble rect tied to char_pos
bubble_rect = Bubble.get_rect(topleft=char_pos)

CurrentScene = Scenes[0]

# --- definitions ---
def noticesign(x,y):
    screen.blit(notice,(x,y))
    if (char_pos[0]-x)**2+(char_pos[1]-y)**2 <= 30000:
        return True

def speechbubble(message):
    screen.blit(speech,(250,50))
    font = pygame.font.Font('Grand9K Pixel.ttf', 20)
    # typewriter: reveal N chars based on time since scene_enter_time
    char_ms = 60  # ms per character
    if notice_triggered==False:
        elapsed = pygame.time.get_ticks() - scene_enter_time
    else:
        elapsed = pygame.time.get_ticks() - scene_enter_time
    visible = max(0, min(len(message), elapsed // char_ms))
    x = 290
    for ch in message[:visible]:
        if ch == ' ':
            x += 5
        else:
            glyph = font.render(ch, True, (0,0,0))
            screen.blit(glyph, (x, 305))
            x += 12

# timer for delayed messages
scene_enter_time = pygame.time.get_ticks()
notice_time = pygame.time.get_ticks()
notice_triggered=False

# --- main loop ---
while True:
    dt = clock.tick(60) / 1000.0  # seconds since last frame (smooth movement)

    # ----- EVENTS -----
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

        # click detection should use the positioned rect
        if event.type == pygame.MOUSEBUTTONDOWN:
            if bubble_rect.collidepoint(event.pos):
                print("Object clicked!")

    # ----- INPUT (per frame, not inside the event loop) -----
    key = pygame.key.get_pressed()
    base_speed = 220  # pixels/second (adjust for feel)
    speed = base_speed * (1.9 if key[pygame.K_LSHIFT] else 1.0)

    # build a normalized movement vector so diagonals aren't faster
    move_x = (1 if key[pygame.K_d] else 0) - (1 if key[pygame.K_a] else 0)
    move_y = (1 if key[pygame.K_s] else 0) - (1 if key[pygame.K_w] else 0)
    move_vec = pygame.math.Vector2(move_x, move_y)
    if move_vec.length_squared() > 0:
        move_vec = move_vec.normalize() * speed * dt
        char_pos[0] += move_vec.x
        char_pos[1] += move_vec.y

    # keep bubble_rect in sync with char_pos
    bubble_rect.topleft = (char_pos[0], char_pos[1])

    # ----- SIMPLE SOLID COLLISION RESOLUTION (axis-by-axis snap) -----
    # X axis
    if bubble_rect.colliderect(obstacle_rect):
        inter = bubble_rect.clip(obstacle_rect)
        if inter.width > 0 and inter.height > 0:
            # resolve along the smaller overlap axis for a quick, smooth feel
            if inter.width < inter.height:
                if bubble_rect.centerx < obstacle_rect.centerx:
                    bubble_rect.right = obstacle_rect.left
                else:
                    bubble_rect.left = obstacle_rect.right
                char_pos[0] = bubble_rect.x
            else:
                if bubble_rect.centery < obstacle_rect.centery:
                    bubble_rect.bottom = obstacle_rect.top
                else:
                    bubble_rect.top = obstacle_rect.bottom
                char_pos[1] = bubble_rect.y
            print('ahh', inter.center)

    # ----- SCENE SWITCHING -----
    if char_pos[0] > 500:
        Scene0 = CurrentScene
        idx = Scenes.index(CurrentScene)
        if idx < len(Scenes) - 1:
            CurrentScene = Scenes[idx + 1]
            char_pos = [-300, 150]
            scene_enter_time = pygame.time.get_ticks()
    elif char_pos[0] < -310:
        Scene0 = CurrentScene
        idx = Scenes.index(CurrentScene)
        if idx > 0:
            CurrentScene = Scenes[idx - 1]
            char_pos = [500, 150]
            scene_enter_time = pygame.time.get_ticks()

    # sync rect again if we teleported scenes
    bubble_rect.topleft = (char_pos[0], char_pos[1])

    # ----- DRAW -----
    screen.blit(CurrentScene, (0, 0))

    if CurrentScene == Scenes[0]:
        speechbubble('Choose your character.')

    if CurrentScene == Scenes[1]:
        returnnotice = noticesign(300, 0)
        if returnnotice==True:
            notice_triggered=True
            notice_time=pygame.time.get_ticks()
            speechbubble('Welcome to the cat world!')

    pygame.draw.rect(screen, (0, 0, 25), obstacle_rect)
    screen.blit(Bubble, bubble_rect)

    pygame.display.update()
