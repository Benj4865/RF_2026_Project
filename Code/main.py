import random
import os 
import math
import uuid
import pygame

from config import (
    WIDTH, HEIGHT, FPS,
    OBSTACLE_COLOR, OBSTACLE_SPEED_INCREASE, INITIAL_OBSTACLE_SPEED,
    MAX_ACTIVE_OBSTACLES, MAX_DELTA_TIME,
    LANES, HORIZON_Y, LANE_GAP_TOP, LANE_WIDTH_TOP, LANE_WIDTH_BOTTOM,
    COOP_JUMP_DURATION, COOP_JUMP_HEIGHT,
    COOP_COLLISION_ZONE_HEIGHT, PLAYER_Y,
    COOP_SPAWN_INTERVAL_MIN, COOP_SPAWN_INTERVAL_MAX, COOP_SPEED_MULTIPLIER,
    SINGLE_JUMP_DURATION, SINGLE_JUMP_HEIGHT, SINGLE_JUMP_COOLDOWN, 
)
from utils import (
    calculate_score, generate_score_qr, get_current_spawn_interval,
    get_obstacle_rect, get_obstacle_hitbox, get_perspective_speed_multiplier,
    can_spawn_in_lane, spawn_obstacle,
    get_player_rect, get_singleplayer_jump_rect,
    get_lane_player_rect, get_player_ground_hitbox,
    get_coop_player_foot_hitbox, get_coop_obstacle_bottom_hitbox,
    reset_round, draw_controls_panel, get_sprite_frame, lerp, render_fitted_text
)

pygame.init()
pygame.mouse.set_visible(False)
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
clock = pygame.time.Clock()
hud_font = pygame.font.SysFont(None, 32)
title_font = pygame.font.SysFont(None, 72)
message_font = pygame.font.SysFont(None, 42)
controls_font = pygame.font.SysFont(None, 24)
scroll_offset = 0.0

PLAYER_LANE = 0
circle_x = WIDTH // 2
circle_y = HEIGHT // 2

running = True
game_state = "start"
game_mode = "single"
elapsed_time, spawn_timer, obstacles = reset_round()
current_obstacle_speed = INITIAL_OBSTACLE_SPEED
score = 0
final_score = 0
single_jump_timer = 0.0
single_jump_cooldown_timer = 0.0
single_jump_start_lane = 0
single_jump_target_lane = 0
left_coop_jump_timer = 0.0
right_coop_jump_timer = 0.0
env_objects = []
env_spawn_timer = 0.0
next_env_spawn_interval = 0.0
single_next_spawn_interval = get_current_spawn_interval(INITIAL_OBSTACLE_SPEED)
single_last_spawn_lane = None
single_lane_streak = 0
coop_lane_cooldowns = [0.0 for _ in LANES]
coop_lane_spawn_timers = [0.0 for _ in LANES]
coop_lane_next_spawn_intervals = [0.0 for _ in LANES]


def make_blue_variant(sprite):
    blue_sprite = sprite.copy()
    # Shift hue toward blue and darken so it stays distinct but not too bright.
    blue_sprite.fill((0, 45, 120, 0), special_flags=pygame.BLEND_RGBA_ADD)
    blue_sprite.fill((40, 12, 0, 0), special_flags=pygame.BLEND_RGBA_SUB)
    blue_sprite.fill((182, 182, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return blue_sprite

sheet = pygame.image.load("assets/frog.png").convert_alpha()
player_sprite = get_sprite_frame(sheet, 0, 3, 80, 80)
coop_left_player_sprite = player_sprite
coop_right_player_sprite = make_blue_variant(player_sprite)

obstacle_images = [
    pygame.image.load(f"assets/obstacles/{f}").convert_alpha()
    for f in os.listdir("assets/obstacles")
    if f.endswith(".png")
]

BACKGROUND_COLOR = (98, 82, 82)
BACKGROUND_SHADE_COLOR = (88, 72, 72)
SHOULDER_COLOR = (122, 112, 114)
SHOULDER_SHADE_COLOR = (106, 96, 98)
ROAD_COLOR = (148, 136, 138)
ROAD_SHADE_COLOR = (132, 120, 122)
CENTER_MEDIAN_COLOR = (124, 112, 114)
EDGE_LINE_COLOR = (58, 48, 50)
LANE_MARK_COLOR = (210, 206, 198)
LANE_MARK_WORLD_SPACING = 42.0
LANE_MARK_TRACK_SCALE = 140.0
LANE_MARK_TRACK_CURVE = 9.0
LANE_MARK_SCROLL_MULTIPLIER = 0.32
OBSTACLE_LINE_SYNC_FACTOR = 1.0
LANE_MARK_THICKNESS_HORIZON = 3
LANE_MARK_THICKNESS_NEAR = 14
LANE_MARK_WIDTH_FACTOR = 0.055

SKY_TOP_COLOR = (20, 24, 30)
SKY_HORIZON_COLOR = (52, 54, 60)
INDUSTRIAL_BUILDING_COLOR = (42, 44, 48)
INDUSTRIAL_BUILDING_SHADE = (34, 36, 40)
INDUSTRIAL_WINDOW_COLOR = (118, 96, 66)
SMOKE_COLOR = (86, 88, 94)

ENV_OBJECT_INTERVAL_MIN = 0.45
ENV_OBJECT_INTERVAL_MAX = 0.95
ENV_OBJECT_KINDS = ["crate", "barrel", "pipe", "stack"]
next_env_spawn_interval = random.uniform(ENV_OBJECT_INTERVAL_MIN, ENV_OBJECT_INTERVAL_MAX)

SINGLE_SPAWN_JITTER_MIN = 0.72
SINGLE_SPAWN_JITTER_MAX = 1.35
SINGLE_MAX_SAME_LANE_STREAK = 3
SINGLE_CROSS_LANE_BLOCK_GAP = 92

COOP_LANE_COOLDOWN_START = COOP_JUMP_DURATION * 1.18
COOP_LANE_COOLDOWN_MIN = COOP_JUMP_DURATION * 0.52
COOP_LANE_COOLDOWN_SPEED_RANGE = 260.0
COOP_MULTI_SPAWN_CHANCE_BASE = 0.46
COOP_MULTI_SPAWN_CHANCE_MAX = 0.82
COOP_MULTI_SPAWN_SPEED_RANGE = 280.0
COOP_SPAWN_JITTER_MIN = 0.72
COOP_SPAWN_JITTER_MAX = 1.35

TEXT_SIDE_MARGIN = max(18, int(WIDTH * 0.05))


def build_industrial_skyline():
    rng = random.Random(2026)
    buildings = []
    chimneys = []
    x = -32
    while x < WIDTH + 48:
        width = rng.randint(34, 86)
        height = rng.randint(34, 94)
        buildings.append({"x": x, "width": width, "height": height})
        if rng.random() < 0.42:
            chimney_x = x + rng.randint(6, max(7, width - 12))
            chimneys.append({
                "x": chimney_x,
                "width": rng.randint(6, 11),
                "height": rng.randint(42, 92),
                "smoke_phase": rng.uniform(0.0, 1000.0),
            })
        x += rng.randint(20, 44)
    return buildings, chimneys


INDUSTRIAL_BUILDINGS, INDUSTRIAL_CHIMNEYS = build_industrial_skyline()


def get_next_single_spawn_interval(obstacle_speed):
    base_interval = get_current_spawn_interval(obstacle_speed)
    return random.uniform(base_interval * SINGLE_SPAWN_JITTER_MIN, base_interval * SINGLE_SPAWN_JITTER_MAX)


def would_block_both_lanes_near_spawn(obstacles, lane):
    spawn_y = HORIZON_Y + 10
    other_lane = 1 - lane
    for obstacle in obstacles:
        if obstacle["lane"] == other_lane and abs(obstacle["y"] - spawn_y) < SINGLE_CROSS_LANE_BLOCK_GAP:
            return True
    return False


def get_next_coop_lane_cooldown(obstacle_speed):
    coop_base_speed = INITIAL_OBSTACLE_SPEED * COOP_SPEED_MULTIPLIER
    difficulty = (obstacle_speed - coop_base_speed) / COOP_LANE_COOLDOWN_SPEED_RANGE
    difficulty = max(0.0, min(1.0, difficulty))
    return lerp(COOP_LANE_COOLDOWN_START, COOP_LANE_COOLDOWN_MIN, difficulty)


def get_coop_lane_spawn_chance(obstacle_speed):
    coop_base_speed = INITIAL_OBSTACLE_SPEED * COOP_SPEED_MULTIPLIER
    difficulty = (obstacle_speed - coop_base_speed) / COOP_MULTI_SPAWN_SPEED_RANGE
    difficulty = max(0.0, min(1.0, difficulty))
    return lerp(COOP_MULTI_SPAWN_CHANCE_BASE, COOP_MULTI_SPAWN_CHANCE_MAX, difficulty)


def get_next_coop_spawn_interval(obstacle_speed):
    base_interval = random.uniform(COOP_SPAWN_INTERVAL_MIN, COOP_SPAWN_INTERVAL_MAX)
    coop_base_speed = INITIAL_OBSTACLE_SPEED * COOP_SPEED_MULTIPLIER
    difficulty = (obstacle_speed - coop_base_speed) / COOP_MULTI_SPAWN_SPEED_RANGE
    difficulty = max(0.0, min(1.0, difficulty))
    jitter_scale = random.uniform(COOP_SPAWN_JITTER_MIN, COOP_SPAWN_JITTER_MAX)
    speed_scale = lerp(1.06, 0.86, difficulty)
    return base_interval * jitter_scale * speed_scale


def reset_coop_spawn_state(obstacle_speed):
    intervals = [get_next_coop_spawn_interval(obstacle_speed) for _ in LANES]
    # Start each lane with a different phase so they don't repeatedly sync.
    timers = [random.uniform(0.0, interval * 0.68) for interval in intervals]
    return timers, intervals


def get_ground_regions(amount):
    left_outer = lerp(WIDTH // 2 - LANE_GAP_TOP - LANE_WIDTH_TOP, LANES[0] - LANE_WIDTH_BOTTOM // 2, amount)
    right_outer = lerp(WIDTH // 2 + LANE_GAP_TOP + LANE_WIDTH_TOP, LANES[1] + LANE_WIDTH_BOTTOM // 2, amount)

    left_inner = lerp(WIDTH // 2 - LANE_GAP_TOP, LANES[0] + LANE_WIDTH_BOTTOM // 2, amount)
    right_inner = lerp(WIDTH // 2 + LANE_GAP_TOP, LANES[1] - LANE_WIDTH_BOTTOM // 2, amount)

    transition_width = lerp(LANE_WIDTH_TOP * 0.08, LANE_WIDTH_BOTTOM * 0.3, amount)
    left_trans = left_outer - transition_width
    right_trans = right_outer + transition_width

    return left_trans, left_outer, left_inner, right_inner, right_outer, right_trans


def blend_color(color_a, color_b, amount):
    amount = max(0.0, min(1.0, amount))
    return (
        int(lerp(color_a[0], color_b[0], amount)),
        int(lerp(color_a[1], color_b[1], amount)),
        int(lerp(color_a[2], color_b[2], amount)),
    )


def draw_industrial_background(surface, elapsed):
    for y in range(HORIZON_Y):
        t = y / max(1, HORIZON_Y)
        sky_color = blend_color(SKY_TOP_COLOR, SKY_HORIZON_COLOR, t)
        pygame.draw.line(surface, sky_color, (0, y), (WIDTH, y))

    for building in INDUSTRIAL_BUILDINGS:
        rect = pygame.Rect(
            building["x"],
            HORIZON_Y - building["height"],
            building["width"],
            building["height"],
        )
        pygame.draw.rect(surface, INDUSTRIAL_BUILDING_COLOR, rect)
        if building["width"] > 40:
            shade_rect = pygame.Rect(rect.x + rect.width // 2, rect.y, rect.width // 2, rect.height)
            pygame.draw.rect(surface, INDUSTRIAL_BUILDING_SHADE, shade_rect)
        if building["height"] > 54:
            window_y = rect.y + 10
            while window_y < rect.bottom - 8:
                pygame.draw.line(surface, INDUSTRIAL_WINDOW_COLOR, (rect.x + 5, window_y), (rect.x + 8, window_y))
                window_y += 11

    for chimney in INDUSTRIAL_CHIMNEYS:
        rect = pygame.Rect(
            chimney["x"],
            HORIZON_Y - chimney["height"],
            chimney["width"],
            chimney["height"],
        )
        pygame.draw.rect(surface, INDUSTRIAL_BUILDING_SHADE, rect)
        smoke_time = elapsed * 0.7 + chimney["smoke_phase"]
        for index in range(3):
            puff_x = int(chimney["x"] + chimney["width"] // 2 + (index * 5) - 7)
            puff_y = int(rect.y - 7 - (index * 9) - ((smoke_time * 14 + index * 13) % 10))
            puff_radius = max(2, 5 - index)
            pygame.draw.circle(surface, SMOKE_COLOR, (puff_x, puff_y), puff_radius)


def draw_ground_scanline(y, scroll_phase):
    t = (y - HORIZON_Y) / (HEIGHT - HORIZON_Y)
    t = max(0.0, min(1.0, t))
    left_trans, left_outer, left_inner, right_inner, right_outer, right_trans = get_ground_regions(t)

    shoulder_color = blend_color(SHOULDER_SHADE_COLOR, SHOULDER_COLOR, t)
    road_color = blend_color(ROAD_SHADE_COLOR, ROAD_COLOR, t)
    background_color = blend_color(BACKGROUND_SHADE_COLOR, BACKGROUND_COLOR, t)

    line_y = y
    pygame.draw.line(screen, background_color, (0, line_y), (WIDTH, line_y))
    pygame.draw.line(screen, shoulder_color, (int(left_trans), line_y), (int(left_outer), line_y))
    pygame.draw.line(screen, road_color, (int(left_outer), line_y), (int(left_inner), line_y))
    pygame.draw.line(screen, background_color, (int(left_inner), line_y), (int(right_inner), line_y))
    pygame.draw.line(screen, road_color, (int(right_inner), line_y), (int(right_outer), line_y))
    pygame.draw.line(screen, shoulder_color, (int(right_outer), line_y), (int(right_trans), line_y))

    pygame.draw.line(screen, EDGE_LINE_COLOR, (int(left_outer), line_y), (int(left_outer), line_y))
    pygame.draw.line(screen, EDGE_LINE_COLOR, (int(left_inner), line_y), (int(left_inner), line_y))
    pygame.draw.line(screen, EDGE_LINE_COLOR, (int(right_inner), line_y), (int(right_inner), line_y))
    pygame.draw.line(screen, EDGE_LINE_COLOR, (int(right_outer), line_y), (int(right_outer), line_y))

    # Perspective-correct stripe spacing: dense near horizon, wider near camera.
    marker_track = LANE_MARK_TRACK_SCALE * math.log1p(LANE_MARK_TRACK_CURVE * t)
    marker_phase = (marker_track - (scroll_phase * LANE_MARK_SCROLL_MULTIPLIER)) % LANE_MARK_WORLD_SPACING
    marker_thickness = int(lerp(LANE_MARK_THICKNESS_HORIZON, LANE_MARK_THICKNESS_NEAR, t))
    if marker_phase < marker_thickness:
        marker_color = blend_color((184, 176, 168), LANE_MARK_COLOR, t)
        left_lane_left = int(left_outer) + 1
        left_lane_right = int(left_inner) - 1
        right_lane_left = int(right_inner) + 1
        right_lane_right = int(right_outer) - 1

        left_marker_x = int((left_lane_left + left_lane_right) * 0.5)
        right_marker_x = int((right_lane_left + right_lane_right) * 0.5)
        left_lane_width = max(1, left_lane_right - left_lane_left)
        right_lane_width = max(1, right_lane_right - right_lane_left)
        left_half_width = max(1, int(left_lane_width * LANE_MARK_WIDTH_FACTOR))
        right_half_width = max(1, int(right_lane_width * LANE_MARK_WIDTH_FACTOR))

        left_x1 = max(left_lane_left, left_marker_x - left_half_width)
        left_x2 = min(left_lane_right, left_marker_x + left_half_width)
        right_x1 = max(right_lane_left, right_marker_x - right_half_width)
        right_x2 = min(right_lane_right, right_marker_x + right_half_width)

        pygame.draw.line(
            screen,
            marker_color,
            (left_x1, line_y),
            (left_x2, line_y),
        )
        pygame.draw.line(
            screen,
            marker_color,
            (right_x1, line_y),
            (right_x2, line_y),
        )


def spawn_environment_object(env_objects):
    zone = random.choices(["left", "median", "right"], weights=[0.4, 0.2, 0.4], k=1)[0]
    env_objects.append(
        {
            "zone": zone,
            "kind": random.choice(ENV_OBJECT_KINDS),
            "y": float(HORIZON_Y + 8),
            "x_bias": random.uniform(0.18, 0.82),
        }
    )


def update_environment_objects(env_objects, speed, delta_time):
    for obj in env_objects:
        progress = (obj["y"] - HORIZON_Y) / (HEIGHT - HORIZON_Y)
        progress = max(0.0, min(1.0, progress))
        # Keep prop motion in sync with the same perspective model used for gameplay obstacles.
        obj_speed = speed * get_perspective_speed_multiplier(progress) * 0.92
        obj["y"] += obj_speed * delta_time


def draw_environment_objects(surface, env_objects):
    for obj in sorted(env_objects, key=lambda item: item["y"]):
        y = int(obj["y"])
        if y < HORIZON_Y or y > HEIGHT + 24:
            continue

        progress = (obj["y"] - HORIZON_Y) / (HEIGHT - HORIZON_Y)
        progress = max(0.0, min(1.0, progress))
        left_trans, left_outer, left_inner, right_inner, right_outer, right_trans = get_ground_regions(progress)

        side_margin = max(3, int(lerp(1, 8, progress)))
        if obj["zone"] == "left":
            # Keep side props in a band anchored to the road edge so they follow perspective diagonally.
            band_width = int(lerp(12, 82, progress))
            edge_anchor = int(left_trans) - side_margin
            x_min = max(side_margin, edge_anchor - band_width)
            x_max = max(side_margin + 1, edge_anchor - 1)
        elif obj["zone"] == "right":
            band_width = int(lerp(12, 82, progress))
            edge_anchor = int(right_trans) + side_margin
            x_min = min(WIDTH - side_margin - 1, edge_anchor + 1)
            x_max = min(WIDTH - side_margin, edge_anchor + band_width)
        else:
            x_min = int(left_inner) + side_margin
            x_max = int(right_inner) - side_margin

        if x_max <= x_min:
            continue

        center_x = lerp(x_min, x_max, obj["x_bias"])

        base_width = int(lerp(5, 26, progress))
        base_height = int(lerp(7, 36, progress))
        center = (int(center_x), y)

        if obj["kind"] == "crate":
            rect = pygame.Rect(center[0] - base_width // 2, y - base_height, base_width, base_height)
            pygame.draw.rect(surface, (74, 68, 62), rect)
            pygame.draw.rect(surface, (58, 52, 48), rect, 1)
        elif obj["kind"] == "barrel":
            rect = pygame.Rect(center[0] - base_width // 2, y - base_height, base_width, base_height)
            pygame.draw.ellipse(surface, (70, 64, 70), rect)
            pygame.draw.ellipse(surface, (56, 50, 56), rect, 1)
        elif obj["kind"] == "pipe":
            pipe_width = int(base_width * 1.4)
            pipe_height = max(3, int(base_height * 0.35))
            rect = pygame.Rect(center[0] - pipe_width // 2, y - pipe_height, pipe_width, pipe_height)
            pygame.draw.rect(surface, (76, 74, 72), rect)
            pygame.draw.rect(surface, (58, 56, 54), rect, 1)
        else:
            body_rect = pygame.Rect(center[0] - base_width // 3, y - base_height, max(3, base_width // 2), base_height)
            pygame.draw.rect(surface, (62, 60, 64), body_rect)
            top_rect = pygame.Rect(body_rect.x - 1, body_rect.y - 3, body_rect.width + 2, 3)
            pygame.draw.rect(surface, (92, 84, 76), top_rect)


def blit_centered_fitted_text(surface, font, text, color, center_y, max_width):
    text_surface = render_fitted_text(font, text, color, max_width)
    text_x = max(TEXT_SIDE_MARGIN, (WIDTH - text_surface.get_width()) // 2)
    surface.blit(text_surface, (text_x, center_y - text_surface.get_height() // 2))

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
                elapsed_time, spawn_timer, obstacles = reset_round()
                score = 0
                PLAYER_LANE = 0
                single_jump_timer = 0.0
                single_jump_cooldown_timer = 0.0
                single_jump_start_lane = 0
                single_jump_target_lane = 0
                left_coop_jump_timer = 0.0
                right_coop_jump_timer = 0.0
                env_objects = []
                env_spawn_timer = 0.0
                next_env_spawn_interval = random.uniform(ENV_OBJECT_INTERVAL_MIN, ENV_OBJECT_INTERVAL_MAX)
                single_next_spawn_interval = get_current_spawn_interval(INITIAL_OBSTACLE_SPEED)
                single_last_spawn_lane = None
                single_lane_streak = 0
                coop_lane_cooldowns = [0.0 for _ in LANES]
                coop_lane_spawn_timers, coop_lane_next_spawn_intervals = reset_coop_spawn_state(
                    INITIAL_OBSTACLE_SPEED * COOP_SPEED_MULTIPLIER
                )
                game_state = "running"

            elif game_state == "running" and game_mode == "single" and event.key == pygame.K_SPACE:
                if single_jump_timer <= 0.0 and single_jump_cooldown_timer <= 0.0:
                    single_jump_start_lane = PLAYER_LANE
                    single_jump_target_lane = 1 - PLAYER_LANE
                    single_jump_timer = SINGLE_JUMP_DURATION

            elif game_state == "running" and game_mode == "coop" and event.key == pygame.K_a:
                if left_coop_jump_timer <= 0.0:
                    left_coop_jump_timer = COOP_JUMP_DURATION

            elif game_state == "running" and game_mode == "coop" and event.key == pygame.K_l:
                if right_coop_jump_timer <= 0.0:
                    right_coop_jump_timer = COOP_JUMP_DURATION

            elif game_state == "game_over" and event.key in (pygame.K_r,):
                elapsed_time, spawn_timer, obstacles = reset_round()
                score = 0
                PLAYER_LANE = 0
                current_obstacle_speed = INITIAL_OBSTACLE_SPEED
                single_jump_timer = 0.0
                single_jump_cooldown_timer = 0.0
                single_jump_start_lane = 0
                single_jump_target_lane = 0
                left_coop_jump_timer = 0.0
                right_coop_jump_timer = 0.0
                env_objects = []
                env_spawn_timer = 0.0
                next_env_spawn_interval = random.uniform(ENV_OBJECT_INTERVAL_MIN, ENV_OBJECT_INTERVAL_MAX)
                single_next_spawn_interval = get_current_spawn_interval(INITIAL_OBSTACLE_SPEED)
                single_last_spawn_lane = None
                single_lane_streak = 0
                coop_lane_cooldowns = [0.0 for _ in LANES]
                coop_lane_spawn_timers, coop_lane_next_spawn_intervals = reset_coop_spawn_state(
                    INITIAL_OBSTACLE_SPEED * COOP_SPEED_MULTIPLIER
                )
                game_state = "start"

    if game_state == "running":
        elapsed_time += delta_time
        spawn_timer += delta_time
        env_spawn_timer += delta_time
        if game_mode == "single":
            if single_jump_timer > 0.0:
                single_jump_timer = max(0.0, single_jump_timer - delta_time)
                if single_jump_timer == 0.0:
                    PLAYER_LANE = single_jump_target_lane
                    single_jump_cooldown_timer = SINGLE_JUMP_COOLDOWN
            elif single_jump_cooldown_timer > 0.0:
                single_jump_cooldown_timer = max(0.0, single_jump_cooldown_timer - delta_time)
        else:
            coop_lane_cooldowns = [max(0.0, cooldown - delta_time) for cooldown in coop_lane_cooldowns]

        base_speed = INITIAL_OBSTACLE_SPEED + (elapsed_time * OBSTACLE_SPEED_INCREASE)
        if game_mode == "coop":
            current_obstacle_speed = base_speed * COOP_SPEED_MULTIPLIER
            current_spawn_interval = 0.0
        else:
            current_obstacle_speed = base_speed
            current_spawn_interval = single_next_spawn_interval

        scroll_offset += current_obstacle_speed * delta_time

        if game_mode == "single" and spawn_timer >= current_spawn_interval:
            available_slots = MAX_ACTIVE_OBSTACLES - len(obstacles)
            if available_slots > 0:
                if game_mode == "single":
                    candidate_lanes = [lane for lane in range(len(LANES)) if can_spawn_in_lane(obstacles, lane)]
                    random.shuffle(candidate_lanes)

                    if single_last_spawn_lane is not None and single_lane_streak >= SINGLE_MAX_SAME_LANE_STREAK:
                        non_streak_lanes = [lane for lane in candidate_lanes if lane != single_last_spawn_lane]
                        if non_streak_lanes:
                            candidate_lanes = non_streak_lanes

                    safe_lanes = [lane for lane in candidate_lanes if not would_block_both_lanes_near_spawn(obstacles, lane)]
                    lane_pool = safe_lanes if safe_lanes else candidate_lanes

                    if lane_pool:
                        if single_last_spawn_lane is not None:
                            alternate_lanes = [lane for lane in lane_pool if lane != single_last_spawn_lane]
                            if alternate_lanes and random.random() < 0.62:
                                chosen_lane = random.choice(alternate_lanes)
                            else:
                                chosen_lane = random.choice(lane_pool)
                        else:
                            chosen_lane = random.choice(lane_pool)

                        spawn_obstacle(obstacles, chosen_lane, random.choice(obstacle_images))
                        if chosen_lane == single_last_spawn_lane:
                            single_lane_streak += 1
                        else:
                            single_last_spawn_lane = chosen_lane
                            single_lane_streak = 1
            spawn_timer -= current_spawn_interval
            single_next_spawn_interval = get_next_single_spawn_interval(current_obstacle_speed)
            current_spawn_interval = single_next_spawn_interval

        if game_mode == "coop":
            for lane in range(len(LANES)):
                coop_lane_spawn_timers[lane] += delta_time
                interval = coop_lane_next_spawn_intervals[lane]
                if coop_lane_spawn_timers[lane] < interval:
                    continue

                available_slots = MAX_ACTIVE_OBSTACLES - len(obstacles)
                can_spawn_now = (
                    available_slots > 0
                    and coop_lane_cooldowns[lane] <= 0.0
                    and can_spawn_in_lane(obstacles, lane)
                )

                if can_spawn_now and random.random() < get_coop_lane_spawn_chance(current_obstacle_speed):
                    spawn_obstacle(obstacles, lane, random.choice(obstacle_images))
                    coop_lane_cooldowns[lane] = get_next_coop_lane_cooldown(current_obstacle_speed)

                coop_lane_spawn_timers[lane] -= interval
                coop_lane_next_spawn_intervals[lane] = get_next_coop_spawn_interval(current_obstacle_speed)

        depth_range = max(1.0, HEIGHT - HORIZON_Y)
        for obstacle in obstacles:
            obstacle["prev_y"] = obstacle["y"]
            progress = (obstacle["y"] - HORIZON_Y) / (HEIGHT - HORIZON_Y)
            progress = max(0.0, min(1.0, progress))
            # Use the same perspective curve derivative as lane markers for depth-consistent motion.
            marker_track_derivative = (
                (LANE_MARK_TRACK_SCALE * LANE_MARK_TRACK_CURVE) / (1.0 + (LANE_MARK_TRACK_CURVE * progress))
            ) / depth_range
            line_screen_multiplier = LANE_MARK_SCROLL_MULTIPLIER / max(1e-6, marker_track_derivative)
            obstacle["y"] += current_obstacle_speed * line_screen_multiplier * OBSTACLE_LINE_SYNC_FACTOR * delta_time

        while env_spawn_timer >= next_env_spawn_interval:
            spawn_environment_object(env_objects)
            env_spawn_timer -= next_env_spawn_interval
            next_env_spawn_interval = random.uniform(ENV_OBJECT_INTERVAL_MIN, ENV_OBJECT_INTERVAL_MAX)

        update_environment_objects(env_objects, current_obstacle_speed, delta_time)
        env_objects = [obj for obj in env_objects if obj["y"] < HEIGHT + 36]

        obstacles = [obstacle for obstacle in obstacles if obstacle["y"] < HEIGHT + 80]
        if game_mode == "single":
            obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]
            obstacle_hitboxes = [get_obstacle_hitbox(obstacle) for obstacle in obstacles]

            if single_jump_timer > 0.0:
                jump_progress = 1.0 - (single_jump_timer / SINGLE_JUMP_DURATION)
                lane_progress = single_jump_start_lane + ((single_jump_target_lane - single_jump_start_lane) * jump_progress)
                jump_height = int(SINGLE_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))
                player_rect = get_singleplayer_jump_rect(lane_progress, jump_height)
            else:
                player_rect = get_player_rect(PLAYER_LANE)

            player_ground_hitbox = get_player_ground_hitbox(player_rect)

            for obstacle_hitbox in obstacle_hitboxes:
                if obstacle_hitbox.colliderect(player_ground_hitbox):
                    final_score = score
                    game_state = "game_over"
                    nonce = str(uuid.uuid4())
                    qr_surface = generate_score_qr(final_score, nonce)
                    break
        else:
            if left_coop_jump_timer > 0.0:
                left_coop_jump_timer = max(0.0, left_coop_jump_timer - delta_time)
            if right_coop_jump_timer > 0.0:
                right_coop_jump_timer = max(0.0, right_coop_jump_timer - delta_time)

            left_jump_height = 0
            if left_coop_jump_timer > 0.0:
                jump_progress = 1.0 - (left_coop_jump_timer / COOP_JUMP_DURATION)
                left_jump_height = int(COOP_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))

            right_jump_height = 0
            if right_coop_jump_timer > 0.0:
                jump_progress = 1.0 - (right_coop_jump_timer / COOP_JUMP_DURATION)
                right_jump_height = int(COOP_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))

            obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]
            obstacle_hitboxes = [get_coop_obstacle_bottom_hitbox(obstacle) for obstacle in obstacles]

            left_player_rect = get_lane_player_rect(0, left_jump_height)
            right_player_rect = get_lane_player_rect(1, right_jump_height)
            left_player_ground_hitbox = get_coop_player_foot_hitbox(left_player_rect)
            right_player_ground_hitbox = get_coop_player_foot_hitbox(right_player_rect)

            for obstacle, obstacle_hitbox in zip(obstacles, obstacle_hitboxes):
                prev_obstacle = dict(obstacle)
                prev_obstacle["y"] = obstacle.get("prev_y", obstacle["y"])
                prev_hitbox = get_coop_obstacle_bottom_hitbox(prev_obstacle)
                swept_hitbox = obstacle_hitbox.union(prev_hitbox)

                # Ignore far-away obstacles; co-op hits should only happen near player ground contact.
                if swept_hitbox.bottom < (PLAYER_Y - COOP_COLLISION_ZONE_HEIGHT):
                    continue

                collided_left = obstacle["lane"] == 0 and swept_hitbox.colliderect(left_player_ground_hitbox)
                collided_right = obstacle["lane"] == 1 and swept_hitbox.colliderect(right_player_ground_hitbox)
                if collided_left or collided_right:
                    final_score = score
                    game_state = "game_over"
                    nonce = str(uuid.uuid4())
                    qr_surface = generate_score_qr(final_score, nonce)
                    break

        base_score = calculate_score(elapsed_time, current_obstacle_speed)
        score = base_score * 1.5 if game_mode == "coop" else base_score

    elif game_state == "start":
        current_obstacle_speed = INITIAL_OBSTACLE_SPEED
        single_jump_timer = 0.0
        single_jump_cooldown_timer = 0.0
        left_coop_jump_timer = 0.0
        right_coop_jump_timer = 0.0
        env_spawn_timer = 0.0
        env_objects = []
        single_next_spawn_interval = get_current_spawn_interval(INITIAL_OBSTACLE_SPEED)
        single_last_spawn_lane = None
        single_lane_streak = 0
        coop_lane_cooldowns = [0.0 for _ in LANES]
        coop_lane_spawn_timers, coop_lane_next_spawn_intervals = reset_coop_spawn_state(
            INITIAL_OBSTACLE_SPEED * COOP_SPEED_MULTIPLIER
        )

    player_rect = get_player_rect(PLAYER_LANE)
    left_player_rect = None
    right_player_rect = None
    if game_mode == "single" and single_jump_timer > 0.0:
        jump_progress = 1.0 - (single_jump_timer / SINGLE_JUMP_DURATION)
        lane_progress = single_jump_start_lane + ((single_jump_target_lane - single_jump_start_lane) * jump_progress)
        jump_height = int(SINGLE_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))
        player_rect = get_singleplayer_jump_rect(lane_progress, jump_height)
    elif game_mode == "coop":
        left_jump_height = 0
        if game_state == "running" and left_coop_jump_timer > 0.0:
            jump_progress = 1.0 - (left_coop_jump_timer / COOP_JUMP_DURATION)
            left_jump_height = int(COOP_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))

        right_jump_height = 0
        if game_state == "running" and right_coop_jump_timer > 0.0:
            jump_progress = 1.0 - (right_coop_jump_timer / COOP_JUMP_DURATION)
            right_jump_height = int(COOP_JUMP_HEIGHT * (4 * jump_progress * (1 - jump_progress)))

        left_player_rect = get_lane_player_rect(0, left_jump_height)
        right_player_rect = get_lane_player_rect(1, right_jump_height)

    hud_max_width = WIDTH - (TEXT_SIDE_MARGIN * 2)
    timer_text = render_fitted_text(hud_font, f"Time: {elapsed_time:05.2f}s", (255, 255, 255), hud_max_width)
    score_text = render_fitted_text(hud_font, f"Score: {score}", (255, 255, 255), hud_max_width)
    speed_text = render_fitted_text(hud_font, f"Obstacle Speed: {current_obstacle_speed:.0f}", (255, 255, 255), hud_max_width)

    screen.fill((0, 0, 0))
    draw_industrial_background(screen, elapsed_time)


    scroll_phase = scroll_offset
    for y in range(HORIZON_Y, HEIGHT):
        draw_ground_scanline(y, scroll_phase)

    draw_environment_objects(screen, env_objects)

    if not obstacle_rects:
        if game_mode == "single":
            obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]
        else:
            obstacle_rects = [get_obstacle_rect(obstacle) for obstacle in obstacles]

    for obstacle in obstacles:
        obstacle_rect = get_obstacle_rect(obstacle)
        size = obstacle_rect.height
        scaled = pygame.transform.scale(obstacle["image"], (size, size))
        screen.blit(scaled, (obstacle_rect.centerx - size // 2, obstacle_rect.top))
    # player character
    if game_mode == "single":
        size = player_rect.height
        scaled = pygame.transform.scale(player_sprite, (size, size))
        blit_x = player_rect.centerx - size // 2
        screen.blit(scaled, (blit_x, player_rect.top))
    else:
        coop_player_draw_data = (
            (left_player_rect, coop_left_player_sprite),
            (right_player_rect, coop_right_player_sprite),
        )
        for rect, sprite in coop_player_draw_data:
            size = rect.height
            scaled = pygame.transform.scale(sprite, (size, size))
            screen.blit(scaled, (rect.centerx - size // 2, rect.top))

    if game_state == "running":
        hud_x = TEXT_SIDE_MARGIN
        hud_y = 20
        for text_surface in (timer_text, score_text, speed_text):
            screen.blit(text_surface, (hud_x, hud_y))
            hud_y += text_surface.get_height() + 8

    if game_state == "start":
        mode_text = f"Mode: {'Single Player' if game_mode == 'single' else 'Co-op'} (press 1 or 2)"
        overlay_max_width = WIDTH - (TEXT_SIDE_MARGIN * 2)
        blit_centered_fitted_text(screen, title_font, "The Last Checkpoint", (255, 255, 255), HEIGHT // 2 - 90, overlay_max_width)
        blit_centered_fitted_text(screen, message_font, "Press SPACE or ENTER to start", (220, 220, 220), HEIGHT // 2 - 25, overlay_max_width)
        blit_centered_fitted_text(screen, message_font, mode_text, (220, 220, 220), HEIGHT // 2 + 30, overlay_max_width)

    elif game_state == "game_over":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        overlay_max_width = WIDTH - (TEXT_SIDE_MARGIN * 2)
        blit_centered_fitted_text(screen, title_font, "Game Over", (255, 110, 110), HEIGHT // 2 - 110, overlay_max_width)
        blit_centered_fitted_text(screen, message_font, f"Final Score: {final_score}", (255, 255, 255), HEIGHT // 2 - 35, overlay_max_width)
        blit_centered_fitted_text(screen, message_font, "Press R or ENTER to return", (220, 220, 220), HEIGHT // 2 + 20, overlay_max_width)
        qr_rect = qr_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 200))
        screen.blit(qr_surface, qr_rect)

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
                "SPACE: Jump lanes",
                "Close window: Quit",
            ]
        else:
            controls_lines = [
                "Controls:",
                "A: Left lane jump",
                "L: Right lane jump",
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
    
pygame.quit()
