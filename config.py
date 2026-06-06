import math

FULLSCREEN = True
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SIDEBAR_WIDTH = 260
FPS = 60

CREATURE_COUNT = 200
FOOD_SPAWN_INTERVAL = 40
FOOD_SPAWN_COUNT = 3
MAX_FOOD_ON_MAP = 300

DEFAULT_VISION_RADIUS = 20.0
DEFAULT_ENERGY = 100.0
DEFAULT_SPEED = 1.0
DEFAULT_SIZE = 6

ENERGY_DECAY_RATE = 0.1
MOVE_ENERGY_COST = 0.08
FOOD_EAT_DISTANCE = 3.0
EAT_OVERLAP_RATIO = 0.6
MAX_EAT_SEARCH_RADIUS = 80.0

REPRODUCE_ENERGY_RATIO = 2.0
REPRODUCE_COST_RATIO = 0.5
REPRODUCE_COOLDOWN = 120
REPRODUCE_SPAWN_OFFSET = 20.0
MAX_CREATURE_COUNT = 600
GAME_OVER_TICK = 5000

FOOD_AMOUNT_MIN = 8.0
FOOD_AMOUNT_MAX = 100.0
FOOD_COLOR = (255, 255, 255)

BG_COLOR = (10, 10, 10)
HUD_TEXT_COLOR = (200, 200, 200)
GAME_OVER_COLOR = (255, 255, 255)

CREATURE_COLORS = {
    "Hunter": (220, 50, 50),
    "Grazer": (50, 180, 50),
    "PackHunter": (50, 50, 220),
    "Scavenger": (220, 220, 50),
}
DEFAULT_CREATURE_COLOR = (180, 180, 180)

CREATURE_LIMITS = {
    "max_speed":      (0.5,  4.0),
    "max_energy":     (30.0, 200.0),
    "vision_radius":  (50.0, 300.0),
}

CREATURE_BUDGET = 1.5

CREATURE_PROFILES = {
    "Hunter": {
        "max_speed": 2.5,
        "max_energy": 80.0,
        "vision_radius": 200.0,
    },
    "Grazer": {
        "max_speed": 1.5,
        "max_energy": 100.0,
        "vision_radius": 150.0,
    },
    "PackHunter": {
        "max_speed": 2.2,
        "max_energy": 80.0,
        "vision_radius": 150.0,
    },
    "Scavenger": {
        "max_speed": 3.5,
        "max_energy": 60.0,
        "vision_radius": 160.0,
    },
}

SPATIAL_GRID_CELL_SIZE = 130
