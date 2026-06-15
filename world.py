from __future__ import annotations
import math
import random
from creature import Creature, Perception, FoodSpot, CreatureSpot, Action
from combat import try_eat
from food import Food
from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    CREATURE_COUNT,
    FOOD_SPAWN_INTERVAL,
    FOOD_SPAWN_COUNT,
    MAX_FOOD_ON_MAP,
    ENERGY_DECAY_RATE,
    MOVE_ENERGY_COST,
    FOOD_EAT_DISTANCE,
    SPATIAL_GRID_CELL_SIZE,
    MAX_EAT_SEARCH_RADIUS,
    DEFAULT_SIZE,
    DEFAULT_ENERGY,
    REPRODUCE_ENERGY_RATIO,
    REPRODUCE_COST_RATIO,
    REPRODUCE_COOLDOWN,
    REPRODUCE_SPAWN_OFFSET,
    MAX_CREATURE_COUNT,
    GAME_OVER_TICK,
)


class SpatialGrid:
    def __init__(self, width: int, height: int, cell_size: float):
        self.cell_size = cell_size
        self.cols = int(math.ceil(width / cell_size))
        self.rows = int(math.ceil(height / cell_size))
        self.cells: dict[tuple[int, int], list] = {}

    def clear(self):
        self.cells.clear()

    def _cell_key(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, entity):
        key = self._cell_key(entity.x, entity.y)
        if key not in self.cells:
            self.cells[key] = []
        self.cells[key].append(entity)

    def query_radius(self, x: float, y: float, radius: float) -> list:
        results = []
        min_cx = int((x - radius) // self.cell_size)
        max_cx = int((x + radius) // self.cell_size)
        min_cy = int((y - radius) // self.cell_size)
        max_cy = int((y + radius) // self.cell_size)
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                cell = self.cells.get((cx, cy))
                if cell:
                    results.extend(cell)
        return results


class World:
    def __init__(self, width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT):
        self.creatures: list[Creature] = []
        self.foods: list[Food] = []
        self.tick: int = 0
        self.game_over: bool = False
        self.winner: Creature | None = None
        self.width = width
        self.height = height
        self._creature_grid = SpatialGrid(width, height, SPATIAL_GRID_CELL_SIZE)
        self._food_grid = SpatialGrid(width, height, SPATIAL_GRID_CELL_SIZE)
        self._class_map: dict[str, type[Creature]] = {}
        self._decision_error_counts: dict[str, int] = {}

    def spawn_creatures(self, creature_classes: list[type[Creature]]):
        if not creature_classes:
            return
        for cls in creature_classes:
            self._class_map[cls.__name__] = cls
        per_type = max(1, CREATURE_COUNT // len(creature_classes))
        margin = 30
        for cls in creature_classes:
            for _ in range(per_type):
                x = random.uniform(margin, self.width - margin)
                y = random.uniform(margin, self.height - margin)
                c = cls(x, y)
                c.clamp()
                self._class_map[c.creature_type] = cls
                self.creatures.append(c)
        random.shuffle(self.creatures)

    def update(self):
        if self.game_over:
            return

        self.tick += 1

        self._spawn_food()
        self._rebuild_grids()

        alive = [c for c in self.creatures if c.is_alive]

        perceptions = []
        actions = []
        for c in alive:
            p = self._build_perception(c)
            perceptions.append(p)
            actions.append(self._safe_decide(c, p))

        for c, action in zip(alive, actions):
            self._resolve_movement(c, action)

        self._resolve_reproduction(alive, actions)

        self._rebuild_grids()
        self._resolve_eating(alive)
        self._check_food_collision()

        for c in alive:
            decay = ENERGY_DECAY_RATE
            decay += MOVE_ENERGY_COST * abs(c.speed) / c.max_speed if c.max_speed > 0 else 0
            size_ratio = c.size / DEFAULT_SIZE
            decay *= size_ratio
            c.energy -= decay
            if c.cooldown > 0:
                c.cooldown -= 1
            if c.reproduce_cooldown > 0:
                c.reproduce_cooldown -= 1

        self.creatures = [c for c in self.creatures if c.is_alive]
        self.foods = [f for f in self.foods if not f.depleted]

        self._check_win_condition()

    def _spawn_food(self):
        if self.tick % FOOD_SPAWN_INTERVAL != 0:
            return
        if len(self.foods) >= MAX_FOOD_ON_MAP:
            return
        margin = 20
        for _ in range(FOOD_SPAWN_COUNT):
            x = random.uniform(margin, self.width - margin)
            y = random.uniform(margin, self.height - margin)
            self.foods.append(Food(x, y))

    def _rebuild_grids(self):
        self._creature_grid.clear()
        self._food_grid.clear()
        for c in self.creatures:
            if c.is_alive:
                self._creature_grid.insert(c)
        for f in self.foods:
            if not f.depleted:
                self._food_grid.insert(f)

    def _build_perception(self, creature: Creature) -> Perception:
        nearby_creatures_data = self._creature_grid.query_radius(
            creature.x, creature.y, creature.vision_radius
        )
        nearby_food_data = self._food_grid.query_radius(
            creature.x, creature.y, creature.vision_radius
        )

        vr2 = creature.vision_radius * creature.vision_radius
        food_spots = []
        for f in nearby_food_data:
            if f.depleted:
                continue
            dx = f.x - creature.x
            dy = f.y - creature.y
            if dx * dx + dy * dy <= vr2:
                food_spots.append(FoodSpot(f.x, f.y, f.amount, f.size))

        creature_spots = []
        for other in nearby_creatures_data:
            if other.id == creature.id or not other.is_alive:
                continue
            dx = other.x - creature.x
            dy = other.y - creature.y
            if dx * dx + dy * dy <= vr2:
                creature_spots.append(CreatureSpot(
                    x=other.x,
                    y=other.y,
                    creature_type=other.creature_type,
                    creature_id=other.id,
                    size=other.size,
                    energy_pct=other.energy / other.max_energy if other.max_energy > 0 else 0,
                ))

        return Perception(
            nearby_food=food_spots,
            nearby_creatures=creature_spots,
            self_energy=creature.energy,
            self_max_energy=creature.max_energy,
            self_x=creature.x,
            self_y=creature.y,
            self_angle=creature.angle,
            self_size=creature.size,
            world_width=self.width,
            world_height=self.height,
        )

    def _safe_decide(self, creature: Creature, perception: Perception) -> Action:
        try:
            action = creature.decide(perception)
        except Exception as exc:
            count = self._decision_error_counts.get(creature.creature_type, 0) + 1
            self._decision_error_counts[creature.creature_type] = count
            if count <= 3 or count in (10, 50, 100):
                print(
                    f"Warning: {creature.name} decide() failed "
                    f"({count} error(s) for {creature.creature_type}): {exc}",
                    flush=True,
                )
            return Action(creature.angle, 0.0)
        return self._sanitize_action(creature, action)

    def _sanitize_action(self, creature: Creature, action) -> Action:
        if not isinstance(action, Action):
            print(
                f"Warning: {creature.name} returned invalid action {type(action).__name__}; stopping.",
                flush=True,
            )
            return Action(creature.angle, 0.0)

        target_angle = action.target_angle
        if not isinstance(target_angle, (int, float)) or not math.isfinite(target_angle):
            target_angle = creature.angle

        target_speed = action.target_speed
        if not isinstance(target_speed, (int, float)) or not math.isfinite(target_speed):
            target_speed = 0.0
        target_speed = max(0.0, min(float(target_speed), creature.max_speed))

        attack_target_id = action.attack_target_id
        if attack_target_id is not None and not isinstance(attack_target_id, int):
            attack_target_id = None

        return Action(
            float(target_angle),
            target_speed,
            attack_target_id=attack_target_id,
            reproduce=bool(action.reproduce),
        )

    def _resolve_movement(self, creature: Creature, action: Action):
        action = self._sanitize_action(creature, action)
        desired_speed = action.target_speed
        creature.angle = action.target_angle % (2 * math.pi)
        creature.speed = desired_speed

        creature.x += math.cos(creature.angle) * creature.speed
        creature.y += math.sin(creature.angle) * creature.speed

        margin = creature.size
        if creature.x < margin:
            creature.x = margin
            creature.angle = math.pi - creature.angle
        elif creature.x > self.width - margin:
            creature.x = self.width - margin
            creature.angle = math.pi - creature.angle
        if creature.y < margin:
            creature.y = margin
            creature.angle = -creature.angle
        elif creature.y > self.height - margin:
            creature.y = self.height - margin
            creature.angle = -creature.angle
        creature.angle %= 2 * math.pi

    def _resolve_reproduction(self, alive: list[Creature], actions: list[Action]):
        babies: list[Creature] = []
        for c, action in zip(alive, actions):
            if not action.reproduce:
                continue
            if not c.is_alive:
                continue
            if c.reproduce_cooldown > 0:
                continue
            threshold = c.max_energy * REPRODUCE_ENERGY_RATIO
            if c.energy < threshold:
                continue
            if len(self.creatures) + len(babies) >= MAX_CREATURE_COUNT:
                break

            cost = c.max_energy * REPRODUCE_COST_RATIO
            c.energy -= cost
            c.reproduce_cooldown = REPRODUCE_COOLDOWN

            cls = self._class_map.get(c.creature_type)
            if cls is None:
                continue

            offset_angle = random.uniform(0, 2 * math.pi)
            bx = c.x + math.cos(offset_angle) * REPRODUCE_SPAWN_OFFSET
            by = c.y + math.sin(offset_angle) * REPRODUCE_SPAWN_OFFSET
            bx = max(5, min(self.width - 5, bx))
            by = max(5, min(self.height - 5, by))

            baby = cls(bx, by)
            baby.energy = cost
            baby.clamp()
            babies.append(baby)

        self.creatures.extend(babies)

    def _resolve_eating(self, alive: list[Creature]):
        for c in alive:
            if not c.is_alive:
                continue
            eat_range = min(c.size * 3, MAX_EAT_SEARCH_RADIUS)
            nearby = self._creature_grid.query_radius(c.x, c.y, eat_range)
            for other in nearby:
                if other.id == c.id or not other.is_alive:
                    continue
                if try_eat(c, other):
                    pass

    def _check_food_collision(self):
        for c in self.creatures:
            if not c.is_alive:
                continue
            nearby = self._food_grid.query_radius(c.x, c.y, c.size + FOOD_EAT_DISTANCE)
            for f in nearby:
                if f.depleted:
                    continue
                if math.hypot(c.x - f.x, c.y - f.y) < c.size + FOOD_EAT_DISTANCE:
                    c.eat_food(f.amount)
                    f.amount = 0

    def _check_win_condition(self):
        alive = [c for c in self.creatures if c.is_alive]
        if len(alive) == 0:
            self.game_over = True
            self.winner = None
            return

        alive_types = set(c.creature_type for c in alive)
        if len(alive_types) <= 1:
            self.game_over = True
            best = max(alive, key=lambda c: c.energy)
            self.winner = best
            return

        if self.tick >= GAME_OVER_TICK:
            self.game_over = True
            type_counts: dict[str, list[Creature]] = {}
            for c in alive:
                type_counts.setdefault(c.creature_type, []).append(c)
            if type_counts:
                winning_type = max(type_counts, key=lambda t: len(type_counts[t]))
                best = max(type_counts[winning_type], key=lambda c: c.energy)
                self.winner = best

    def alive_count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self.creatures:
            if c.is_alive:
                counts[c.creature_type] = counts.get(c.creature_type, 0) + 1
        return counts

    @property
    def alive_count(self) -> int:
        return sum(1 for c in self.creatures if c.is_alive)

    def population_ranking(self) -> list[tuple[str, int]]:
        counts = self.alive_count_by_type()
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)

    def top_creatures(self, limit: int = 10) -> list[tuple[str, str, float, float, tuple[int, int, int]]]:
        alive = sorted(
            [c for c in self.creatures if c.is_alive],
            key=lambda c: c.energy,
            reverse=True,
        )
        result = []
        for c in alive[:limit]:
            result.append((c.name, c.creature_type, c.energy, c.size, c.color))
        return result
