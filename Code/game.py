import pygame
from poseEstimator import PoseEstimator
import sys

# Pygame setup
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Move the Circle with Your Position')
clock = pygame.time.Clock()


# Load pose estimator
pose = PoseEstimator()

# Circle properties
circle_radius = 30
circle_x = WIDTH // 2
circle_y = HEIGHT // 2

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Quit event detected. Exiting game loop.")
            running = False

    # Get pose keypoints from pose estimator
    frame, keypoints, _ = pose.get_frame_and_keypoints()
    if frame is not None:
        pass #As frame exists, no need to print anything here
    else:
        print("No image from camera.")

    if keypoints is not None and len(keypoints) > 0:
        
        print(f"Keypoints detected: {keypoints}")
        # Use nose (keypoint 0) for horizontal position
        nose_x = int(keypoints[0][0])
        
        frame_width = frame.shape[1]
        
        print(f"Nose x: {nose_x}, Frame width: {frame_width}")
        
        # Map nose_x from camera frame to game window (inverted)
        circle_x = WIDTH - int(nose_x / frame_width * WIDTH)
        
    else:
        print("No person detected.")

    screen.fill((30, 30, 30))
    pygame.draw.circle(screen, (0, 200, 255), (circle_x, circle_y), circle_radius)
    font = pygame.font.Font(None, 36)
    text_surface = font.render(f"Position: ({circle_x}, {circle_y})", True, (255, 255, 255))
    screen.blit(text_surface, (10, 10))
    pygame.display.flip()
    clock.tick(30)

print("Releasing resources...")
pose.release()
pygame.quit()
sys.exit()
