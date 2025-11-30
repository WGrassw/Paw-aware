import pygame
import time
import random
from sys import exit
screen = pygame.display.set_mode((1200,800))
pygame.display.set_caption('Runner')


full=pygame.image.load("fullcatheart.png").convert_alpha()
half=pygame.image.load("halfcatheart.png").convert_alpha()
empty=pygame.image.load("emptycatheart.png").convert_alpha()

def draw_healthbar(screen,health):
    x=25
    if health==9:
        for k in range(9):
            screen.blit(full, (x,30))
            x+=50
    elif health%1!=0:
        h=9-(health+0.5)
        for k in range(int(health)):
            screen.blit(full, (x,30))
            x+=50
        screen.blit(half, (x,30))
        x+=50
        for k in range(int(h)):
            screen.blit(empty, (x,30))
            x+=50
    else:
        h=9-health
        for k in range(health):
            screen.blit(full, (x,30))
            x+=50
        for k in range(h):
            screen.blit(empty, (x,30))
            x+=50
    if health==0:
        print('dead')
            
