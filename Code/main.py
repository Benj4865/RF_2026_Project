import pygame 

WIDTH, HEIGHT = 800, 600
FPS = 60
LANES = [200,600]
PLAYER_LANE = 0 

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

running = True 
while running: 
        for event in pygame.event.get(): 

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    PLAYER_LANE = 1 - PLAYER_LANE  # toggles between 0 and 1

            if event.type == pygame.QUIT: 
                running = False

        screen.fill((0, 0, 0))
        pygame.draw.polygon(screen, (50, 50, 50), [
            (150, 0),  # top left
            (250, 0),  # top right
            (250, HEIGHT),  # bottom right
            (150, HEIGHT),  # bottom left
        ])

        pygame.draw.rect(screen, (255, 255, 255), (LANES[PLAYER_LANE] - 25, 500, 50, 50))

        pygame.display.flip()
        clock.tick(FPS)

pygame.quit()            

