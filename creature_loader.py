from __future__ import annotations
import importlib
import importlib.util
import os
import sys
from creature import Creature


def load_creatures(package_dir: str | None = None) -> list[type[Creature]]:
    if package_dir is None:
        package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'creatures')

    if not os.path.isdir(package_dir):
        return []

    results: list[type[Creature]] = []

    parent_dir = os.path.dirname(package_dir)
    parent_name = os.path.basename(parent_dir)
    pkg_name = 'creatures'

    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    for filename in sorted(os.listdir(package_dir)):
        if filename.startswith('_') or not filename.endswith('.py'):
            continue
        module_name = f"{parent_name}.{pkg_name}.{filename[:-3]}"
        try:
            spec = importlib.util.spec_from_file_location(
                module_name, os.path.join(package_dir, filename)
            )
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"Warning: failed to load {filename}: {e}")
            continue

        module_creatures: list[type[Creature]] = []
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, Creature)
                    and attr is not Creature
                    and not getattr(attr, '__abstractmethods__', None)):
                module_creatures.append(attr)

        if len(module_creatures) > 1:
            names = ", ".join(cls.__name__ for cls in module_creatures)
            print(
                f"Warning: {filename} exports multiple Creature classes ({names}); "
                "all will join the arena.",
                flush=True,
            )

        results.extend(module_creatures)

    return results
