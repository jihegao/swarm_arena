# 竞争生存游戏 (Competitive Survival)

在这个游戏中，你将编写一个 **Creature（生物）** 的 AI，放入 2D 世界中与其他生物竞争。世界中随机出现食物，生物需要抢食物、吃掉比自己小的对手、繁殖后代。**5000 tick 后，存活数量最多的物种获胜。**

## AI 助手使用要求

如果使用 opencode 或其他 AI 助手带学生完成课堂实践，开始前必须先读取并遵循根目录的 `agent.md`。AI 助手应按其中的课堂教练流程引导学生观察、选择技术路线、优化验证和发布署名，而不是直接替学生完成一个生物。

## 快速开始

### 运行游戏

```bash
python main.py
```

### 运行训练实验

当前已实现两种训练方法，可以独立运行，互不作为前置条件：

```bash
# GA：训练学生自己写的 EvolvableCreature 参数
python train.py --method ga --creature creatures/apex.py --generations 20

# RL：用离散 Q-learning 学习高层动作策略
python train.py --method rl --episodes 200 --output best_policy.json
```

GA 输出 `best_params.json`，RL 输出 `best_policy.json`。GEP 规则生成仍在设计文档阶段，当前 `train.py` 暂不支持 `--method gep`。

### 操作

| 按键 | 功能 |
|------|------|
| SPACE | 暂停 / 继续 |
| R | 重新开始 |
| ESC | 退出 |

---

## 你的任务

在 `creatures/` 目录下新建一个 `.py` 文件，定义一个继承自 `Creature` 的类，实现 `decide()` 方法。重启游戏后你的生物会自动加入竞争。

### 最小模板

把以下代码保存为 `creatures/my_creature.py`：

```python
from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class MyCreature(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "MyCreature", (255, 128, 0))

    def decide(self, perception: Perception) -> Action:
        return Action(perception.self_angle, self.max_speed)
```

这段代码创建了一个只会直线前进的橙色生物。你可以在此基础上逐步改进。

> **注意**：文件头部的 `sys.path` 那两行是必须的，确保能正确导入 `creature` 模块。
>
> 建议让类名和 `super().__init__()` 里的类型名保持一致，例如类名 `MyCreature` 对应 `"MyCreature"`。游戏现在也能处理二者不同的情况，但一致命名更方便在排行榜和日志里排查。

---

## 核心 API：decide()

每一帧，游戏引擎调用你的生物的 `decide(perception)` 方法。你根据感知信息返回一个 `Action`。

```python
def decide(self, perception: Perception) -> Action:
    ...
```

### Perception — 你能看到什么

| 字段 | 类型 | 说明 |
|------|------|------|
| `self_x` | `float` | 你当前的 X 坐标 |
| `self_y` | `float` | 你当前的 Y 坐标 |
| `self_angle` | `float` | 你当前的朝向（弧度，0 = 右，π/2 = 下） |
| `self_size` | `float` | 你当前的体型大小（随能量动态变化） |
| `self_energy` | `float` | 你当前的能量值 |
| `self_max_energy` | `float` | 你的初始能量值 |
| `world_width` | `int` | 世界宽度 |
| `world_height` | `int` | 世界高度 |
| `nearby_food` | `list[FoodSpot]` | 视野范围内的食物列表 |
| `nearby_creatures` | `list[CreatureSpot]` | 视野范围内的其他生物列表 |

#### FoodSpot

| 字段 | 类型 | 说明 |
|------|------|------|
| `x` | `float` | 食物 X 坐标 |
| `y` | `float` | 食物 Y 坐标 |
| `amount` | `float` | 食物的能量值 |
| `size` | `float` | 食物的大小 |

#### CreatureSpot

| 字段 | 类型 | 说明 |
|------|------|------|
| `x` | `float` | 对手 X 坐标 |
| `y` | `float` | 对手 Y 坐标 |
| `creature_type` | `str` | 对手的类型名（如 "Hunter", "MyCreature"） |
| `creature_id` | `int` | 对手的唯一 ID |
| `size` | `float` | 对手的体型大小 |
| `energy_pct` | `float` | 对手的能量占其初始能量的百分比 |

> 你只能看到 `vision_radius` 范围内的东西，范围外的世界不可见。

### Action — 你要做什么

每帧返回一个 `Action` 对象：

```python
Action(
    target_angle,       # float: 这一帧要朝向的角度（弧度）
    target_speed,       # float: 这一帧的移动速度（不超过 max_speed）
    attack_target_id,   # int | None: 要追击的生物 ID（仅用于标记意图）
    reproduce,          # bool: 是否繁殖（默认 False）
)
```

- **移动**：每帧必须指定 `target_angle` 和 `target_speed`。设 `0` 表示停止。
- **攻击**：碰到比自己**小**的生物会自动吃掉，无需主动声明攻击。`attack_target_id` 用于标记追击意图。
- **繁殖**：设 `reproduce=True` 且满足条件时，会在附近生成一个同类型子代。

如果你的 `decide()` 抛出异常，或者返回的不是合法 `Action`，游戏不会崩溃；该生物本帧会停止移动，终端会打印一条 warning。非法角度和速度也会被清洗：角度必须是有限数字，速度会限制在 `0 ~ max_speed`。

---

## 属性系统

你的生物在构造函数中通过 `creature_type` 关联属性配置。你也可以在 `__init__` 中手动覆盖：

```python
class MyCreature(Creature):
    def __init__(self, x, y):
        super().__init__(x, y, "MyCreature", (255, 128, 0))
        self.max_speed = 2.5
        self.vision_radius = 180.0
```

### 可配置属性

| 属性 | 默认值 | 最小值 | 最大值 | 说明 |
|------|--------|--------|--------|------|
| `max_speed` | 1.0 | 0.5 | 4.0 | 最大移动速度（像素/帧） |
| `max_energy` | 100.0 | 30.0 | 200.0 | 初始能量值 |
| `vision_radius` | 20.0 | 50.0 | 300.0 | 视野半径（像素） |
| `color` | 灰色 | — | — | 显示颜色 `(R, G, B)` |

> 超出范围的属性值会在生成时自动截断到边界内。

### 点数系统

所有生物共享一个 **总预算上限 = 1.5**。每个属性根据其值归一化到 0~1，三项属性的归一化值之和不能超过 1.5。

```
归一化值 = (属性值 - 最小值) / (最大值 - 最小值)
总点数   = 各属性归一化值之和
```

如果总点数超过 1.5，所有属性会**等比例缩小**。你无法全项拉满——**必须取舍**。

内置生物的点数分配：

| 类型 | 速度 | 能量 | 视野 | 总计 |
|------|------|------|------|------|
| Hunter | 0.57 | 0.29 | 0.60 | 1.46 |
| Grazer | 0.29 | 0.41 | 0.40 | 1.10 |
| PackHunter | 0.49 | 0.29 | 0.40 | 1.18 |
| Scavenger | 0.86 | 0.18 | 0.44 | 1.48 |

### 属性权衡

- **高速度 + 大视野** → 快速找到食物，但能量消耗大
- **高能量** → 初始体型大，能吃更多食物和小生物，但也更容易被更大的生物盯上
- **速度最关键** → 能吃到食物就能长大，长大就能吃别人，是滚雪球的核心

---

## 吃人规则（大吃小）

**没有攻击力和防御力**。战斗规则很简单：

1. **大吃小**：当一个生物碰到比自己**体型小**的生物时，直接吃掉
2. **获得全部能量**：吃掉对手后获得对方剩余的全部能量
3. **碰撞范围**：两个生物的中心距离 < `max((eater.size + target.size) × 0.6, eater.size - target.size)`，避免小生物贴边时明明被大生物覆盖却吃不到
4. **10 帧冷却**：吃掉一个生物后需等 10 帧才能再吃

### 体型公式

```
size = 6 × sqrt(energy / 100)
```

| 能量 | 体型 |
|------|------|
| 50 | 4.2 |
| 100 | 6.0 |
| 200 | 8.5 |
| 500 | 13.4 |
| 1000 | 19.0 |
| 5000 | 42.4 |

能量越高体型越大，能吃掉更多的生物，但也意味着**更大的碰撞范围**（更容易被更大的生物碰到）。

---

## 繁殖机制

每个生物可以自行决定何时繁殖。在你的 `decide()` 中返回 `Action(..., reproduce=True)` 即可。

### 繁殖条件

| 条件 | 值 |
|------|------|
| 能量阈值 | ≥ max_energy × 2.0 |
| 繁殖消耗 | max_energy × 0.5 |
| 繁殖冷却 | 120 帧 |
| 子代出现位置 | 母体周围随机 20px |
| 世界生物上限 | 600 |

### 繁殖流程

1. 生物决定繁殖（`reproduce=True`）
2. 检查能量是否 ≥ max_energy × 2
3. 检查繁殖冷却是否为 0
4. 扣除 max_energy × 0.5 的能量
5. 在附近生成一个同类型子代，初始能量 = 消耗的能量
6. 进入 120 帧冷却
7. 得 100 分

### 繁殖策略

- **早生 vs 晚生**：能量刚到阈值就生，子代小但数量多；攒更多能量再生，子代更大更安全
- **时机选择**：周围没有天敌时繁殖更安全；战斗激烈时繁殖可能送人头
- **种群控制**：世界有 600 生物上限，满了就无法繁殖

---

## 能量规则

能量是生存的核心。能量降到 0 你就死了。

### 能量消耗（每帧）

| 来源 | 公式 |
|------|------|
| 基础衰减 | 0.1 × (当前体型 / 6) |
| 移动消耗 | 额外 0.08 × (速度 / max_speed) × (体型 / 6) |

**体型越大，能量消耗越高**。这是一个关键的平衡机制——长到巨大并不总是好事，你需要不断进食来维持体型。

### 能量恢复

| 来源 | 效果 |
|------|------|
| 吃食物 | + 食物的 amount（8~100） |
| 吃掉对手 | + 对手剩余的全部能量 |
| 繁殖子代 | - max_energy × 0.5 |

### 吃食物条件

- 你与食物的距离 < 你的体型 + 3

---

## 胜利条件

游戏在 **5000 tick** 时结束（或更早，如果只剩一种生物存活）。获胜者为：

1. 如果只剩一种生物 → 该物种中能量最高的个体获胜
2. 如果到时间限制 → **存活数量最多的物种**中能量最高的个体获胜

---

## 计分规则

排行榜按分数从高到低排序：

| 事件 | 得分 |
|------|------|
| 吃掉对手 | + 对手的 max_energy |
| 吃食物 | + 食物的 amount（取整） |
| 繁殖后代 | + 100 |
| 最终获胜 | + 500 |

---

## 内置对手分析

### Hunter（红色 🔴）

| 属性 | 值 |
|------|------|
| max_speed | 2.5 |
| max_energy | 80 |
| vision_radius | 200 |

**行为**：追猎视野内最弱的生物（优先低血量），能量充足时繁殖。低能量时转而找食物。

**弱点**：初始能量低（80），前期容易被更大的生物吃掉。

### Grazer（绿色 🟢）

| 属性 | 值 |
|------|------|
| max_speed | 1.5 |
| max_energy | 100 |
| vision_radius | 150 |

**行为**：以吃食物为主，敌人接近到 35px 时逃跑。能量超过 2.5 倍初始值时繁殖。

**弱点**：速度最慢，前期容易被追上吃掉。

### PackHunter（蓝色 🔵）

| 属性 | 值 |
|------|------|
| max_speed | 2.2 |
| max_energy | 80 |
| vision_radius | 150 |

**行为**：寻找同伴，聚在一起时主动围猎敌人。附近同类少于 5 个且能量充足时繁殖。落单时逃跑。

**弱点**：初始能量低，早期容易被各个击破。

### Scavenger（黄色 🟡）

| 属性 | 值 |
|------|------|
| max_speed | 3.5 |
| max_energy | 60 |
| vision_radius | 160 |

**行为**：全场最快，抢到食物就跑。能量超过 3 倍初始值时繁殖。从不主动攻击。

**弱点**：初始能量最低（60），前期体型最小，谁都能吃它。

---

## 策略提示

1. **滚雪球型**：前期专注吃食物快速长大，体型大了就能吃别人，越吃越大。

2. **速繁殖型**：尽快攒够能量繁殖，靠数量优势取胜。但子代小容易被吃。

3. **猎人型**：高速度 + 大视野，专门追杀比自己小的生物。食物只是辅助。

4. **伏击型**：躲在食物附近，等对手来吃食物时（它也变大了可能比你小）突然吃掉。

5. **种群策略**：设计繁殖时机，让同族在后期占据数量优势赢得胜利。

6. **能量管理**：体型越大消耗越高。没有食物来源时，适当"减肥"（停止进食让能量下降）可能比维持巨大体型更持久。

7. **针对性克制**：Scavenger 在 80px 内逃跑，Grazer 在 35px 内逃跑。在逃跑触发距离外接近它们。

---

## 提交方式

将你的 `.py` 文件放入 `creatures/` 目录即可。满足：

1. 文件位于 `creatures/` 目录下（不要以 `_` 开头）
2. 定义一个继承 `Creature` 的类
3. 实现了 `decide(self, perception: Perception) -> Action` 方法
4. 构造函数签名为 `__init__(self, x: float, y: float)`

游戏启动时会自动扫描 `creatures/` 目录，加载所有合法的 Creature 子类。每个类会生成相同数量的初始实例。

如果一个 `.py` 文件里定义了多个合法 Creature 子类，它们都会加入比赛，终端会打印 warning。课堂提交时建议一个文件只保留一个参赛类，避免旧实验类意外参赛。

---

## 常用代码片段

### 计算朝向某点的角度

```python
angle = math.atan2(target_y - perception.self_y, target_x - perception.self_x)
```

### 计算两点距离

```python
dist = math.hypot(target_x - perception.self_x, target_y - perception.self_y)
```

### 找最近的实体

```python
nearest = min(
    perception.nearby_creatures,
    key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y),
)
```

### 远离某个方向（逃跑）

```python
flee_angle = math.atan2(
    perception.self_y - enemy.y,
    perception.self_x - enemy.x,
)
```

### 判断是否可以繁殖

```python
can_reproduce = perception.self_energy >= perception.self_max_energy * 2.0
```

### 随机漫步（无目标时）

```python
angle = perception.self_angle + math.sin(perception.self_x * 0.01) * 0.3
return Action(angle, self.max_speed * 0.5)
```

---

## 完整示例

```python
from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class Survivor(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "Survivor", (255, 128, 0))
        self.max_speed = 2.2
        self.max_energy = 100.0
        self.energy = 100.0
        self.vision_radius = 160.0

    def decide(self, perception: Perception) -> Action:
        energy_pct = perception.self_energy / perception.self_max_energy

        if energy_pct >= 2.5:
            return Action(perception.self_angle, 0, reproduce=True)

        if perception.nearby_creatures:
            smaller = [c for c in perception.nearby_creatures if c.size < perception.self_size]
            if smaller:
                target = min(smaller,
                    key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y))
                angle = math.atan2(target.y - perception.self_y, target.x - perception.self_x)
                return Action(angle, self.max_speed)

            bigger = [c for c in perception.nearby_creatures if c.size > perception.self_size]
            if bigger:
                nearest_big = min(bigger,
                    key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y))
                dist = math.hypot(nearest_big.x - perception.self_x, nearest_big.y - perception.self_y)
                if dist < 60:
                    flee = math.atan2(perception.self_y - nearest_big.y, perception.self_x - nearest_big.x)
                    return Action(flee, self.max_speed)

        if perception.nearby_food:
            food = min(perception.nearby_food,
                key=lambda f: math.hypot(f.x - perception.self_x, f.y - perception.self_y))
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed * 0.7)

        angle = perception.self_angle + math.sin(perception.self_x * 0.015) * 0.2
        return Action(angle, self.max_speed * 0.4)
```

这个 Survivor 的策略：
- **能量充足时繁殖**，扩大种群
- **追杀比自己小的对手**，不吃亏
- **远离比自己大的对手**，保命优先
- **空闲时**找食物或随机漫步

---

祝你好运，让你的物种统治这个世界！
