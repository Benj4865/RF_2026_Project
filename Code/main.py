import random

import pygame

from config import (
    WIDTH, HEIGHT, FPS,
    OBSTACLE_COLOR, OBSTACLE_SPEED_INCREASE, INITIAL_OBSTACLE_SPEED,
    MAX_ACTIVE_OBSTACLES, MAX_DELTA_TIME,
    POSE_UPDATE_INTERVAL, ENABLE_POSE_INPUT,
    POSE_INFERENCE_WIDTH, POSE_CONFIDENCE, POSE_IOU, POSE_MAX_DETECTIONS,
    LANES, HORIZON_Y, LANE_GAP_TOP, LANE_WIDTH_TOP, LANE_WIDTH_BOTTOM,
    COOP_SYNC_WINDOW, COOP_JUMP_DURATION, COOP_JUMP_HEIGHT,
    COOP_JUMP_COLLISION_GRACE,
    COOP_AIRBORNE_DEADZONE_HEIGHT,
    COOP_SPAWN_INTERVAL_MIN, COOP_SPAWN_INTERVAL_MAX, COOP_SPEED_MULTIPLIER,
)
from utils import (
    calculate_score, get_current_spawn_interval,
    get_obstacle_rect, get_obstacle_hitbox, get_obstacle_progress, get_perspective_speed_multiplier,
    get_coop_obstacle_rect, get_ground_hitbox_from_rect,
    can_spawn_in_lane, spawn_obstacle,
    get_player_rect, get_coop_player_rects, get_coop_beam_rect, get_player_ground_hitbox,
    reset_round, draw_controls_panel,
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
game_mode = "single"
elapsed_time, spawn_timer, pose_timer, obstacles = reset_round()
current_obstacle_speed = INITIAL_OBSTACLE_SPEED
score = 0
final_score = 0
coop_jump_timer = 0.0
coop_jump_grace_timer = 0.0
coop_next_spawn_interval = random.uniform(COOP_SPAWN_INTERVAL_MIN, COOP_SPAWN_INTERVAL_MAX)
last_left_jump_press = -10.0
last_right_jump_press = -10.0

while running:
    delta_time = clock.tick(FPS) / 1000.0
    delta_time = min(delta_time, MAX_DELTA_TIME)
    obstacle_rects = []

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if game_state == "start" and event.key == pygame.K_1:
                game_mode = "single"

            elif game_state == "start" and event.key == pygame.K_2:
                game_mode = "coop"

            elif game_state == "start" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                elapsed_time, spawn_timer, pose_timer, obstacles = reset_round()
                score = 0
                PLAYER_LANE = 0
                coop_jump_timer = 0.0
                coop_jump_grace_timer = 0.0
                coop_next_spawn_interval = random.uniform(COOP_SPAWN_INTERVAL_MIN, COOP_SPAWN_INTERVAL_MAX)
                last_left_jump_press = -10.0
                last_right_jump_press = -10.0
                game_state = "running"

            elif game_state == "running" and game_mode == "single" and event.key == pygame.K_SPACE:
                PLAYER_LANE = 1 - PLAYER_LANE  # toggles between 0 and 1

            elif game_state == "running" and game_mode == "coop" and event.key in (pygame.K_a, pygame.K_l):
                if event.key == pygame.K_a:
                    last_left_jump_press = elapsed_time
                else:
                    last_right_jump_press = elapsed_time

                if (
                    abs(last_left_jump_press - last_right_jump_press) <= COOP_SYNC_WINDOW
                    and coop_jump_timer <= 0.0
                ):
                    coop_jump_timer = COOP_JUMP_DURATION
                    coop_jump_grace_timer = COOP_JUMP_COLLISION_GRACE

            elif game_state == "game_over" and event.key in (pygame.K_r, pygame.K_RETURN):
                elapsed_time, spawn_timer, pose_timer, obstacles = reset_round()
                score = 0
                PLAYER_LANE = 0
                current_obstacle_speed = INITIAL_OBSTACLE_SPEED
                coop_jump_timer = 0.0
                coop_jump_grace_timer = 0.0
                coop_next_spawn_interval = random.uniform(COOP_SPAWN_INTERVAL_MIN, COOP_SPAWN_INTERVAL_MAX)
                game_state = "start"

    if game_state == "running":
        elapsed_time += delta_time
        spawn_timer += delta_time
        pose_timer += delta_time
        base_speed = INITIAL_OBSTACLE_SPEED + (elapsed_time * OBSTACLE_SPEED_INCREASE)
        if game_mode == "coop":
            current_obstacle_speed = base_speed * COOP_SPEED_MULTIPLIER
            current_spawn_interval = coop_next_spawn_interval
        else:
            current_obstacle_speed = base_speed
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
                if game_mode == "single":
                    lanes = list(range(len(LANES)))
                    random.shuffle(lanes)
                    spawned = False
                    for lane in lanes:
                        if spawned:
                            break
                        if can_spawn_in_lane(obstacles, lane):
                            spawn_obstacle(obstacles, lane)
                            spawned = True
                else:
                    spawn_y = HORIZON_Y + 10
                    can_spawn_center = all(
                        abs(obstacle["y"] - spawn_y) >= int(HEIGHT * 0.14)
                        for obstacle in obstacles
                    )
                    if can_spawn_center:
                        obstacles.append({"y": float(spawn_y), "prev_y": float(spawn_y)})

            spawn_timer -= current_spawn_interval
            if game_mode == "coop":
                coop_next_spawn_interval = random.uniform(COOP_SPAWN_INTERVAL_MIN, COOP_SPAWN_INTERVAL_MAX)
                current_spawn_interval = coop_next_spawn_interval

        for obstacle in obstacles:
            obstacle["prev_y"] = obstacle["y"]
            progress = get_obstacle_progress(obstacle)
            perspective_multiplier = get_perspective_speed_multiplier(progress)
            obstacle["y"] += current_obstacle_speed * perspective_multiplier * delta_time

        obstacles = [obstacle for obstacle in obstacles if obstacle["y"] < HEIGHT + 80]
        if game_mode == "single":
            obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]
            obstacle_hitboxes = [get_obstacle_hitbox(obstacle) for obstacle in obstacles]

            player_rect = get_player_rect(PLAYER_LANE)
            for obstacle_hitbox in obstacle_hitboxes:
                if obstacle_hitbox.colliderect(player_rect):
                    final_score = score
                    game_state = "game_over"
                    break
        else:
            if coop_jump_timer > 0.0:
                coop_jump_timer -= delta_time
            if coop_jump_grace_timer > 0.0:
                coop_jump_grace_timer -= delta_time

            jump_height = 0
            if coop_jump_timer > 0.0:
                jump_progress = 1.0 - (coop_jump_timer / COOP_JUMP_DURATION)
                jump_height = int(COOP_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))

            obstacle_rects = [get_coop_obstacle_rect(obstacle) for obstacle in obstacles]
            obstacle_hitboxes = []
            for obstacle, obstacle_rect in zip(obstacles, obstacle_rects):
                current_hitbox = get_ground_hitbox_from_rect(obstacle_rect)
                previous_obstacle = {"y": obstacle.get("prev_y", obstacle["y"])}
                previous_rect = get_coop_obstacle_rect(previous_obstacle)
                previous_hitbox = get_ground_hitbox_from_rect(previous_rect)
                obstacle_hitboxes.append(current_hitbox.union(previous_hitbox))

            left_player_rect, right_player_rect = get_coop_player_rects(jump_height)
            beam_rect = get_coop_beam_rect(left_player_rect, right_player_rect)
            left_player_ground_hitbox = get_player_ground_hitbox(left_player_rect)
            right_player_ground_hitbox = get_player_ground_hitbox(right_player_rect)

            for obstacle_hitbox in obstacle_hitboxes:
                if coop_jump_grace_timer > 0.0:
                    continue
                if jump_height >= COOP_AIRBORNE_DEADZONE_HEIGHT:
                    continue
                if (
                    obstacle_hitbox.colliderect(left_player_ground_hitbox)
                    or obstacle_hitbox.colliderect(right_player_ground_hitbox)
                    or obstacle_hitbox.colliderect(beam_rect)
                ):
                    final_score = score
                    game_state = "game_over"
                    break

        score = calculate_score(elapsed_time, current_obstacle_speed)

    elif game_state == "start":
        current_obstacle_speed = INITIAL_OBSTACLE_SPEED
        coop_jump_timer = 0.0
        coop_jump_grace_timer = 0.0

    player_rect = get_player_rect(PLAYER_LANE)
    left_player_rect = None
    right_player_rect = None
    beam_rect = None
    if game_mode == "coop":
        jump_height = 0
        if game_state == "running" and coop_jump_timer > 0.0:
            jump_progress = 1.0 - (coop_jump_timer / COOP_JUMP_DURATION)
            jump_height = int(COOP_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))
        left_player_rect, right_player_rect = get_coop_player_rects(jump_height)
        beam_rect = get_coop_beam_rect(left_player_rect, right_player_rect)

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
        if game_mode == "single":
            obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]
        else:
            obstacle_rects = [get_coop_obstacle_rect(obstacle) for obstacle in obstacles]

    for obstacle_rect in obstacle_rects:
        pygame.draw.rect(screen, OBSTACLE_COLOR, obstacle_rect, border_radius=6)

    if game_mode == "single":
        pygame.draw.rect(screen, (255, 255, 255), player_rect, border_radius=8)
    else:
        pygame.draw.rect(screen, (255, 255, 255), left_player_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), right_player_rect, border_radius=8)
        pygame.draw.rect(screen, (120, 220, 255), beam_rect, border_radius=4)

    if game_state == "running":
        screen.blit(timer_text, (20, 20))
        screen.blit(score_text, (20, 55))
        screen.blit(speed_text, (20, 90))

    if game_state == "start":
        mode_text = message_font.render(
            f"Mode: {'Single Player' if game_mode == 'single' else 'Co-op'} (press 1 or 2)",
            True,
            (220, 220, 220),
        )
        title_text = title_font.render("Road Fighter", True, (255, 255, 255))
        prompt_text = message_font.render("Press SPACE or ENTER to start", True, (220, 220, 220))
        screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 2 - 90))
        screen.blit(prompt_text, (WIDTH // 2 - prompt_text.get_width() // 2, HEIGHT // 2 - 25))
        screen.blit(mode_text, (WIDTH // 2 - mode_text.get_width() // 2, HEIGHT // 2 + 30))

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
            "1: Single Player",
            "2: Co-op",
            "SPACE / ENTER: Start",
        ]
    elif game_state == "running":
        if game_mode == "single":
            controls_lines = [
                "Controls:",
                "SPACE: Change lane",
                "Close window: Quit",
            ]
        else:
            controls_lines = [
                "Controls:",
                "A + L (sync): Jump both",
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
