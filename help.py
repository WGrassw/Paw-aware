import pygame
import sys

# Initialize Pygame
pygame.init()

# Set up the display
WIDTH, HEIGHT = 600, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Clickable Buttons Example")

# Define colors
WHITE = (255, 255, 255)
BLUE = (0, 120, 255)
DARK_BLUE = (0, 90, 200)
BLACK = (0, 0, 0)

# Define font
font = pygame.font.SysFont(None, 40)

# Button class
class Button:
    def __init__(self, x, y, width, height, text, color, hover_color, action=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.action = action

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(surface, self.hover_color if is_hovered else self.color, self.rect)

        text_surface = font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def check_click(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos) and self.action:
                self.action()

# Example actions
def start_game():
    print("Game started!")

def quit_game():
    pygame.quit()
    sys.exit()

# Create buttons
start_button = Button(200, 120, 200, 60, "uwhihewhejfekfhefhdi", BLUE, DARK_BLUE, start_game)
quit_button = Button(200, 220, 200, 60, "Quit", BLUE, DARK_BLUE, quit_game)

# Game loop
while True:
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        start_button.check_click(event)
        quit_button.check_click(event)

    start_button.draw(screen)
    quit_button.draw(screen)

    pygame.display.flip()
