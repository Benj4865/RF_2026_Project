import random

import pygame

from config import (
    WIDTH, HEIGHT, FPS,
    OBSTACLE_COLOR, OBSTACLE_SPEED_INCREASE, INITIAL_OBSTACLE_SPEED,
    MAX_ACTIVE_OBSTACLES, MAX_DELTA_TIME,
    POSE_UPDATE_INTERVAL, ENABLE_POSE_INPUT,
    POSE_INFERENCE_WIDTH, POSE_CONFIDENCE, POSE_IOU, POSE_MAX_DETECTIONS,
    LANES, HORIZON_Y, LANE_GAP_TOP, LANE_WIDTH_TOP, LANE_WIDTH_BOTTOM,
)
from utils import (
    calculate_score, get_current_spawn_interval,
    get_obstacle_rect, get_obstacle_hitbox, get_obstacle_progress, get_perspective_speed_multiplier,
    can_spawn_in_lane, spawn_obstacle,
    get_player_rect, reset_round, draw_controls_panel,
)
from poseEstimator import PoseEstimator

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

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
hud_font = pygame.font.SysFont(None, 32)
title_font = pygame.font.SysFont(None, 72)
message_font = pygame.font.SysFont(None, 42)
controls_font = pygame.font.SysFont(None, 24)

PLAYER_LANE = 0
circle_x = WIDTH // 2
circle_y = HEIGHT // 2

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

        if ENABLE_POSE_INPUT and pose_timer >= POSE_UPDATE_INTERVAL:
            frame, keypoints, _ = pose.get_frame_and_keypoints()
            pose_timer -= POSE_UPDATE_INTERVAL

            if frame is not None and keypoints is not None and len(keypoints) > 0:
                nose_x = int(keypoints[0][0])
                frame_width = frame.shape[1]
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
        obstacle_hitboxes = [get_obstacle_hitbox(obstacle) for obstacle in obstacles]

        player_rect = get_player_rect(PLAYER_LANE)
        for obstacle_hitbox in obstacle_hitboxes:
            if obstacle_hitbox.colliderect(player_rect):
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
        (WIDTH // 2 - LANE_GAP_TOP - LANE_WIDTH_TOP, HORIZON_Y),
        (WIDTH // 2 - LANE_GAP_TOP, HORIZON_Y),
        (LANES[0] + LANE_WIDTH_BOTTOM // 2, HEIGHT),
        (LANES[0] - LANE_WIDTH_BOTTOM // 2, HEIGHT),
    ])

    # right lane
    pygame.draw.polygon(screen, (50, 50, 50), [
        (WIDTH // 2 + LANE_GAP_TOP, HORIZON_Y),
        (WIDTH // 2 + LANE_GAP_TOP + LANE_WIDTH_TOP, HORIZON_Y),
        (LANES[1] + LANE_WIDTH_BOTTOM // 2, HEIGHT),
        (LANES[1] - LANE_WIDTH_BOTTOM // 2, HEIGHT),
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

    draw_controls_panel(screen, controls_lines, controls_font)

    pygame.display.flip()

if pose is not None:
    pose.release()
pygame.quit()
