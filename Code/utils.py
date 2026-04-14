import random

import pygame

from config import (
    WIDTH, HEIGHT,
    HORIZON_Y, LANES, LANE_GAP_TOP, LANE_WIDTH_TOP,
    LANE_WIDTH_BOTTOM, PLAYER_Y,
    SPEED_MULTIPLIER_AT_HORIZON, SPEED_MULTIPLIER_AT_BOTTOM,
    INITIAL_OBSTACLE_SPEED,
    BASE_OBSTACLE_SPAWN_INTERVAL, MIN_OBSTACLE_SPAWN_INTERVAL,
    MIN_LANE_VERTICAL_GAP,
    TIME_SCORE_RATE, SPEED_SCORE_FACTOR,
)


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


def draw_controls_panel(surface, lines, font):
    padding = 10
    line_height = 22
    panel_width = max(210, max(font.size(line)[0] for line in lines) + padding * 2)
    panel_height = padding * 2 + line_height * len(lines)
    panel_x = WIDTH - panel_width - 16
    panel_y = 16

    panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 135))
    surface.blit(panel, (panel_x, panel_y))

    for index, line in enumerate(lines):
        text = font.render(line, True, (230, 230, 230))
        surface.blit(text, (panel_x + padding, panel_y + padding + index * line_height))
