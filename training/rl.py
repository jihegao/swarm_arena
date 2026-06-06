from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from typing import Callable

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from creature import Creature, Perception
from creature_loader import load_creatures
from training.evaluation import reset_entity_ids
from training.policy import ACTION_NAMES, decode_action, discrete_state_key, encode_features
from world import World


ProgressFn = Callable[[str], None]


@dataclass(frozen=True)
class RLConfig:
    episodes: int = 300
    learning_rate: float = 0.2
    discount: float = 0.9
    epsilon: float = 0.25
    epsilon_decay: float = 0.995
    min_epsilon: float = 0.03
    width: int = SCREEN_WIDTH
    height: int = SCREEN_HEIGHT
    seed: int | None = None
    quiet_opponent_warnings: bool = True

    def __post_init__(self):
        if self.episodes < 1:
            raise ValueError("episodes must be at least 1")
        if not 0 < self.learning_rate <= 1:
            raise ValueError("learning_rate must be in (0, 1]")
        if not 0 <= self.discount <= 1:
            raise ValueError("discount must be between 0 and 1")
        if not 0 <= self.epsilon <= 1:
            raise ValueError("epsilon must be between 0 and 1")
        if not 0 <= self.min_epsilon <= 1:
            raise ValueError("min_epsilon must be between 0 and 1")


@dataclass
class RLEpisodeStats:
    episode: int
    fitness: float
    survival_ticks: int
    survivor_count: int
    total_energy: float
    epsilon: float


@dataclass
class RLTrainingResult:
    q_table: dict[str, dict[str, float]]
    best_fitness: float
    history: list[RLEpisodeStats]


class QPolicy:
    def __init__(
        self,
        q_table: dict[str, dict[str, float]] | None = None,
        learning_rate: float = 0.2,
        discount: float = 0.9,
        epsilon: float = 0.25,
    ):
        self.q_table = q_table or {}
        self.learning_rate = learning_rate
        self.discount = discount
        self.epsilon = epsilon

    def values(self, state: str) -> dict[str, float]:
        if state not in self.q_table:
            self.q_table[state] = {name: 0.0 for name in ACTION_NAMES}
        return self.q_table[state]

    def select_action(self, state: str, explore: bool = True) -> str:
        if explore and random.random() < self.epsilon:
            return random.choice(ACTION_NAMES)
        values = self.values(state)
        return max(values, key=values.get)

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str | None,
        done: bool = False,
    ):
        values = self.values(state)
        current = values[action]
        next_best = 0.0 if done or next_state is None else max(self.values(next_state).values())
        target = reward + self.discount * next_best
        values[action] = current + self.learning_rate * (target - current)


class RLTrainer:
    def __init__(
        self,
        config: RLConfig | None = None,
        opponent_classes: list[type[Creature]] | None = None,
    ):
        self.config = config or RLConfig()
        self.opponent_classes = opponent_classes
        self.policy = QPolicy(
            learning_rate=self.config.learning_rate,
            discount=self.config.discount,
            epsilon=self.config.epsilon,
        )
        if self.config.seed is not None:
            random.seed(self.config.seed)

    def train(self, progress_callback: ProgressFn | None = None) -> RLTrainingResult:
        history: list[RLEpisodeStats] = []
        best_fitness = float("-inf")

        for episode in range(1, self.config.episodes + 1):
            stats = self._run_episode(episode)
            history.append(stats)
            best_fitness = max(best_fitness, stats.fitness)
            self.policy.epsilon = max(
                self.config.min_epsilon,
                self.policy.epsilon * self.config.epsilon_decay,
            )
            if progress_callback is not None and (episode == 1 or episode % 10 == 0 or episode == self.config.episodes):
                progress_callback(
                    f"Episode {episode:04d}/{self.config.episodes:04d}: "
                    f"fitness={stats.fitness:.3f} survivors={stats.survivor_count} "
                    f"ticks={stats.survival_ticks} epsilon={stats.epsilon:.3f}"
                )

        return RLTrainingResult(self.policy.q_table, best_fitness, history)

    def _run_episode(self, episode: int) -> RLEpisodeStats:
        reset_entity_ids()
        if self.config.seed is not None:
            random.seed(self.config.seed + episode)

        policy = self.policy
        instances: list[Creature] = []

        class LearningCreature(Creature):
            def __init__(self, x: float, y: float):
                super().__init__(x, y, "LearningCreature", (80, 190, 255))
                self.max_speed = 2.2
                self.max_energy = 90.0
                self.energy = self.max_energy
                self.vision_radius = 180.0
                self._last_state: str | None = None
                self._last_action: str | None = None
                self._last_energy: float = self.energy
                self.clamp()
                instances.append(self)

            def decide(self, perception: Perception):
                features = encode_features(perception)
                state = discrete_state_key(features)
                if self._last_state is not None and self._last_action is not None:
                    energy_delta = perception.self_energy - self._last_energy
                    reward = 0.01 + energy_delta / 50.0
                    if features.threat_count > 0 and self._last_action == "FLEE_THREAT":
                        reward += 0.02
                    policy.update(self._last_state, self._last_action, reward, state)

                action_name = policy.select_action(state, explore=True)
                self._last_state = state
                self._last_action = action_name
                self._last_energy = perception.self_energy
                return decode_action(action_name, perception, self)

        opponents = self._opponents()
        classes: list[type[Creature]] = [LearningCreature]
        classes.extend(cls for cls in opponents if cls.__name__ != LearningCreature.__name__)

        world = World(self.config.width, self.config.height)
        world.spawn_creatures(classes)
        for creature in world.creatures:
            world._class_map[creature.creature_type] = type(creature)

        last_alive_tick = 0
        while not world.game_over:
            if any(c.is_alive and isinstance(c, LearningCreature) for c in world.creatures):
                last_alive_tick = world.tick
            world.update()

        survivors = [c for c in world.creatures if c.is_alive and isinstance(c, LearningCreature)]
        won = world.winner is not None and isinstance(world.winner, LearningCreature)
        for c in instances:
            if c._last_state is None or c._last_action is None:
                continue
            terminal_reward = 20.0 if won and c.is_alive else -10.0 if not c.is_alive else 2.0
            policy.update(c._last_state, c._last_action, terminal_reward, None, done=True)

        total_energy = sum(c.energy for c in survivors)
        if not survivors:
            fitness = last_alive_tick / 5000
        else:
            fitness = len(survivors) * 10 + total_energy / 100 + (20 if won else 0)

        return RLEpisodeStats(
            episode=episode,
            fitness=fitness,
            survival_ticks=last_alive_tick,
            survivor_count=len(survivors),
            total_energy=total_energy,
            epsilon=policy.epsilon,
        )

    def _opponents(self) -> list[type[Creature]]:
        if self.opponent_classes is not None:
            return self.opponent_classes
        if self.config.quiet_opponent_warnings:
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                return load_creatures()
        return load_creatures()


def save_rl_result(result: RLTrainingResult, output: str):
    payload = {
        "type": "q_learning_policy",
        "actions": list(ACTION_NAMES),
        "q_table": result.q_table,
        "best_fitness": result.best_fitness,
        "history": [asdict(item) for item in result.history],
    }
    with open(output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def load_q_policy(path: str) -> QPolicy:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    q_table = payload.get("q_table", payload)
    return QPolicy(q_table=q_table, epsilon=0.0)
