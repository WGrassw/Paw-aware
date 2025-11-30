import pygame
from sys import exit
pygame.init()
screen = pygame.display.set_mode((600, 400))
pygame.display.set_caption('Runner')
clock = pygame.time.Clock()

background1=pygame.image.load('background test.jpg').convert()
character=pygame.image.load('cattt.png').convert_alpha()
char_pos=-300

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    screen.blit(background1,(0,0))
    screen.blit(character,(char_pos,150))
    char_pos+=4
    if char_pos>=600:
        char_pos=-300

    pygame.display.update()
    clock.tick(60)
