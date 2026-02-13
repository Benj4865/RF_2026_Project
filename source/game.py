# Simple Pygame window setup
import pygame
import sys

def main():
	pygame.init()
	screen = pygame.display.set_mode((800, 600))
	pygame.display.set_caption('Simple Pygame Window')
	clock = pygame.time.Clock()

	running = True
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False

		screen.fill((30, 30, 30))
		pygame.display.flip()
		clock.tick(60)

	pygame.quit()
	sys.exit()

if __name__ == "__main__":
	main()
