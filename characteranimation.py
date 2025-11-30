import pygame
import time
import random
pygame.init()
pygame.mixer.init() 
from sys import exit
footstep = pygame.mixer.Sound("catfootsteps.wav")
footstepfast = pygame.mixer.Sound("catfootsteps fast.wav")
walk_left_frames = [
    pygame.image.load("catwalkingright1.png"),
    pygame.image.load("catwalkingright2.png"),
    pygame.image.load("catwalkingright3.png"),
    pygame.image.load("catwalkingright4.png"),
    pygame.image.load("catwalkingright5.png"),
    pygame.image.load("catwalkingright6.png"),
    pygame.image.load("catwalkingright7.png"),
    pygame.image.load("catwalkingright8.png"),
    pygame.image.load("catwalkingright9.png"),
    pygame.image.load("catwalkingright10.png"),
    pygame.image.load("catwalkingright11.png"),
]
for k in range(len(walk_left_frames)):
    walk_left_frames[k].convert_alpha().set_alpha()

walk_right_frames = [
    
    pygame.image.load("catwalkingleft1.png"),
    pygame.image.load("catwalkingleft2.png"),
    pygame.image.load("catwalkingleft3.png"),
    pygame.image.load("catwalkingleft4.png"),
    pygame.image.load("catwalkingleft5.png"),
    pygame.image.load("catwalkingleft6.png"),
    pygame.image.load("catwalkingleft7.png"),
    pygame.image.load("catwalkingleft8.png"),
    pygame.image.load("catwalkingleft9.png"),
    pygame.image.load("catwalkingleft10.png"),
    pygame.image.load("catwalkingleft11.png"),
]

# Player variables (now module-level variables)
player_x = 100
player_y = 650
base_player_speed = 5
sprint_player_speed = 10 
frame_index = 0.0 
direction = 1 
moving = False
was_moving = False
was_sprinting = False 
base_animation_speed = 0.1 
sprint_animation_speed = 0.2 
base_FPS = 80 
sprint_FPS = 100
current_frame = None
current_player_speed = base_player_speed
current_animation_speed = base_animation_speed
current_FPS = base_FPS


def update_character_logic(keys):
    global player_x, frame_index, direction, moving, was_moving
    global current_player_speed, current_animation_speed, current_FPS, current_frame
    global was_sprinting

    # Input handling
    if keys[pygame.K_LEFT]:
        direction = -1
        moving = True
    elif keys[pygame.K_RIGHT]:
        direction = 1
        moving = True
    else:
        moving = False

    is_sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

    # Set speed and animation speed
    current_player_speed = sprint_player_speed if is_sprinting and moving else base_player_speed
    current_animation_speed = sprint_animation_speed if is_sprinting and moving else base_animation_speed
    current_FPS = sprint_FPS if is_sprinting and moving else base_FPS

    # Update position and animation
    if moving:
        player_x += current_player_speed * direction
        frame_index = (frame_index + current_animation_speed) % len(walk_right_frames)

    # Set current animation frame
    if direction == 1:
        current_frame = walk_right_frames[int(frame_index)]
    elif direction == -1:
        current_frame = walk_left_frames[int(frame_index)]

    # Handle sound playback
    if moving and not was_moving:
        # Started walking
        if is_sprinting:
            footstepfast.play(-1)
        else:
            footstep.play(-1)
    elif not moving and was_moving:
        # Stopped walking
        footstep.stop()
        footstepfast.stop()
    elif moving and was_moving and is_sprinting != was_sprinting:
        # Sprinting state changed mid-movement
        footstep.stop()
        footstepfast.stop()
        if is_sprinting:
            footstepfast.play(-1)
        else:
            footstep.play(-1)

    # Update previous states
    was_moving = moving
    was_sprinting = is_sprinting
    
def draw_character(screen):
    """
    Draws the character to the provided screen surface.
    Needs to be called every frame from the main game loop.
    """
    # Use the global variables set by update_character_logic
    if current_frame:
        screen.blit(current_frame, (player_x, player_y))

            
