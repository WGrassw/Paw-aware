import pygame
import time
import random
from sys import exit

pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((600,400))
pygame.display.set_caption('Runner')


# --------------- UI Helpers ---------------

def _vgradient(surface, top_color, bottom_color):
    """Vertical gradient fill."""
    w, h = surface.get_size()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (w, y))

class Button:
    def __init__(self, rect, text, font, base=(30,30,30), hover=(60,60,60), disabled=(130,130,130)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.base, self.hover, self.disabled = base, hover, disabled
        self.enabled = True

    def draw(self, surf, mouse):
        color = self.base
        if not self.enabled:
            color = self.disabled
        elif self.rect.collidepoint(mouse):
            color = self.hover
        pygame.draw.rect(surf, color, self.rect, border_radius=12)
        pygame.draw.rect(surf, (240,240,240), self.rect, 2, border_radius=12)
        label = self.font.render(self.text, True, (250,250,250))
        surf.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

class InputBox:
    def __init__(self, rect, font, placeholder="Enter name..."):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.text = ""
        self.active = False
        self.placeholder = placeholder

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if self.active and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                if len(self.text) < 16 and event.unicode.isprintable():
                    self.text += event.unicode

    def value(self):
        return self.text.strip()

    def draw(self, surf):
        bg = (255,255,255) if self.active else (245,245,245)
        pygame.draw.rect(surf, bg, self.rect, border_radius=10)
        pygame.draw.rect(surf, (50,50,50), self.rect, 2, border_radius=10)
        show = self.text if self.text else self.placeholder
        col = (20,20,20) if self.text else (120,120,120)
        label = self.font.render(show, True, col)
        surf.blit(label, (self.rect.x + 12, self.rect.y + (self.rect.h - label.get_height())//2))

def _draw_card(surf, rect, title, advantage, weakness, icon_color, selected, fonts):
    """Pretty choice card."""
    r = pygame.Rect(rect)
    # card base
    card_bg = (255,255,255)
    shadow = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0,0,0,80), shadow.get_rect(), border_radius=18)
    surf.blit(shadow, (r.x+4, r.y+6))
    pygame.draw.rect(surf, card_bg, r, border_radius=18)
    pygame.draw.rect(surf, (30,30,30), r, 2, border_radius=18)

    # header bar
    header = pygame.Rect(r.x, r.y, r.w, 54)
    pygame.draw.rect(surf, (24, 33, 68), header, border_radius=18)
    title_label = fonts['title'].render(title, True, (240,240,255))
    surf.blit(title_label, (header.x + 16, header.y + 14))

    # icon
    icon_rect = pygame.Rect(r.x + 20, r.y + 72, 64, 64)
    pygame.draw.circle(surf, icon_color, icon_rect.center, 32)
    pygame.draw.circle(surf, (255,255,255), icon_rect.center, 32, 3)

    # text blocks
    adv_label = fonts['label'].render("Advantage", True, (34,139,34))
    wk_label  = fonts['label'].render("Weakness", True, (178,34,34))
    surf.blit(adv_label, (icon_rect.right + 14, icon_rect.y))
    adv_txt = fonts['body'].render(advantage, True, (20,20,20))
    surf.blit(adv_txt, (icon_rect.right + 14, icon_rect.y + 26))

    surf.blit(wk_label, (icon_rect.right + 14, icon_rect.y + 64))
    wk_txt = fonts['body'].render(weakness, True, (20,20,20))
    surf.blit(wk_txt, (icon_rect.right + 14, icon_rect.y + 90))

    # selected ring
    if selected:
        glow = pygame.Surface((r.w+14, r.h+14), pygame.SRCALPHA)
        pygame.draw.rect(glow, (56,130,255,60), glow.get_rect(), border_radius=22)
        surf.blit(glow, (r.x-7, r.y-7))
        pygame.draw.rect(surf, (56,130,255), r, 4, border_radius=18)

def start_screen(screen, *, use_font_path=None):
    """
    Returns a dict with chosen name/kit/stats.
    Call this BEFORE your main game loop:
        config = start_screen(screen)
    """
    clock = pygame.time.Clock()
    W, H = screen.get_size()
    # fonts
    try:
        title_font = pygame.font.Font(use_font_path or None, 36)
        body_font  = pygame.font.Font(use_font_path or None, 22)
        small_font = pygame.font.Font(use_font_path or None, 18)
    except:
        title_font = pygame.font.SysFont(None, 36)
        body_font  = pygame.font.SysFont(None, 22)
        small_font = pygame.font.SysFont(None, 18)

    fonts = {'title': title_font, 'body': body_font, 'label': small_font}

    # UI layout
    name_box = InputBox((W//2 - 180, 90, 360, 46), body_font, "Enter your cat's name...")
    card_w, card_h = 460, 180
    gap = 24
    left_card  = pygame.Rect(W//2 - card_w - gap//2, 170, card_w, card_h)
    right_card = pygame.Rect(W//2 + gap//2,          170, card_w, card_h)

    start_btn = Button((W//2 - 110, H - 100, 220, 56), "Start Adventure", body_font)

    selection = None  # "sprinter" or "sharpshooter"
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        mouse = pygame.mouse.get_pos()
        # BG
        _vgradient(screen, (235,241,255), (205,218,255))
        title = title_font.render("Choose Your Cat", True, (25,25,35))
        screen.blit(title, title.get_rect(center=(W//2, 46)))

        subtitle = small_font.render("Each cat has a unique advantage and a trade-off.", True, (60,60,70))
        screen.blit(subtitle, subtitle.get_rect(center=(W//2, 70)))

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit
            name_box.handle(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if left_card.collidepoint(event.pos):
                    selection = "sprinter"
                elif right_card.collidepoint(event.pos):
                    selection = "sharpshooter"

            if start_btn.clicked(event):
                if name_box.value() and selection:
                    # assemble config
                    if selection == "sprinter":
                        stats = {
                            "sprint_multiplier": 1.8,  # hold SHIFT
                            "max_stamina": 100,
                            "stamina_recovery": 22,     # per second
                            "accuracy_bonus": 0.0,
                            "food_spawn_multiplier": 1.0
                        }
                    else:  # sharpshooter
                        stats = {
                            "sprint_multiplier": 1.0,
                            "max_stamina": 80,
                            "stamina_recovery": 18,
                            "accuracy_bonus": 0.25,     # +25% hit chance/precision
                            "food_spawn_multiplier": 0.75  # less food spawns
                        }
                    return {
                        "name": name_box.value(),
                        "kit": selection,
                        "stats": stats
                    }

        # Cards (hover → subtle lift)
        hover_left  = left_card.collidepoint(mouse)
        hover_right = right_card.collidepoint(mouse)
        left_draw  = left_card.move(0, -4 if hover_left  else 0)
        right_draw = right_card.move(0, -4 if hover_right else 0)

        _draw_card(
            screen, left_draw,
            title="A",
            advantage="Hold Shift to sprint",
            weakness="Lower stamina",
            icon_color=(255, 196, 0),
            selected=(selection == "sprinter"),
            fonts=fonts
        )
        _draw_card(
            screen, right_draw,
            title="B",
            advantage="High accuracy",
            weakness="Finds less food",
            icon_color=(140, 120, 255),
            selected=(selection == "sharpshooter"),
            fonts=fonts
        )

        # Name box + hint
        name_box.draw(screen)
        hint = small_font.render("Tip: You can rename your cat anytime in Settings.", True, (90,90,110))
        screen.blit(hint, hint.get_rect(center=(W//2, name_box.rect.bottom + 18)))

        # Start button enabled state
        start_btn.enabled = bool(name_box.value() and selection)
        start_btn.draw(screen, mouse)

        # Footer
        footer = small_font.render("Click a card to select. Press Enter to finish name.", True, (80,80,95))
        screen.blit(footer, footer.get_rect(center=(W//2, H - 28)))

        pygame.display.flip()

choice=start_screen(screen)
