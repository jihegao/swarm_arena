# Creature 训练扩展设计：GA + RL + GEP

## 背景

当前项目已经有一套离线遗传算法训练能力：

- `EvolvableCreature` 用 `gene_defs` 声明可训练浮点参数。
- `GeneticTrainer` 在 headless `World` 中评估基因组。
- `train.py` 输出 `best_params.json`，学生再把参数加载回自己的 creature。

这个基础适合继续扩展，但强化学习（RL）和 Genetic Expression Programming（GEP）的训练对象不同：

| 方法 | 训练对象 | 最适合解决的问题 |
|------|----------|------------------|
| GA | 一组数值参数 | 调行为阈值、速度比例、繁殖阈值等 |
| RL | 状态到动作的策略 | 在不同局面下动态选择行动 |
| GEP | 可解释的决策表达式或规则树 | 自动生成 `decide()` 里的判断逻辑 |

因此扩展目标不是把三者强行塞进同一个基因字典，而是形成一个统一训练平台，让不同算法共享评估环境、指标、输出格式和 CLI。

## 设计目标

1. 保留现有 GA 用法，已有 `EvolvableCreature` 和 `train.py` 不被破坏。
2. 新增 RL 训练，让 creature 能根据局面学习“逃跑、觅食、追击、繁殖、游走”等高层动作选择。
3. 新增 GEP 训练，让系统能自动生成可读、可移植的 `decide()` 决策表达式。
4. 训练仍然离线运行，不影响正常 `main.py` 游戏。
5. 输出结果可直接落地为参数文件、策略文件或 Python creature 模板。

## 总体架构

```text
creature / policy 定义
        |
        v
Training CLI
        |
        +-- GA Trainer   -> best_params.json
        +-- RL Trainer   -> best_policy.json
        +-- GEP Trainer  -> generated_creature.py / expression.json
        |
        v
EpisodeEvaluator
        |
        v
Headless World simulation
```

建议将现有训练代码逐步拆成以下模块：

```text
train.py                       # 统一 CLI 入口
trainer.py                     # 保留兼容，可继续导出 GAConfig/GeneticTrainer
training/
  __init__.py
  evaluation.py                # EpisodeEvaluator、RewardTracker、评估指标
  policy.py                    # Policy 接口、状态编码、动作解码
  ga.py                        # 迁移或包装现有 GeneticTrainer
  rl.py                        # Q-learning / DQN-like 轻量实现
  gep.py                       # 表达式基因、变异、交叉、代码生成
  outputs.py                   # JSON / Python 文件输出
```

第一阶段可以不马上移动现有 `trainer.py`，先新增 `training/`，再让 `train.py` 根据 `--method` 分发。

## 统一训练抽象

### EpisodeEvaluator

所有训练方法共享同一个评估器：

```python
class EpisodeEvaluator:
    def evaluate_creature_class(self, creature_cls, episodes: int) -> EvaluationResult:
        ...

    def evaluate_policy(self, policy, episodes: int) -> EvaluationResult:
        ...
```

`EvaluationResult` 建议包含：

```python
@dataclass
class EvaluationResult:
    fitness: float
    survival_ticks: float
    survivor_count: float
    total_energy: float
    food_eaten: float
    kills: float
    reproductions: float
    wins: float
```

当前 `World` 没有记录 food/kills/reproduction 事件，第一版可以只使用已有信息：

```text
fitness = survivor_count * 10 + total_energy / 100
灭绝时 fitness = last_alive_tick / GAME_OVER_TICK
```

第二版再给 `World` 增加可选 observer，用于记录奖励事件。

### StateEncoder

RL 和 GEP 不能直接吃完整 `Perception` 对象，应先编码成稳定特征：

| 特征 | 说明 |
|------|------|
| `energy_pct` | `self_energy / self_max_energy` |
| `nearest_food_dist` | 最近食物距离，按视野归一化 |
| `nearest_food_angle` | 最近食物相对角度 |
| `best_food_score` | `amount / distance` |
| `nearest_threat_dist` | 最近大体型威胁距离 |
| `nearest_threat_angle` | 威胁相对角度 |
| `nearest_prey_dist` | 最近可捕食目标距离 |
| `nearest_prey_angle` | 可捕食目标相对角度 |
| `prey_count` | 视野内可吃目标数量 |
| `threat_count` | 视野内威胁数量 |
| `edge_pressure_x/y` | 离边界的风险方向 |

为了教学和调试，第一版 RL 使用离散状态桶：

```text
energy: low / mid / high
food: none / near / far
threat: none / near / far
prey: none / near / far
edge: safe / risky
```

这样可以用 Q-learning，不需要引入 PyTorch。

### ActionDecoder

直接学习连续角度和速度会让问题过难。建议训练高层动作，再转换成 `Action`：

| 动作 | 转换逻辑 |
|------|----------|
| `FLEE_THREAT` | 朝最近威胁反方向全速移动 |
| `CHASE_PREY` | 朝最近可吃目标全速移动 |
| `SEEK_FOOD` | 朝最佳食物移动 |
| `REPRODUCE` | 原地或半速移动并 `reproduce=True` |
| `WANDER` | 按当前角度加轻微扰动移动 |
| `REST` | 原地或低速等待 |

RL 学的是“当前局面应该选哪个高层动作”，不是手写所有几何细节。

## GA 设计调整

GA 保持现有定位：优化参数。

### 保留能力

- `gene_defs`
- 随机初始化
- 锦标赛选择
- 两点交叉
- 高斯变异
- 精英保留
- `best_params.json`

### 建议增强

1. 多 episode 评估：同一基因组跑多个随机种子，减少偶然性。
2. 训练集/验证集种子：防止只适配某个随机开局。
3. 可配置对手集：训练时指定内置对手或学生互打。
4. 输出 history：保存每代 best/avg，便于画曲线。

CLI 示例：

```bash
python train.py --method ga --creature creatures/apex.py --generations 50 --episodes 3
```

输出：

```text
best_params.json
training_history.json
```

## RL 设计

### 第一版：离散 Q-learning

第一版不引入深度学习框架，原因：

- 项目当前是纯 Python 小工程。
- 离散动作更容易让学生理解。
- 可输出可读 JSON 策略表。
- 训练失败时更容易调试。

核心数据：

```python
Q: dict[StateKey, dict[ActionName, float]]
```

训练流程：

```text
每个 episode:
    创建 World
    放入 LearningCreature + 对手
    每 tick:
        Perception -> StateKey
        epsilon-greedy 选择高层动作
        高层动作 -> Action
        world.update()
        计算 reward
        更新 Q(state, action)
```

### Reward 设计

奖励需要同时鼓励短期生存和长期胜利：

| 事件 | reward |
|------|--------|
| 每存活一 tick | `+0.01` |
| 能量增加 | `+delta_energy / 20` |
| 能量下降 | `delta_energy / 50` |
| 吃掉对手 | `+5` |
| 成功繁殖 | `+3` |
| 自己死亡 | `-10` |
| 本物种获胜 | `+20` |

第一版如果没有事件 observer，可先用能量变化、存活、胜负计算奖励。第二版再把吃人、吃食物、繁殖事件接入 observer。

### RL Creature 接入

新增一个包装 creature：

```python
class PolicyCreature(Creature):
    def __init__(self, x, y, policy):
        super().__init__(x, y, "PolicyCreature", color)
        self.policy = policy

    def decide(self, perception):
        state = encode_state(perception)
        action_name = self.policy.select_action(state)
        return decode_action(action_name, perception, self)
```

训练完成输出：

```text
best_policy.json
```

学生可创建最终版：

```python
class MyRLCreature(PolicyCreature):
    def __init__(self, x, y):
        super().__init__(x, y, load_q_policy("best_policy.json"))
```

CLI 示例：

```bash
python train.py --method rl --episodes 500 --seed 42 --output best_policy.json
```

## GEP 设计

GEP 的目标是自动进化 `decide()` 的表达式，而不是只优化数字。它比 GA 更适合生成“规则逻辑”。

### 表达式范围

第一版 GEP 不直接生成任意 Python 代码，避免不安全和不可控。只允许组合白名单函数、特征和常量。

#### 终结符

```text
energy_pct
nearest_food_dist
nearest_threat_dist
nearest_prey_dist
prey_count
threat_count
edge_pressure
constant floats
```

#### 函数集

```text
add, sub, mul, safe_div
min, max
lt, gt
if_else
```

#### 动作叶子

```text
FLEE_THREAT
CHASE_PREY
SEEK_FOOD
REPRODUCE
WANDER
REST
```

表达式示例：

```text
if_else(
  gt(threat_count, 0),
  FLEE_THREAT,
  if_else(gt(energy_pct, 2.0), REPRODUCE, SEEK_FOOD)
)
```

### 染色体表示

建议使用 Karva-like 线性基因：

```python
["if_else", "gt", "SEEK_FOOD", "threat_count", 0.0, "FLEE_THREAT", ...]
```

训练前将线性基因解码为表达式树。这样便于：

- 随机生成
- 交叉
- 变异
- 控制最大深度
- 序列化到 JSON

### GEP 训练流程

```text
初始化表达式种群
循环 generations:
    解码表达式
    包装成 ExpressionPolicyCreature
    在 World 中评估 fitness
    选择 + 交叉 + 变异 + 精英保留
输出最佳表达式与生成的 creature 文件
```

### 输出形式

GEP 应输出两类文件：

```text
best_expression.json       # 可继续训练
generated_creature.py      # 可直接放进 creatures/
```

生成代码应保持可读：

```python
def decide(self, perception):
    features = encode_features(perception)
    action_name = evaluate_expression(EXPRESSION, features)
    return decode_action(action_name, perception, self)
```

后续可以增加“展开成纯 Python if/else”的代码生成模式，但第一版用解释器执行表达式更稳。

CLI 示例：

```bash
python train.py --method gep --generations 80 --population-size 60 \
  --output best_expression.json --creature-output generated_creature.py
```

## 三种方法如何组合

推荐不是三选一，而是形成训练流水线：

### 路线 A：规则 creature + GA

学生先写规则，再用 GA 调参数。

```text
手写 decide() 框架 -> gene_defs 参数化 -> GA 输出 best_params.json
```

适合入门。

### 路线 B：RL 学动作选择 + GA 调身体参数

```text
RL 学 SEEK_FOOD/FLEE/CHASE/REPRODUCE 选择
GA 优化 max_speed/max_energy/vision_radius
```

适合动态策略。

### 路线 C：GEP 生成规则 + GA 微调常量

```text
GEP 生成 if/else 表达式结构
GA 优化表达式里的阈值常量
```

适合自动发现可解释策略。

### 路线 D：GEP 初始化 RL

```text
GEP 找到可用规则
RL 在规则基础上继续学习动作 Q 值
```

适合高级课程，但不建议第一版实现。

## CLI 设计

统一入口：

```bash
python train.py --method ga  --creature creatures/apex.py
python train.py --method rl  --episodes 500
python train.py --method gep
```

通用参数：

| 参数 | 说明 |
|------|------|
| `--method` | `ga` / `rl` / `gep` |
| `--episodes` | 每个候选或策略评估多少局 |
| `--seed` | 随机种子 |
| `--width` / `--height` | 世界尺寸 |
| `--opponents` | 指定对手类型或文件 |
| `--output` | 输出路径 |

GA 参数：

```text
--generations
--population-size
--mutation-rate
--elite-count
--tournament-size
```

RL 参数：

```text
--learning-rate
--discount
--epsilon
--epsilon-decay
--min-epsilon
```

GEP 参数：

```text
--head-length
--max-depth
--constants
--mutation-rate
--crossover-rate
```

## 实施阶段

### Phase 1：训练平台抽象

- 新增 `training/evaluation.py`
- 把现有 `evaluate_genes()` 的 World 运行逻辑抽成通用 episode runner
- `train.py` 增加 `--method ga`，默认仍为 GA，保证兼容
- 输出 `training_history.json`

验收标准：

- 原命令仍可运行。
- 新命令 `python train.py --method ga ...` 可运行。
- GA 结果与旧版接近。

### Phase 2：RL Q-learning

- 新增 `training/policy.py`
- 实现 `StateEncoder` 和 `ActionDecoder`
- 新增 `training/rl.py`
- 输出 `best_policy.json`
- 新增示例 `creatures/rl_creature.py`

验收标准：

- 训练 100 episode 后，策略能明显优于随机游走。
- `best_policy.json` 可被 creature 加载并正常参赛。

### Phase 3：World observer 奖励事件

- 给 `World` 增加可选 `event_observer`
- 在吃食物、吃 creature、繁殖、死亡、胜利时记录事件
- RL reward 使用事件，不再只靠能量差估算

验收标准：

- 不传 observer 时正常游戏行为不变。
- RL 训练日志能统计 food/kills/reproductions。

### Phase 4：GEP 表达式训练

- 新增 `training/gep.py`
- 实现表达式白名单解释器
- 实现表达式种群的初始化、变异、交叉、选择
- 输出 `best_expression.json` 和 `generated_creature.py`

验收标准：

- 生成的 creature 能直接放入 `creatures/` 运行。
- 表达式可读、可复现、可继续训练。

### Phase 5：混合训练

- GEP 生成表达式结构，GA 优化常量。
- RL 使用 GEP 规则作为初始 policy。
- 增加课程示例和对比实验脚本。

验收标准：

- 同一任务可以输出 GA/RL/GEP 三种训练曲线。
- 学生能比较三种方法的优缺点。

## 风险与取舍

| 风险 | 处理方式 |
|------|----------|
| RL 状态空间过大 | 第一版使用离散桶和高层动作 |
| 奖励设计导致投机行为 | 使用胜负、生存、能量、繁殖多指标约束 |
| GEP 生成不可读代码 | 只生成白名单表达式，限制深度 |
| 训练太慢 | 支持小地图、少对手、少 tick 的课程训练模式 |
| 三套训练重复代码 | 共享 EpisodeEvaluator、StateEncoder、ActionDecoder |

## 推荐优先级

最推荐的实现顺序：

1. 先做统一评估器，避免 GA/RL/GEP 各自复制 World 运行逻辑。
2. 再做 RL 的离散 Q-learning，因为它能复用 StateEncoder 和 ActionDecoder。
3. 然后做 World observer，提升 RL 奖励质量。
4. 最后做 GEP，因为它需要稳定的特征、动作和评估器。

这个顺序能保证每一步都有可运行成果，而且不会破坏当前 GA 训练。
