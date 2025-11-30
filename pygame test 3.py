import pygame
import time
import random
from sys import exit
pygame.init()
clock = pygame.time.Clock()
screen = pygame.display.set_mode((600,400))
pygame.display.set_caption('Runner')
Scenes=[pygame.image.load('background test.jpg').convert(),pygame.image.load('Scene1.jpg').convert()]
Bubble=pygame.image.load('Bubble.png').convert_alpha()
notice=pygame.image.load('notice.png').convert_alpha()
speech=pygame.image.load('speech.png').convert_alpha()
char_pos=[300,200]
char_pos1=0

obstacle_rect=pygame.Rect(random.randint(0,500),random.randint(0,500),25,25)
bubble_rect = Bubble.get_rect(topleft=char_pos)

CurrentScene=Scenes[0]
#how to click on an object?
def noticesign(x,y):
    screen.blit(notice,(x,y))
    if (char_pos[0]-x)**2+(char_pos[1]-y)**2 <= 30000:
        return True

def speechbubble(message):
    screen.blit(speech,(250,50))
    font = pygame.font.Font('Grand9K Pixel.ttf', 20)
    text=font.render(message, True, (0, 0,0))
    screen.blit(text, (290, 305))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
            
        position = char_pos
 
        left=False
        right=False
        up=False
        down=False
        bubble_rect.topleft = char_pos
        collision_point = bubble_rect.clip(obstacle_rect).center
        if bubble_rect.colliderect(obstacle_rect):
            print('ahh',collision_point)
        else:
            key = pygame.key.get_pressed()
            speed = 20 if key[pygame.K_LSHIFT] else 10
            if key[pygame.K_a]: char_pos[0] -= speed
            if key[pygame.K_d]: char_pos[0] += speed
            if key[pygame.K_w]: char_pos[1] -= speed
            if key[pygame.K_s]: char_pos[1] += speed


        
        if char_pos[0]>500:
            Scene0=CurrentScene
            CurrentScene=Scenes[Scenes.index(CurrentScene)+1]
            if CurrentScene!=Scene0:
                char_pos=[-300,150]
        elif char_pos[0]<-310:
            Scene0=CurrentScene
            CurrentScene=Scenes[Scenes.index(CurrentScene)-1]
            if CurrentScene!=Scene0:
                char_pos=[500,150]

        screen.blit(CurrentScene,(0,0))
        if CurrentScene==Scenes[0]:
            speechbubble('Choose your character.')
            if event.type == pygame.MOUSEBUTTONDOWN:
                if Bubble.get_rect().collidepoint(event.pos):
                    print("Object clicked!")
        if CurrentScene==Scenes[1]:
            returnnotice=noticesign(300,0)
            if returnnotice==True:
                speechbubble('Welcome!') #<- how to make the sign pop up after a certain amount of time?
                speechbubble('Hello!')

        Bubble.get_rect().topleft = char_pos
        pygame.draw.rect(screen, (0,0,25), obstacle_rect)
        screen.blit(Bubble,char_pos)
        pygame.display.update()
        clock.tick(60)

