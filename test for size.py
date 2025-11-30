import pygame
from sys import exit
pygame.init()
screen = pygame.display.set_mode((600,400))
pygame.display.set_caption('Runner')
clock = pygame.time.Clock()

Scenes=[pygame.image.load('background test.jpg').convert(),pygame.image.load('Scene1.jpg').convert()]
screen.blit(Scenes[0],(0,0))
speech=pygame.image.load('speech.png').convert_alpha()
screen.blit(speech,(250,50))
font = pygame.font.Font('Grand9K Pixel.ttf', 20)
text=font.render("Pixel Text", True, (0, 0,0))
screen.blit(text, (290, 280))

    
pygame.display.update()
clock.tick(60)
print(get_fonts())
