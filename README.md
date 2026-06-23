# Swarm Arena / 竞争生存仿真

Developer documentation for a small competitive survival simulator. The project
is useful as a codebase for agent behavior experiments, classroom tooling,
genetic parameter search, and Q-learning policy exploration.

这是一个面向开发者的竞争生存仿真项目文档。项目可用于实现生物行为、课堂实验工具、遗传算法参数搜索，以及 Q-learning 高层策略探索。

## Project Shape / 项目结构

| Path | Purpose | 说明 |
| --- | --- | --- |
| `main.py` | Starts the visible Pygame simulation. | 启动可视化仿真。 |
| `world.py` | Owns world state, ticks, spawning, eating, reproduction, and scoring. | 管理世界状态、tick、生成、进食、繁殖和计分。 |
| `creature.py` | Defines `Creature`, `Perception`, and `Action`. | 定义生物基类、感知输入和行为输出。 |
| `creatures/` | Built-in and custom creature implementations. | 内置和自定义生物实现。 |
| `evolvable.py` | Base class for GA-tunable creatures. | GA 可调参生物的基类。 |
| `train.py` | Command-line entry point for GA and RL training. | GA 和 RL 训练入口。 |
| `training/` | Evaluation, policy, RL, and visual status helpers. | 训练评估、策略、强化学习和可视化状态辅助模块。 |
| `renderer.py` | Pygame rendering for the arena and side panel. | 竞技场和侧栏的 Pygame 渲染。 |
| `agent.md` | Protocol for AI-assisted classroom coaching. | AI 辅助课堂教练协议。 |
| `courseware.html` | Developer-facing bilingual courseware/deck. | 面向开发者的双语工程课件。 |
| `tests/` | Regression tests for safety, GA status, and RL visualization. | 安全性、GA 状态和 RL 可视化回归测试。 |

## Local Setup / 本地环境

Use the repository-local virtual environment first. This is the current project
convention and avoids mismatches with system Python.

优先使用仓库内 `.venv`。这是当前项目约定，可避免系统 Python 版本和依赖差异。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip pygame pytest
.venv/bin/python --version
.venv/bin/python -c "import pygame; print(pygame.version.ver)"
```

Run the simulation:

运行仿真：

```bash
.venv/bin/python main.py
```

If the active environment intentionally uses `python3` directly, keep commands
consistent inside that environment. For repository validation, prefer
`.venv/bin/python`.

如果本地环境明确约定直接使用 `python3`，请保持同一环境内命令一致。仓库验证仍优先使用 `.venv/bin/python`。

## Simulation Model / 仿真模型

The arena is a 2D world containing food and creature instances. Each tick:

每个 tick 中，二维世界会处理食物和生物实例：

1. The world builds a bounded `Perception` for each living creature.
2. The creature returns an `Action`.
3. The engine sanitizes invalid angles, speeds, and exceptions.
4. Movement, energy decay, eating, reproduction, scoring, and end conditions run.
5. The renderer displays the arena and leaderboard when running visually.

1. 世界为每个存活生物构造有范围限制的 `Perception`。
2. 生物返回一个 `Action`。
3. 引擎清洗非法角度、速度和异常。
4. 执行移动、能量衰减、进食、繁殖、计分和结束条件。
5. 可视化运行时，渲染竞技场和排行榜。

The default match ends at 5000 ticks, or earlier when only one species remains.
At the time limit, the species with the largest living population wins; within
that species, the highest-energy creature is reported as the winner.

默认比赛在 5000 tick 结束；如果只剩一种生物则提前结束。到达时间上限时，存活数量最多的物种获胜；该物种中能量最高的个体会被报告为胜者。

## Creature API / 生物 API

Custom creatures live in `creatures/*.py`. A valid creature class:

自定义生物放在 `creatures/*.py`。合法生物类需要：

- inherits from `Creature` or `EvolvableCreature`;
- has `__init__(self, x: float, y: float)`;
- calls `super().__init__(x, y, creature_type, color)`;
- implements `decide(self, perception: Perception) -> Action`;
- can be imported without interactive prompts or side effects.

- 继承 `Creature` 或 `EvolvableCreature`；
- 提供 `__init__(self, x: float, y: float)`；
- 调用 `super().__init__(x, y, creature_type, color)`；
- 实现 `decide(self, perception: Perception) -> Action`；
- 能被导入，且导入时不触发交互或额外副作用。

Minimal implementation:

最小实现：

```python
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from creature import Action, Creature, Perception


class RuleSurvivor(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "RuleSurvivor", (255, 128, 0))
        self.max_speed = 2.2
        self.max_energy = 100.0
        self.energy = self.max_energy
        self.vision_radius = 160.0

    def decide(self, perception: Perception) -> Action:
        if perception.nearby_food:
            food = min(
                perception.nearby_food,
                key=lambda f: math.hypot(f.x - perception.self_x, f.y - perception.self_y),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed)

        return Action(perception.self_angle, self.max_speed * 0.5)
```

`Perception` exposes only local information. The engine intentionally prevents a
creature from reading the full world state through the decision API.

`Perception` 只暴露局部信息。引擎有意避免生物通过决策 API 读取完整世界状态。

| Field | Type | 中文说明 |
| --- | --- | --- |
| `self_x`, `self_y` | `float` | 当前坐标 |
| `self_angle` | `float` | 当前朝向，弧度，`0` points right |
| `self_size` | `float` | 当前体型，由能量动态计算 |
| `self_energy` | `float` | 当前能量 |
| `self_max_energy` | `float` | 初始/最大参考能量 |
| `world_width`, `world_height` | `int` | 世界尺寸 |
| `nearby_food` | `list[FoodSpot]` | 视野内食物 |
| `nearby_creatures` | `list[CreatureSpot]` | 视野内其他生物 |

`Action` controls one frame:

`Action` 控制单帧行为：

```python
Action(
    target_angle,      # float, radians / 弧度
    target_speed,      # float, clamped to 0..max_speed / 会被限制到合法速度
    attack_target_id,  # int | None, intent marker only / 仅标记追击意图
    reproduce,         # bool, request reproduction / 请求繁殖
)
```

Eating is collision-based. A creature automatically eats a smaller creature on
contact after cooldown rules pass. `attack_target_id` is not required for eating.

进食/战斗基于碰撞。冷却规则通过后，生物碰到更小生物会自动吃掉对方；`attack_target_id` 不是吃掉对手的必要条件。

## Attribute Budget / 属性预算

The core tunable attributes are constrained by a shared point budget.

核心可调属性受统一点数预算约束。

| Attribute | Default | Min | Max | 中文说明 |
| --- | ---: | ---: | ---: | --- |
| `max_speed` | 1.0 | 0.5 | 4.0 | 最大移动速度 |
| `max_energy` | 100.0 | 30.0 | 200.0 | 初始能量 |
| `vision_radius` | 20.0 | 50.0 | 300.0 | 视野半径 |

Each attribute is normalized, then the sum is capped at `1.5`. If a creature
exceeds the budget, attributes are scaled down proportionally.

每项属性会归一化后求和，总预算上限为 `1.5`。如果超预算，引擎会按比例缩小属性。

```text
normalized = (value - min_value) / (max_value - min_value)
budget = normalized_speed + normalized_energy + normalized_vision
```

This keeps custom creatures comparable and makes speed, energy, and vision real
tradeoffs instead of free upgrades.

这个限制保证自定义生物可比较，也让速度、能量、视野成为真实取舍，而不是免费增强。

## Training Workflows / 训练工作流

`train.py` supports two implemented routes. They are independent workflows, not
prerequisites for each other.

`train.py` 当前支持两条已实现路线。它们彼此独立，不互为前置条件。

### GA Parameter Search / GA 参数搜索

Use GA when the behavior structure is readable but numeric thresholds need
tuning. The target class must inherit `EvolvableCreature` and define gene ranges.

当行为结构已经清晰，但速度、视野、逃跑距离、繁殖阈值等数字需要调优时使用 GA。目标类必须继承 `EvolvableCreature` 并定义基因范围。

```bash
.venv/bin/python train.py \
  --method ga \
  --creature creatures/<creature_file>.py \
  --generations 20 \
  --history-output ga_history.json \
  --output best_params.json
```

Treat GA output as evidence for a parameter review. Do not blindly copy the
highest-scoring genome into production without a visible before/after check.

GA 输出应作为参数评审证据。不要在没有可视化前后对比的情况下直接把最高分基因写回正式生物。

### Q-learning Policy Exploration / Q-learning 策略探索

Use RL to inspect high-level action tradeoffs: seek food, flee, chase, wander,
or reproduce. The current command trains `LearningCreature`; it does not
automatically rewrite arbitrary creature files.

RL 用于观察高层动作取舍：找食物、逃跑、追击、漫步、繁殖。当前命令训练的是 `LearningCreature`，不会自动改写任意生物文件。

```bash
.venv/bin/python train.py --method rl --episodes 200 --output best_policy.json
```

After training, inspect the learned policy and migrate only the useful idea into
a readable creature rule or small lookup.

训练后应检查学到的策略，只把有价值的策略思想迁移成可读规则或小型查表逻辑。

## Developer Validation / 开发验证

Run the regression suite with a local bytecode cache path. This avoids cache
permission and interpreter mismatch issues seen in this repository.

运行回归测试时指定本地字节码缓存路径，可避免本仓库曾遇到的缓存路径和解释器差异问题。

```bash
PYTHONPYCACHEPREFIX=/Users/gaojihe/apps/swarm_arena/.pycache_check \
  .venv/bin/python -m pytest -q
```

Recommended checks before publishing a behavior or training change:

发布行为或训练改动前建议检查：

- import the new creature file;
- run a short visible simulation;
- run focused tests for the touched subsystem;
- inspect generated `best_params.json`, `ga_history.json`, or `best_policy.json`
  before committing them;
- keep generated experiments out of commits unless they are intentional examples
  or release artifacts.

- 导入新的生物文件；
- 运行一次短可视化仿真；
- 对改动子系统运行聚焦测试；
- 提交前检查生成的 `best_params.json`、`ga_history.json` 或 `best_policy.json`；
- 除非它们是有意保留的示例或发布产物，否则不要提交实验生成文件。

## Publishing / 发布到 GitHub

For documentation or behavior changes, publish from a clean, named branch:

文档或行为改动建议从干净的具名分支发布：

```bash
git status --short --branch
git add README.md courseware.html
git commit -m "docs: add bilingual developer materials"
git push origin HEAD
```

If the branch is intended to land in `main`, open a pull request and keep the PR
description focused on scope, validation, and generated artifacts.

如果该分支准备合入 `main`，请打开 PR，并在说明中聚焦范围、验证和生成物状态。

## AI-assisted Development Boundary / AI 辅助开发边界

`agent.md` is intentionally separate from this README. It defines how an AI
assistant should coach a classroom practice cycle without replacing the learner's
observation, route choice, naming, or attribution.

`agent.md` 与 README 刻意分离。它定义 AI 助手如何引导课堂实践循环，同时不替代学习者的观察、路线选择、命名和署名。

When changing the classroom flow, keep `README.md`, `courseware.html`, and
`agent.md` aligned. The durable loop is:

修改课堂流程时，保持 `README.md`、`courseware.html` 和 `agent.md` 对齐。当前稳定流程是：

```text
observe -> choose one route -> validate one change -> publish with attribution
观察 -> 选择一条路线 -> 验证一个改动 -> 带署名发布
```
