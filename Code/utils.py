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

def load_image(path):
    image = pygame.image.load(path).convert_alpha()
    return image

def scale_image_to_rect(image, rect):
    return pygame.transform.scale(image, (rect.width, rect.height))

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


def get_obstacle_hitbox(obstacle):
    """Returns a thin rect at the bottom of the obstacle representing ground contact."""
    full_rect = get_obstacle_rect(obstacle)
    hitbox_height = max(6, full_rect.height // 4)
    return pygame.Rect(
        full_rect.x,
        full_rect.bottom - hitbox_height,
        full_rect.width,
        hitbox_height,
    )


def get_coop_obstacle_rect(obstacle):
    progress = (obstacle["y"] - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    progress = max(0.0, min(1.0, progress))
    lane_width = get_lane_width(progress)
    obstacle_width = max(16, int(lane_width * 0.35))
    obstacle_height = max(18, int(lane_width * 0.65))
    center_x = WIDTH // 2
    return pygame.Rect(
        int(center_x - obstacle_width / 2),
        int(obstacle["y"] - obstacle_height / 2),
        obstacle_width,
        obstacle_height,
    )


def get_ground_hitbox_from_rect(rect):
    hitbox_height = max(6, rect.height // 4)
    return pygame.Rect(
        rect.x,
        rect.bottom - hitbox_height,
        rect.width,
        hitbox_height,
    )


def get_coop_player_rects(jump_offset=0):
    player_y = PLAYER_Y - jump_offset
    base_progress = (PLAYER_Y - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    base_progress = max(0.0, min(1.0, base_progress))

    left_center_x = get_lane_center(0, base_progress)
    right_center_x = get_lane_center(1, base_progress)
    lane_width = get_lane_width(base_progress)
    player_width = max(24, int(lane_width * 0.35))
    player_height = max(34, int(lane_width * 0.75))

    left_rect = pygame.Rect(
        int(left_center_x - player_width / 2),
        int(player_y - player_height / 2),
        player_width,
        player_height,
    )
    right_rect = pygame.Rect(
        int(right_center_x - player_width / 2),
        int(player_y - player_height / 2),
        player_width,
        player_height,
    )
    return left_rect, right_rect


def get_player_ground_hitbox(rect):
    hitbox_height = max(4, rect.height // 5)
    return pygame.Rect(
        rect.x,
        rect.bottom - hitbox_height,
        rect.width,
        hitbox_height,
    )


def get_coop_player_foot_hitbox(rect):
    # Co-op uses a narrower and thinner foot contact to reduce unfair jump collisions.
    hitbox_width = max(10, int(rect.width * 0.62))
    hitbox_height = max(2, rect.height // 12)
    return pygame.Rect(
        int(rect.centerx - hitbox_width / 2),
        rect.bottom - hitbox_height,
        hitbox_width,
        hitbox_height,
    )


def get_coop_obstacle_bottom_hitbox(obstacle):
    full_rect = get_obstacle_rect(obstacle)
    hitbox_width = max(10, int(full_rect.width * 0.72))
    hitbox_height = max(2, full_rect.height // 12)
    return pygame.Rect(
        int(full_rect.centerx - hitbox_width / 2),
        full_rect.bottom - hitbox_height,
        hitbox_width,
        hitbox_height,
    )


def get_coop_beam_rect(left_rect, right_rect):
    beam_height = max(6, min(left_rect.height, right_rect.height) // 6)
    beam_top = (left_rect.centery + right_rect.centery) // 2 - beam_height // 2
    beam_left = left_rect.right
    beam_right = right_rect.left
    return pygame.Rect(
        beam_left,
        beam_top,
        max(1, beam_right - beam_left),
        beam_height,
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
    return get_lane_player_rect(player_lane)


def get_lane_player_rect(player_lane, jump_offset=0):
    player_progress = (PLAYER_Y - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    player_progress = max(0.0, min(1.0, player_progress))
    player_lane_center = get_lane_center(player_lane, player_progress)
    player_lane_width = get_lane_width(player_progress)
    player_width = max(28, int(player_lane_width * 0.5))
    player_height = max(36, int(player_lane_width * 0.85))
    return pygame.Rect(
        int(player_lane_center - player_width / 2),
        int((PLAYER_Y - jump_offset) - player_height / 2),
        player_width,
        player_height,
    )


def get_singleplayer_jump_rect(lane_progress, jump_offset=0):
    player_y = PLAYER_Y - jump_offset
    base_progress = (PLAYER_Y - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    base_progress = max(0.0, min(1.0, base_progress))

    left_center_x = get_lane_center(0, base_progress)
    right_center_x = get_lane_center(1, base_progress)
    player_lane_center = lerp(left_center_x, right_center_x, lane_progress)
    player_lane_width = get_lane_width(base_progress)
    player_width = max(28, int(player_lane_width * 0.5))
    player_height = max(36, int(player_lane_width * 0.85))
    return pygame.Rect(
        int(player_lane_center - player_width / 2),
        int(player_y - player_height / 2),
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
