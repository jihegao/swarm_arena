from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

from evolvable import EvolvableCreature
from trainer import GAConfig, GeneticTrainer
from training.rl import RLConfig, RLTrainer, save_rl_result


def load_evolvable_class(
    path: str,
    class_name: str | None = None,
) -> type[EvolvableCreature]:
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(abs_path)

    module_name = f"_ga_creature_{os.path.splitext(os.path.basename(abs_path))[0]}"
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")

    module_dir = os.path.dirname(abs_path)
    project_root = os.path.dirname(module_dir)
    for import_dir in (module_dir, project_root):
        if import_dir and import_dir not in sys.path:
            sys.path.insert(0, import_dir)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    candidates = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, EvolvableCreature)
            and attr is not EvolvableCreature
            and not getattr(attr, "__abstractmethods__", None)
        ):
            candidates.append(attr)

    if class_name:
        for candidate in candidates:
            if candidate.__name__ == class_name:
                return candidate
        raise ValueError(f"No EvolvableCreature subclass named {class_name!r} in {path}")

    if not candidates:
        raise ValueError(f"No concrete EvolvableCreature subclass found in {path}")
    if len(candidates) > 1:
        names = ", ".join(cls.__name__ for cls in candidates)
        raise ValueError(f"Multiple evolvable classes found ({names}); use --class-name")
    return candidates[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train creatures with GA or RL.")
    parser.add_argument("--method", choices=("ga", "rl"), default="ga")
    parser.add_argument("--creature", help="Path to the student's evolvable creature .py file. Required for GA.")
    parser.add_argument("--class-name", help="Class name to train when the file defines multiple candidates.")
    parser.add_argument("--generations", type=int, default=50)
    parser.add_argument("--population-size", type=int, default=30)
    parser.add_argument("--mutation-rate", type=float, default=0.15)
    parser.add_argument("--elite-count", type=int, default=2)
    parser.add_argument("--tournament-size", type=int, default=5)
    parser.add_argument("--episodes", type=int, default=1)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", default="best_params.json")
    parser.add_argument("--history-output", help="Optional path for training history JSON.")

    parser.add_argument("--learning-rate", type=float, default=0.2)
    parser.add_argument("--discount", type=float, default=0.9)
    parser.add_argument("--epsilon", type=float, default=0.25)
    parser.add_argument("--epsilon-decay", type=float, default=0.995)
    parser.add_argument("--min-epsilon", type=float, default=0.03)
    return parser.parse_args()


def write_history(path: str, history):
    payload = [
        item.__dict__
        for item in history
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def train_ga(args: argparse.Namespace) -> int:
    if not args.creature:
        raise ValueError("--creature is required when --method ga")
    creature_cls = load_evolvable_class(args.creature, args.class_name)
    config = GAConfig(
        population_size=args.population_size,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        elite_count=args.elite_count,
        tournament_size=args.tournament_size,
        width=args.width,
        height=args.height,
        seed=args.seed,
    )
    trainer = GeneticTrainer(creature_cls, config)
    print(
        f"Training {creature_cls.__name__}: "
        f"method=ga generations={config.generations} population={config.population_size}",
        flush=True,
    )
    result = trainer.train(lambda message: print(message, flush=True))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result.best_genes, f, indent=2, sort_keys=True)
        f.write("\n")
    if args.history_output:
        write_history(args.history_output, result.history)

    print(f"Best fitness: {result.best_fitness:.3f}")
    print(f"Wrote {args.output}")
    if args.history_output:
        print(f"Wrote {args.history_output}")
    return 0


def train_rl(args: argparse.Namespace) -> int:
    if args.output == "best_params.json":
        args.output = "best_policy.json"
    config = RLConfig(
        episodes=args.episodes,
        learning_rate=args.learning_rate,
        discount=args.discount,
        epsilon=args.epsilon,
        epsilon_decay=args.epsilon_decay,
        min_epsilon=args.min_epsilon,
        width=args.width,
        height=args.height,
        seed=args.seed,
    )
    trainer = RLTrainer(config)
    print(
        f"Training LearningCreature: method=rl episodes={config.episodes} "
        f"epsilon={config.epsilon}",
        flush=True,
    )
    result = trainer.train(lambda message: print(message, flush=True))
    save_rl_result(result, args.output)
    print(f"Best fitness: {result.best_fitness:.3f}")
    print(f"Wrote {args.output}")
    return 0


def main() -> int:
    args = parse_args()
    if args.method == "ga":
        return train_ga(args)
    if args.method == "rl":
        return train_rl(args)
    raise ValueError(f"Unknown method: {args.method}")


if __name__ == "__main__":
    raise SystemExit(main())
