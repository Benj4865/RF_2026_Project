import random

import pygame 
from poseEstimator import PoseEstimator

WIDTH, HEIGHT = 600, 800
FPS = 60
PLAYER_LANE = 0 

INITIAL_OBSTACLE_SPEED = 220.0
OBSTACLE_SPEED_INCREASE = 8.0
TIME_SCORE_RATE = 12.0
SPEED_SCORE_FACTOR = 0.08
BASE_OBSTACLE_SPAWN_INTERVAL = 1
MIN_OBSTACLE_SPAWN_INTERVAL = 0.5
OBSTACLE_COLOR = (220, 70, 70)
PLAYER_Y = int(HEIGHT * 0.82)
MAX_ACTIVE_OBSTACLES = 6
MIN_LANE_VERTICAL_GAP = HEIGHT * 0.16
MAX_DELTA_TIME = 1.0 / 30.0
POSE_UPDATE_INTERVAL = 1.0 / 8.0
ENABLE_POSE_INPUT = False
POSE_INFERENCE_WIDTH = 256
POSE_CONFIDENCE = 0.35
POSE_IOU = 0.45
POSE_MAX_DETECTIONS = 1
SPEED_MULTIPLIER_AT_HORIZON = 0.70
SPEED_MULTIPLIER_AT_BOTTOM = 1.35

LANE_OFFSET_BOTTOM = int(WIDTH * 0.25)
LANES = [
    int(WIDTH / 2 - LANE_OFFSET_BOTTOM),
    int(WIDTH / 2 + LANE_OFFSET_BOTTOM),
]
HORIZON_Y = int(HEIGHT * 0.18)
LANE_GAP_TOP = int(WIDTH * 0.03)
LANE_WIDTH_BOTTOM = int(WIDTH * 0.18)
LANE_WIDTH_TOP = int(WIDTH * 0.05)

pose = (
    PoseEstimator(
        inference_width=POSE_INFERENCE_WIDTH,
        confidence=POSE_CONFIDENCE,
        iou=POSE_IOU,
        max_detections=POSE_MAX_DETECTIONS,
    )
    if ENABLE_POSE_INPUT
    else None
)

# Circle properties
circle_radius = 30
circle_x = WIDTH // 2
circle_y = HEIGHT // 2

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
hud_font = pygame.font.SysFont(None, 32)
title_font = pygame.font.SysFont(None, 72)
message_font = pygame.font.SysFont(None, 42)
controls_font = pygame.font.SysFont(None, 24)


def calculate_score(elapsed_time, obstacle_speed):
    return int((elapsed_time * TIME_SCORE_RATE) + (elapsed_time * obstacle_speed * SPEED_SCORE_FACTOR))


def get_current_spawn_interval(obstacle_speed):
    speed_ratio = obstacle_speed / max(1.0, INITIAL_OBSTACLE_SPEED)
    scaled_interval = BASE_OBSTACLE_SPAWN_INTERVAL / max(1.0, speed_ratio)
    return max(MIN_OBSTACLE_SPAWN_INTERVAL, scaled_interval)


def lerp(start, end, amount):
    return start + (end - start) * amount


def get_lane_center(lane_index, amount):
    top_centers = [
        WIDTH // 2 - LANE_GAP_TOP - (LANE_WIDTH_TOP / 2),
        WIDTH // 2 + LANE_GAP_TOP + (LANE_WIDTH_TOP / 2),
    ]
    return lerp(top_centers[lane_index], LANES[lane_index], amount)


def get_lane_width(amount):
    return lerp(LANE_WIDTH_TOP, LANE_WIDTH_BOTTOM, amount)


def get_obstacle_rect(obstacle):
    progress = (obstacle["y"] - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    progress = max(0.0, min(1.0, progress))
    lane_width = get_lane_width(progress)
    obstacle_width = max(18, int(lane_width * 0.45))
    obstacle_height = max(18, int(lane_width * 0.7))
    center_x = get_lane_center(obstacle["lane"], progress)
    return pygame.Rect(
        int(center_x - obstacle_width / 2),
        int(obstacle["y"] - obstacle_height / 2),
        obstacle_width,
        obstacle_height,
    )


def get_obstacle_progress(obstacle):
    progress = (obstacle["y"] - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    return max(0.0, min(1.0, progress))


def get_perspective_speed_multiplier(progress):
    return lerp(SPEED_MULTIPLIER_AT_HORIZON, SPEED_MULTIPLIER_AT_BOTTOM, progress)


def can_spawn_in_lane(obstacles, lane):
    spawn_y = HORIZON_Y + 10
    for obstacle in obstacles:
        if obstacle["lane"] == lane and abs(obstacle["y"] - spawn_y) < MIN_LANE_VERTICAL_GAP:
            return False
    return True


def spawn_obstacle(obstacles, lane):
    obstacles.append({"lane": lane, "y": float(HORIZON_Y + 10)})


def get_player_rect(player_lane):
    player_progress = (PLAYER_Y - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    player_progress = max(0.0, min(1.0, player_progress))
    player_lane_center = get_lane_center(player_lane, player_progress)
    player_lane_width = get_lane_width(player_progress)
    player_width = max(28, int(player_lane_width * 0.5))
    player_height = max(36, int(player_lane_width * 0.85))
    return pygame.Rect(
        int(player_lane_center - player_width / 2),
        int(PLAYER_Y - player_height / 2),
        player_width,
        player_height,
    )


def reset_round():
    return 0.0, 0.0, 0.0, []


def draw_controls_panel(surface, lines):
    padding = 10
    line_height = 22
    panel_width = max(210, max(controls_font.size(line)[0] for line in lines) + padding * 2)
    panel_height = padding * 2 + line_height * len(lines)
    panel_x = WIDTH - panel_width - 16
    panel_y = 16

    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 135))
    surface.blit(panel, (panel_x, panel_y))

    for index, line in enumerate(lines):
        text = controls_font.render(line, True, (230, 230, 230))
        surface.blit(text, (panel_x + padding, panel_y + padding + index * line_height))


running = True 
game_state = "start"
elapsed_time, spawn_timer, pose_timer, obstacles = reset_round()
current_obstacle_speed = INITIAL_OBSTACLE_SPEED
score = 0
final_score = 0
while running: 
    delta_time = clock.tick(FPS) / 1000.0
    delta_time = min(delta_time, MAX_DELTA_TIME)
    obstacle_rects = []

    for event in pygame.event.get(): 
        if event.type == pygame.QUIT: 
            running = False

        if event.type == pygame.KEYDOWN:
            if game_state == "start" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                elapsed_time, spawn_timer, pose_timer, obstacles = reset_round()
                score = 0
                PLAYER_LANE = 0
                game_state = "running"

            elif game_state == "running" and event.key == pygame.K_SPACE:
                PLAYER_LANE = 1 - PLAYER_LANE  # toggles between 0 and 1

            elif game_state == "game_over" and event.key in (pygame.K_r, pygame.K_RETURN):
                elapsed_time, spawn_timer, pose_timer, obstacles = reset_round()
                score = 0
                PLAYER_LANE = 0
                current_obstacle_speed = INITIAL_OBSTACLE_SPEED
                game_state = "start"

    if game_state == "running":
        elapsed_time += delta_time
        spawn_timer += delta_time
        pose_timer += delta_time
        current_obstacle_speed = INITIAL_OBSTACLE_SPEED + (elapsed_time * OBSTACLE_SPEED_INCREASE)
        current_spawn_interval = get_current_spawn_interval(current_obstacle_speed)

        # Throttle pose processing so frame times stay more consistent.
        if ENABLE_POSE_INPUT and pose_timer >= POSE_UPDATE_INTERVAL:
            frame, keypoints, _ = pose.get_frame_and_keypoints()
            pose_timer -= POSE_UPDATE_INTERVAL

            if frame is not None and keypoints is not None and len(keypoints) > 0:
                nose_x = int(keypoints[0][0])
                frame_width = frame.shape[1]

                # Map nose_x from camera frame to game window (inverted)
                circle_x = WIDTH - int(nose_x / frame_width * WIDTH)

        while spawn_timer >= current_spawn_interval:
            available_slots = MAX_ACTIVE_OBSTACLES - len(obstacles)
            if available_slots > 0:
                lanes = list(range(len(LANES)))
                random.shuffle(lanes)
                spawned = False
                for lane in lanes:
                    if spawned:
                        break
                    if can_spawn_in_lane(obstacles, lane):
                        spawn_obstacle(obstacles, lane)
                        spawned = True

            spawn_timer -= current_spawn_interval

        for obstacle in obstacles:
            progress = get_obstacle_progress(obstacle)
            perspective_multiplier = get_perspective_speed_multiplier(progress)
            obstacle["y"] += current_obstacle_speed * perspective_multiplier * delta_time

        obstacles = [obstacle for obstacle in obstacles if obstacle["y"] < HEIGHT + 80]
        obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]

        player_rect = get_player_rect(PLAYER_LANE)
        for obstacle_rect in obstacle_rects:
            if obstacle_rect.colliderect(player_rect):
                final_score = score
                game_state = "game_over"
                break

        score = calculate_score(elapsed_time, current_obstacle_speed)

    elif game_state == "start":
        current_obstacle_speed = INITIAL_OBSTACLE_SPEED

    player_rect = get_player_rect(PLAYER_LANE)
    timer_text = hud_font.render(f"Time: {elapsed_time:05.2f}s", True, (255, 255, 255))
    score_text = hud_font.render(f"Score: {score}", True, (255, 255, 255))
    speed_text = hud_font.render(f"Obstacle Speed: {current_obstacle_speed:.0f}", True, (255, 255, 255))

    screen.fill((0, 0, 0))
    # left lane
    pygame.draw.polygon(screen, (50, 50, 50), [
        (WIDTH//2 - LANE_GAP_TOP - LANE_WIDTH_TOP, HORIZON_Y),
        (WIDTH//2 - LANE_GAP_TOP, HORIZON_Y),
        (LANES[0] + LANE_WIDTH_BOTTOM//2, HEIGHT),
        (LANES[0] - LANE_WIDTH_BOTTOM//2, HEIGHT),
    ])

    # right lane
    pygame.draw.polygon(screen, (50, 50, 50), [
        (WIDTH//2 + LANE_GAP_TOP, HORIZON_Y),
        (WIDTH//2 + LANE_GAP_TOP + LANE_WIDTH_TOP, HORIZON_Y),
        (LANES[1] + LANE_WIDTH_BOTTOM//2, HEIGHT),
        (LANES[1] - LANE_WIDTH_BOTTOM//2, HEIGHT),
    ])

    if not obstacle_rects:
        obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]

    for obstacle_rect in obstacle_rects:
        pygame.draw.rect(screen, OBSTACLE_COLOR, obstacle_rect, border_radius=6)

    pygame.draw.rect(screen, (255, 255, 255), player_rect, border_radius=8)

    if game_state == "running":
        screen.blit(timer_text, (20, 20))
        screen.blit(score_text, (20, 55))
        screen.blit(speed_text, (20, 90))

    if game_state == "start":
        title_text = title_font.render("Road Fighter", True, (255, 255, 255))
        prompt_text = message_font.render("Press SPACE or ENTER to start", True, (220, 220, 220))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 2 - 90))
        screen.blit(prompt_text, (WIDTH // 2 - prompt_text.get_width() // 2, HEIGHT // 2 - 25))

    elif game_state == "game_over":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        game_over_text = title_font.render("Game Over", True, (255, 110, 110))
        final_score_text = message_font.render(f"Final Score: {final_score}", True, (255, 255, 255))
        restart_text = message_font.render("Press R or ENTER to return", True, (220, 220, 220))
        screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - 110))
        screen.blit(final_score_text, (WIDTH // 2 - final_score_text.get_width() // 2, HEIGHT // 2 - 35))
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 20))

    if game_state == "start":
        controls_lines = [
            "Controls:",
            "SPACE / ENTER: Start",
            "SPACE: Change lane",
        ]
    elif game_state == "running":
        controls_lines = [
            "Controls:",
            "SPACE: Change lane",
            "Close window: Quit",
        ]
    else:
        controls_lines = [
            "Controls:",
            "R / ENTER: Back to start",
            "Close window: Quit",
        ]

    draw_controls_panel(screen, controls_lines)

    pygame.display.flip()

if pose is not None:
    pose.release()
pygame.quit()            

