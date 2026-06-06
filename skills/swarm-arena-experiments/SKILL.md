---
name: swarm-arena-experiments
description: Use when working in the swarm_arena project to run or explain independent GA and RL creature training experiments, validate training commands, inspect outputs, or help students compare experiment methods.
---

# Swarm Arena Experiments

Use this skill in `/Users/gaojihe/apps/swarm_arena` when the task involves running, validating, documenting, or explaining creature training experiments.

## Project Assumptions

- Run commands from the repository root.
- Training entrypoint: `python3 train.py`.
- Normal game entrypoint: `python3 main.py`.
- Built-in training methods are independent student experiments:
  - `ga`: genetic algorithm parameter training for an `EvolvableCreature`.
  - `rl`: Q-learning over discrete high-level actions.
- Do not put generated example creatures into `creatures/` unless the user wants them loaded into the live game; that directory is auto-scanned.

## Method Selection

Use GA when the student has written an `EvolvableCreature` with `gene_defs` and wants to tune numeric parameters.

Use RL when the student wants the agent to learn high-level action selection (`FLEE_THREAT`, `CHASE_PREY`, `SEEK_FOOD`, `REPRODUCE`, `WANDER`, `REST`) without writing full decision rules.

## Core Commands

GA:

```bash
python3 train.py --method ga --creature creatures/apex.py --generations 20
```

RL:

```bash
python3 train.py --method rl --episodes 200 --output best_policy.json
```

Legacy GA compatibility:

```bash
python3 train.py --creature creatures/apex.py --generations 20
```

## Smoke Tests

Use small maps and tiny populations for fast validation:

```bash
PYTHONPYCACHEPREFIX=.pycache_check python3 -m py_compile \
  train.py trainer.py evolvable.py training/*.py
```

```bash
python3 train.py --method ga --creature creatures/apex.py \
  --generations 1 --population-size 2 --width 240 --height 180 \
  --seed 2 --output /private/tmp/swarm_ga_params.json
```

```bash
python3 train.py --method rl --episodes 1 --width 240 --height 180 \
  --seed 1 --output /private/tmp/swarm_rl_policy.json
```

If `py_compile` fails because Python tries to write cache files outside the workspace, set `PYTHONPYCACHEPREFIX=.pycache_check`, then remove `.pycache_check` after validation.

## Outputs

- GA writes gene parameters, normally `best_params.json`.
- RL writes a Q-learning policy, normally `best_policy.json`.
- Use `--history-output` with GA when the user wants per-generation history.

## Reporting Results

When reporting an experiment run, include:

- Command used.
- Best fitness or final visible metric from stdout.
- Output file path.
- Whether the run was a smoke test or a real training run.

For real student experiments, recommend longer runs than smoke tests:

- GA: 20-50 generations, population 30+.
- RL: 200-1000 episodes.

## Common Pitfalls

- GA requires `--creature`; RL does not.
- `--episodes` currently matters most for RL. GA still uses the original single-evaluation trainer.
- Files in `creatures/` affect both the live game and opponent loading during training.
