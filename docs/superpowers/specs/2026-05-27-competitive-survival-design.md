# Competitive Survival Framework - Design Spec

## Overview

A pygame-based 2D competitive survival simulation. Multiple creature types coexist in a world with randomly spawning food. Creatures eat food, hunt each other, perceive their surroundings, and compete until only one survives (battle royale). The framework uses an ECS-lite architecture: a unified `Creature` base class with pluggable AI via a single `decide()` method. Custom creature classes live in `creatures/` and are auto-loaded at startup.

## Core Design Decisions

| Decision | Choice |
|----------|--------|
| Architecture | ECS-lite: base class + pluggable `decide()` |
| Combat | Collision + attribute comparison (attack vs defense, size matters) |
| Perception | Circular vision range per creature |
| Movement | Angle + speed (continuous), consistent with existing ant projects |
| Survival | Energy system: moving/combat costs energy, food restores energy, 0 energy = death; body size scales with energy |
| Evolution | Battle royale: all creatures spawn at once, last one standing wins; score from kills and food only |
| Scale | 50-200 creatures, 500+ food, 1200x800 window |
| Extensibility | Built-in types + user-customizable via `creatures/` directory |

## File Structure

```
ant_swarm/
├── main.py                  # Entry point: pygame loop, start simulation
├── config.py                # All tunable parameters (world size, food rate, etc.)
├── world.py                 # World: manages entities, physics, food spawning
├── creature.py              # Creature base class + Perception + Action dataclasses
├── combat.py                # Combat resolution logic (centralized)
├── renderer.py              # All pygame drawing
├── food.py                  # Food entity
├── creature_loader.py       # Auto-load creature classes from creatures/ directory
├── creatures/
│   ├── __init__.py          # Exports all creature classes
│   ├── hunter.py            # Built-in: aggressive pursuer
│   ├── grazer.py            # Built-in: food-focused, avoids conflict
│   ├── pack_hunter.py       # Built-in: weak alone, groups up to hunt
│   └── scavenger.py         # Built-in: fast, steals food, runs from fights
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-27-competitive-survival-design.md
```

## Module Design

### config.py

All constants in one place. Key parameters:

```python
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

CREATURE_COUNT = 100  # total, divided among types
FOOD_SPAWN_INTERVAL = 30  # frames between food spawns
FOOD_SPAWN_COUNT = 3  # food items per spawn
MAX_FOOD_ON_MAP = 500

DEFAULT_VISION_RADIUS = 120
DEFAULT_ENERGY = 100.0
DEFAULT_SPEED = 2.0
DEFAULT_ATTACK = 10.0
DEFAULT_DEFENSE = 5.0
DEFAULT_SIZE = 6
ENERGY_DECAY_RATE = 0.02  # energy lost per frame
MOVE_ENERGY_COST = 0.01  # additional cost per frame while moving
ATTACK_ENERGY_COST = 0.5  # energy cost per attack action
COMBAT_COOLDOWN = 30  # frames between attacks

CREATURE_COLORS = {
    "Hunter": (220, 50, 50),
    "Grazer": (50, 180, 50),
    "PackHunter": (50, 50, 220),
    "Scavenger": (220, 220, 50),
}
```

### creature.py

The core abstraction. Defines `Creature` base class, `Perception`, and `Action`.

#### Perception (dataclass)

What a creature can see in its vision radius:

```python
@dataclass
class FoodSpot:
    x: float
    y: float
    amount: float

@dataclass
class CreatureSpot:
    x: float
    y: float
    creature_type: str
    size: int
    energy_pct: float  # 0.0 - 1.0, how healthy they look

@dataclass
class Perception:
    nearby_food: list[FoodSpot]
    nearby_creatures: list[CreatureSpot]
    self_energy: float
    self_x: float
    self_y: float
    self_angle: float
    world_width: int
    world_height: int
```

#### Action (dataclass)

What a creature decides to do each frame. Only one action per frame:

```python
@dataclass
class Action:
    target_angle: float  # desired heading
    target_speed: float  # desired speed (0 = stop, up to creature's max_speed)
    attack_target_id: int | None  # creature ID to attack, or None
```

Movement always happens. Attack is attempted if `attack_target_id` is not None and target is within melee range.

#### Creature (base class)

```python
class Creature:
    __slots__ = [
        'id', 'x', 'y', 'angle', 'speed', 'max_speed',
        'energy', 'max_energy', 'attack_power', 'defense_power',
        'vision_radius', 'creature_type', 'color',
        'cooldown',
    ]

    def __init__(self, x, y, creature_type, color):
        # sets all slots from config defaults

    @abstractmethod
    def decide(self, perception: Perception) -> Action:
        """Override this to define AI behavior. Returns one Action per frame."""
        ...

    def take_damage(self, amount: float) -> float:
        """Apply damage (already reduced by defense). Returns actual damage taken."""

    def eat_food(self, amount: float):
        """Restore energy, capped at max_energy."""

    @property
    def size(self) -> float:
        """Dynamic size based on current energy. DEFAULT_SIZE * (energy / DEFAULT_ENERGY)."""
        ...

    @property
    def is_alive(self) -> bool:
        return self.energy > 0
```

**Key rule**: Subclasses ONLY override `decide()`. All state mutation (movement, damage, energy) is done by `World`.

### world.py

The simulation engine. Owns all entities and runs the game loop.

```python
class World:
    def __init__(self):
        self.creatures: list[Creature] = []
        self.foods: list[Food] = []
        self.tick: int = 0
        self.game_over: bool = False
        self.winner: Creature | None = None

    def spawn_creatures(self, creature_classes: list[type[Creature]]):
        """Create N creatures of each type, randomly positioned."""

    def update(self) -> list[Event]:
        """One simulation tick. Returns list of Events for renderer."""

    def _spawn_food(self):
        """Periodically add food at random positions."""

    def _build_perception(self, creature: Creature) -> Perception:
        """Query all entities within creature's vision radius."""

    def _resolve_movement(self, creature: Creature, action: Action):
        """Apply movement from action, clamp to world bounds."""

    def _resolve_attacks(self, attacks: list[tuple[Creature, int]]):
        """Process all attack actions via combat.py."""

    def _check_food_collision(self):
        """Creature touches food -> eat it."""

    def _apply_energy_decay(self):
        """All creatures lose energy each tick. Dead creatures removed."""

    def _check_win_condition(self):
        """Game over when <= 1 creature alive."""
```

**Update order per tick**:
1. Spawn food (if interval reached)
2. Build perception for each creature
3. Call `creature.decide(perception)` for each alive creature
4. Resolve all movements
5. Resolve all attacks (via combat.py)
6. Check food collisions
7. Apply energy decay
8. Remove dead creatures
9. Check win condition

### combat.py

Centralized combat resolution. Deterministic, no randomness.

```python
def resolve_attack(attacker: Creature, defender: Creature) -> CombatResult:
    """
    Damage formula:
        raw_damage = attacker.attack_power - defender.defense_power * 0.5
        size_bonus = (attacker.size - defender.size) * 0.3
        final_damage = max(0.1, raw_damage + size_bonus)
    
    Energy cost: attacker pays ATTACK_ENERGY_COST
    
    Returns CombatResult with damage dealt, energy costs.
    """

@dataclass
class CombatResult:
    attacker_id: int
    defender_id: int
    damage: float
    attacker_energy_cost: float
    defender_killed: bool
```

Combat rules:
- Attack only possible if target is within `attacker.size + defender.size + 5` pixels (melee range)
- Attacker must not be on cooldown (`COMBAT_COOLDOWN` frames)
- Damage = attacker.attack_power - defender.defense_power * 0.5, minimum 0.1
- Size advantage: bigger creature deals bonus damage (size is dynamic, scales with energy)
- Attacker pays energy cost regardless of outcome
- Defender dies if energy reaches 0; attacker gains 30% of defender's remaining energy

### food.py

Simple food entity:

```python
class Food:
    __slots__ = ['id', 'x', 'y', 'amount', 'color']
    AMOUNT_MIN = 10.0
    AMOUNT_MAX = 30.0
```

Food spawns at random positions. When a creature overlaps a food item (distance < creature.size + 3), the creature eats it: gains energy equal to food.amount, food is consumed.

### renderer.py

Handles all pygame drawing. No game logic.

```python
class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont(None, 24)

    def render(self, world: World):
        """Draw everything: food, creatures, HUD."""

    def _draw_food(self, foods: list[Food]):
        """Green circles, size proportional to amount."""

    def _draw_creatures(self, creatures: list[Creature]):
        """Circles with a direction indicator line, sized by energy. Colored by type."""

    def _draw_hud(self, world: World):
        """Top bar: tick count, alive count by type, total alive."""

    def _draw_game_over(self, winner: Creature):
        """Overlay announcing winner."""
```

### creature_loader.py

Auto-discovery of creature classes:

```python
def load_creatures() -> list[type[Creature]]:
    """
    Import all modules in creatures/ directory.
    Find all classes that subclass Creature and are not Creature itself.
    Return them as a list.
    """
```

This lets users drop a new `.py` file in `creatures/` with a Creature subclass, and it automatically joins the next simulation run.

### main.py

Entry point:

```python
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    
    creature_classes = load_creatures()
    world = World()
    world.spawn_creatures(creature_classes)
    renderer = Renderer(screen)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        
        if not world.game_over:
            world.update()
        
        renderer.render(world)
        clock.tick(FPS)
    
    pygame.quit()
```

## Built-in Creature Types

### Hunter (hunter.py)
- **Stats**: high attack, moderate speed, low vision, high energy cost
- **AI**: target nearest creature, pursue and attack. Eats food only when low energy.
- **Color**: Red `(220, 50, 50)`

### Grazer (grazer.py)
- **Stats**: low attack, high defense, large vision, efficient energy usage
- **AI**: seek nearest food, flee from nearby creatures. Fights only when cornered.
- **Color**: Green `(50, 180, 50)`

### PackHunter (pack_hunter.py)
- **Stats**: low attack/defense individually, moderate speed, small vision
- **AI**: seek nearby allies, coordinate attacks on nearest non-PackHunter. Weakest 1v1 but strong in groups.
- **Color**: Blue `(50, 50, 220)`

### Scavenger (scavenger.py)
- **Stats**: high speed, low attack/defense, tiny size
- **AI**: rush to food, grab it, run from everyone. Never initiates combat.
- **Color**: Yellow `(220, 220, 50)`

## Data Flow

```
main.py game loop
    │
    ├─ World.update()
    │   ├─ spawn_food()
    │   ├─ for each creature:
    │   │   ├─ perception = _build_perception(creature)
    │   │   └─ action = creature.decide(perception)
    │   ├─ _resolve_movement(actions)
    │   ├─ _resolve_attacks(actions)  → combat.py
    │   ├─ _check_food_collision()
    │   ├─ _apply_energy_decay()
    │   └─ _check_win_condition()
    │
    └─ Renderer.render(world)
```

## Extending: Adding a New Creature

1. Create `creatures/my_creature.py`
2. Define a class inheriting `Creature`
3. Override `decide(self, perception) -> Action`
4. Optionally override `__init__` to customize stats
5. It auto-loads on next run

Example:

```python
from creature import Creature, Perception, Action
import math

class Coward(Creature):
    def __init__(self, x, y):
        super().__init__(x, y, "Coward", (200, 200, 200))
        self.max_speed = 3.5
        self.vision_radius = 150

    def decide(self, perception: Perception) -> Action:
        if perception.nearby_creatures:
            nearest = min(perception.nearby_creatures,
                         key=lambda c: math.hypot(c.x - self.x, c.y - self.y))
            flee_angle = math.atan2(self.y - nearest.y, self.x - nearest.x)
            return Action("move", flee_angle, self.max_speed, None)
        
        if perception.nearby_food:
            food = min(perception.nearby_food,
                      key=lambda f: math.hypot(f.x - self.x, f.y - self.y))
            angle = math.atan2(food.y - self.y, food.x - self.x)
            return Action("move", angle, self.max_speed, None)
        
        return Action("move", self.angle, self.max_speed * 0.5, None)
```

## Win Condition

Simulation ends when 0 or 1 creature remains alive. The last creature standing (or the last species if implementing team mode) is declared the winner. A game-over overlay shows the winner's type and survival time.

## Performance Considerations

- Use `__slots__` on Creature and Food for memory efficiency
- Vision queries: spatial partitioning via grid (divide world into cells of size = max_vision_radius) to avoid O(n^2) perception checks
- Creature count capped at 200 to maintain 60 FPS
- Food list cleanup uses list comprehension, not in-place removal during iteration

## Dependencies

- Python 3.10+
- pygame >= 2.0
- numpy >= 1.20 (for potential spatial grid optimization)
