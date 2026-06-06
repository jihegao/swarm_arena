import sys
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, FULLSCREEN, SIDEBAR_WIDTH
from world import World
from renderer import Renderer
from creature_loader import load_creatures


def main():
    pygame.init()

    if FULLSCREEN:
        info = pygame.display.Info()
        sw = info.current_w
        sh = info.current_h
        screen = pygame.display.set_mode((sw, sh), pygame.FULLSCREEN)
    else:
        sw = SCREEN_WIDTH
        sh = SCREEN_HEIGHT
        screen = pygame.display.set_mode((sw, sh))

    pygame.display.set_caption("Competitive Survival")

    world_w = sw - SIDEBAR_WIDTH
    world_h = sh

    def create_world():
        creature_classes = load_creatures()
        if not creature_classes:
            print("No creature classes found in creatures/ directory!")
            sys.exit(1)
        w = World(world_w, world_h)
        w.spawn_creatures(creature_classes)
        return w

    world = create_world()
    renderer = Renderer(screen, sidebar_width=SIDEBAR_WIDTH)
    paused = False
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    from creature import Creature
                    from food import Food
                    Creature._next_id = 0
                    Food._next_id = 0
                    world = create_world()
                    paused = False

        if not paused:
            world.update()

        renderer.render(world)
        clock.tick(FPS)


if __name__ == "__main__":
    main()
