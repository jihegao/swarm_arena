# 遗传算法离线训练模式 — 设计文档

## 目标

在竞争生存游戏中引入遗传算法（GA），让学生能够自动优化其 Creature 的属性配置和行为参数。训练过程独立于游戏运行，不修改现有引擎。

## 方案选择

| 方案 | 描述 | 优缺点 |
|------|------|--------|
| **A. 离线训练（选定）** | 新增 train.py，headless 模拟 + GA 进化 | 教学价值高，不干扰游戏，训练快 |
| B. 游戏内实时进化 | 繁殖时基因变异，自然选择驱动 | 简单但进化慢，学生控制力弱 |
| C. 混合模式 | 离线 + 游戏内结合 | 复杂度高，现阶段不需要 |

## 架构

```
学生编写 EvolvableCreature → train.py 运行 GA → 输出最优参数 → 正常游戏使用
```

新增 3 个文件，不改现有代码：

| 文件 | 职责 |
|------|------|
| `evolvable.py` | EvolvableCreature 基类 + 基因编码/解码 |
| `trainer.py` | 遗传算法引擎（选择/交叉/变异/评估） |
| `train.py` | CLI 入口，配置训练参数并启动 |

## 核心设计

### 1. EvolvableCreature 基类

学生继承此类，声明可优化参数的范围：

```python
class EvolvableCreature(Creature):
    gene_defs = {
        "flee_distance":    (20.0, 120.0),
        "reproduce_ratio":  (2.0,  5.0),
        "prey_chase_speed": (0.5,  1.0),
    }

    def __init__(self, x, y, genes=None):
        super().__init__(x, y, "Evolvable", (170, 70, 255))
        self.genes = genes or {k: random.uniform(*v) for k, v in self.gene_defs.items()}
        ...

    def decide(self, perception):
        # 使用 self.genes 参数做决策
        ...
```

基因编码：`dict[str, float]`，每个 key 对应一个行为参数，值在声明的 `[lo, hi]` 范围内。

**关于属性参数**：`gene_defs` 可以包含 `max_speed`、`max_energy`、`vision_radius`，但 EvolvableCreature 的 `__init__` 必须在设置完基因后调用 `self.clamp()` 确保符合点数预算。超出范围的属性会被自动截断。

### 2. Headless 模拟

复用 World 类，跳过渲染：

```python
def evaluate(genes: dict) -> float:
    world = World(WIDTH, HEIGHT)
    # 放入 N 个使用该 genes 的个体 + 内置对手
    while not world.game_over:
        world.update()
    return fitness_score  # 存活数 * 10 + 总能量
```

### 3. 遗传算法流程

```
初始化: 随机生成 POP_SIZE 个基因组
循环 GENERATIONS 代:
    1. 评估: 每个基因组跑一轮模拟
    2. 选择: 锦标赛选择 (tournament selection)
    3. 交叉: 两点交叉产生子代
    4. 变异: 每个参数以 MUTATION_RATE 概率随机扰动
    5. 精英保留: 最优 ELITE_COUNT 直接进入下一代
输出: 历史最优基因组 → best_params.json
```

### 4. 训练参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| POP_SIZE | 30 | 每代个体数 |
| GENERATIONS | 50 | 进化代数 |
| MUTATION_RATE | 0.15 | 每个参数的变异概率 |
| ELITE_COUNT | 2 | 精英保留数量 |
| TOURNAMENT_SIZE | 5 | 锦标赛选择大小 |

### 5. 适应度函数

```
fitness = 该物种存活数量 * 10 + 该物种总能量 / 100
```

存活数量为主指标，总能量为辅助排序。

**灭绝兜底**：如果该物种在游戏中全灭，用存活时间作为负向指标：
```
if 全灭:
    fitness = 存活 tick 数 / 10000  # 0.0 ~ 1.0，远小于正常适应度
```

### 6. 使用流程

1. 学生继承 EvolvableCreature，定义 gene_defs 和使用 genes 的 decide()
2. 运行 `python train.py --creature creatures/my_evolvable.py --generations 50`
3. 训练完成，最优参数写入 `best_params.json`
4. 用最优参数运行 `python main.py` 观察效果

### 7. 不修改的部分

- world.py、creature.py、main.py 等现有文件不动
- 训练系统是独立旁路工具
- 正常游戏完全不受影响

## 文件结构

```
ant_swarm/
├── evolvable.py          # 新增：EvolvableCreature 基类
├── trainer.py            # 新增：GA 引擎
├── train.py              # 新增：CLI 入口
├── creature.py           # 不改
├── world.py              # 不改
├── main.py               # 不改
├── config.py             # 不改
└── creatures/            # 不改
```

## 输出

- `best_params.json`：最优基因参数，格式示例：
  ```json
  {"flee_distance": 45.3, "reproduce_ratio": 2.8, "prey_chase_speed": 0.92}
  ```
- 控制台输出：每代的最优适应度、平均适应度
- 可选：适应度进化曲线图

**加载最优参数**：学生创建一个继承自 EvolvableCreature 的最终版 Creature，在 `__init__` 中读取 `best_params.json` 作为固定 genes：

```python
import json
class MyOptimizedCreature(EvolvableCreature):
    def __init__(self, x, y):
        with open("best_params.json") as f:
            genes = json.load(f)
        super().__init__(x, y, genes=genes)
```
