import sys
from world import World
from creature_loader import load_creatures
from creature import Creature
from food import Food


def main():
    Creature._next_id = 0
    Food._next_id = 0

    creature_classes = load_creatures()
    if not creature_classes:
        print("No creature classes found!")
        sys.exit(1)

    names = [c.__name__ for c in creature_classes]
    print(f"参赛生物: {', '.join(names)}")
    print()

    world = World(1660, 1080)
    world.spawn_creatures(creature_classes)

    initial_counts = world.alive_count_by_type()
    print(f"初始数量: {dict(sorted(initial_counts.items()))}")

    while not world.game_over:
        world.update()

    print()
    print(f"游戏结束于 Tick: {world.tick}")
    print()

    final_counts = world.alive_count_by_type()
    print(f"最终存活数量: {dict(sorted(final_counts.items()))}")
    print()

    if world.winner:
        winner = world.winner
        print(f"🏆 获胜种群: {winner.creature_type}")
        print(f"   个体: {winner.name}")
        print(f"   能量: {winner.energy:.1f}")
        print(f"   体型: {winner.size:.1f}")
    else:
        print("没有获胜者")

    ranking = world.population_ranking()
    if ranking:
        print()
        print("排名 (按种群数量):")
        for i, (ctype, count) in enumerate(ranking, 1):
            print(f"  {i}. {ctype}: {count}")

    top = world.top_creatures(limit=5)
    if top:
        print()
        print("最强个体:")
        for name, ctype, energy, size in top:
            print(f"  {name} ({ctype}): 能量={energy:.0f}, 体型={size:.1f}")


if __name__ == "__main__":
    main()
