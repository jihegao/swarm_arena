from __future__ import annotations
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from config import (
    DEFAULT_VISION_RADIUS,
    DEFAULT_ENERGY,
    DEFAULT_SPEED,
    DEFAULT_SIZE,
    CREATURE_COLORS,
    DEFAULT_CREATURE_COLOR,
    CREATURE_PROFILES,
    CREATURE_LIMITS,
    CREATURE_BUDGET,
)


@dataclass
class FoodSpot:
    x: float
    y: float
    amount: float
    size: float


@dataclass
class CreatureSpot:
    x: float
    y: float
    creature_type: str
    creature_id: int
    size: float
    energy_pct: float


@dataclass
class Perception:
    nearby_food: list[FoodSpot]
    nearby_creatures: list[CreatureSpot]
    self_energy: float
    self_max_energy: float
    self_x: float
    self_y: float
    self_angle: float
    self_size: float
    world_width: int
    world_height: int


@dataclass
class Action:
    target_angle: float
    target_speed: float
    attack_target_id: int | None = None
    reproduce: bool = False


class Creature(ABC):
    __slots__ = (
        'id', 'x', 'y', 'angle', 'speed', 'max_speed',
        'energy', 'max_energy',
        'vision_radius', 'creature_type', 'color',
        'cooldown', 'reproduce_cooldown', 'name',
    )

    _next_id = 0

    def __init__(self, x: float, y: float, creature_type: str,
                 color: tuple[int, int, int] | None = None):
        self.id = Creature._next_id
        Creature._next_id += 1
        self.x = x
        self.y = y
        self.angle = math.pi * 2 * (self.id / 100)
        self.speed = 0.0
        self.max_speed = DEFAULT_SPEED
        self.energy = DEFAULT_ENERGY
        self.max_energy = DEFAULT_ENERGY
        self.vision_radius = DEFAULT_VISION_RADIUS
        self.creature_type = creature_type
        self.color = color if color is not None else CREATURE_COLORS.get(
            creature_type, DEFAULT_CREATURE_COLOR
        )
        if self.color[0] >= 230 and self.color[1] >= 230 and self.color[2] >= 230:
            self.color = DEFAULT_CREATURE_COLOR
        self.cooldown = 0
        self.reproduce_cooldown = 0
        self.name = f"{creature_type}#{self.id}"

        profile = CREATURE_PROFILES.get(creature_type)
        if profile:
            self.max_speed = profile["max_speed"]
            self.max_energy = profile["max_energy"]
            self.energy = profile["max_energy"]
            self.vision_radius = profile["vision_radius"]

    @abstractmethod
    def decide(self, perception: Perception) -> Action:
        ...

    def eat_food(self, amount: float):
        self.energy += amount

    @property
    def size(self) -> float:
        return DEFAULT_SIZE * math.sqrt(self.energy / DEFAULT_ENERGY)

    @property
    def is_alive(self) -> bool:
        return self.energy > 0

    def distance_to(self, px: float, py: float) -> float:
        return math.hypot(self.x - px, self.y - py)

    def clamp(self):
        for attr, (lo, hi) in CREATURE_LIMITS.items():
            val = getattr(self, attr)
            setattr(self, attr, max(lo, min(hi, val)))

        cost = 0.0
        for attr, (lo, hi) in CREATURE_LIMITS.items():
            val = getattr(self, attr)
            cost += (val - lo) / (hi - lo)

        if cost > CREATURE_BUDGET:
            scale = CREATURE_BUDGET / cost
            for attr, (lo, hi) in CREATURE_LIMITS.items():
                val = getattr(self, attr)
                setattr(self, attr, lo + (val - lo) * scale)

        self.energy = max(0.0, min(self.energy, self.max_energy))

    def budget_cost(self) -> float:
        cost = 0.0
        for attr, (lo, hi) in CREATURE_LIMITS.items():
            val = getattr(self, attr)
            cost += (val - lo) / (hi - lo)
        return cost
