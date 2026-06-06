# LLM Creature Design Spec

## Overview

Add a new creature type, `LLMCreature`, that can connect to an OpenAI-compatible LLM endpoint and periodically adjust its behavior rules during a simulation. The simulation already calls each creature's `decide(perception)` method synchronously every tick, so the LLM must not sit in the per-frame critical path. The creature will keep a local rule engine for every-frame decisions and use the LLM only to update a small set of strategy parameters at a fixed interval.

If no LLM credentials are configured, if the network call fails, or if the model returns invalid data, `LLMCreature` remains playable with deterministic fallback rules.

## Goals

- Add one auto-loadable creature class in `creatures/llm_creature.py`.
- Let the creature periodically adjust behavior rules based on summarized perception and internal state.
- Keep every-frame `decide()` fast and synchronous.
- Support OpenAI-compatible configuration through environment variables.
- Make failures safe: no API key, timeout, malformed JSON, or unavailable dependency must not crash the game.
- Add focused tests for configuration, strategy parsing, interval behavior, and fallback decisions.

## Non-Goals

- Do not call an LLM on every tick.
- Do not add a global async event loop to `World`.
- Do not change the `Creature`, `Perception`, or `Action` public APIs.
- Do not require users to install or configure an LLM provider before running the game.
- Do not train, fine-tune, or persist long-term learned policy state.

## Runtime Configuration

`LLMCreature` reads environment variables at construction time:

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_CREATURE_API_KEY` | unset | Enables remote LLM calls when present. |
| `LLM_CREATURE_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL. |
| `LLM_CREATURE_MODEL` | `gpt-4.1-mini` | Chat/completions model name. |
| `LLM_CREATURE_INTERVAL` | `240` | Minimum ticks between strategy update attempts per creature. |
| `LLM_CREATURE_TIMEOUT` | `2.0` | Network timeout in seconds. |
| `LLM_CREATURE_ENABLED` | `1` | Set to `0`, `false`, or `no` to force local-only behavior. |

The implementation should use only the Python standard library for HTTP requests unless the project later adds an official dependency manager. This keeps the creature loadable in the current repository, which has no dependency manifest.

## Strategy Model

The LLM does not return Python code. It returns a constrained JSON object that updates numeric weights and a high-level mode:

```json
{
  "mode": "forage",
  "food_weight": 1.0,
  "prey_weight": 0.8,
  "threat_margin": 1.15,
  "reproduce_ratio": 2.2,
  "wander_speed": 0.35
}
```

Accepted fields:

| Field | Type | Allowed Range | Meaning |
|-------|------|---------------|---------|
| `mode` | string | `forage`, `hunt`, `flee`, `reproduce`, `balanced` | Biases priority when multiple actions are possible. |
| `food_weight` | float | `0.0` to `3.0` | Relative preference for food targets. |
| `prey_weight` | float | `0.0` to `3.0` | Relative preference for smaller creature targets. |
| `threat_margin` | float | `1.0` to `2.0` | Treat creatures above `self_size * threat_margin` as threats. |
| `reproduce_ratio` | float | `2.0` to `4.0` | Energy ratio needed before requesting reproduction. |
| `wander_speed` | float | `0.1` to `1.0` | Fraction of max speed used while wandering. |

Missing or invalid fields keep their previous values. Out-of-range numeric values are clamped. Unknown fields are ignored.

Default local strategy:

```python
{
    "mode": "balanced",
    "food_weight": 1.0,
    "prey_weight": 1.0,
    "threat_margin": 1.1,
    "reproduce_ratio": 2.3,
    "wander_speed": 0.4,
}
```

## Local Decision Flow

Every `decide(perception)` call follows the same fast local flow:

1. Increment an internal decision counter.
2. If the update interval has elapsed, attempt one LLM strategy refresh. The refresh must have a short timeout and must swallow expected network/parse errors.
3. Identify threats: nearby creatures whose size exceeds `self_size * threat_margin`.
4. If threats are close, flee directly away from the nearest threat.
5. If energy exceeds `reproduce_ratio * self_max_energy` and local danger is low, return `reproduce=True`.
6. Score smaller creatures as prey using distance and `prey_weight`.
7. Score visible food using distance, amount, and `food_weight`.
8. Choose prey or food according to strategy mode and score.
9. If nothing useful is visible, wander with a deterministic turn pattern and `wander_speed`.

Mode effects:

| Mode | Effect |
|------|--------|
| `forage` | Prefer food unless prey score is clearly better. |
| `hunt` | Prefer prey unless food score is clearly better. |
| `flee` | Increase threat sensitivity and avoid conflict. |
| `reproduce` | Reproduce as soon as safe and eligible. |
| `balanced` | Pick the best normalized target score. |

## LLM Prompt Contract

The prompt should send compact, non-sensitive simulation state rather than raw full perception lists. Example fields:

- Current energy ratio.
- Current position as normalized `x_pct` and `y_pct`.
- Counts of nearby food, prey, larger threats, and neutral creatures.
- Nearest food distance and best food amount.
- Nearest prey distance and prey energy estimate.
- Nearest threat distance.
- Previous strategy.

The system instruction should require strict JSON only, no markdown, and no code. The user instruction should ask for a strategy update for the next interval, not a per-frame action.

## HTTP Integration

Use OpenAI-compatible `POST /chat/completions`:

```json
{
  "model": "gpt-4.1-mini",
  "messages": [
    {"role": "system", "content": "...strict JSON strategy..."},
    {"role": "user", "content": "{...summary...}"}
  ],
  "temperature": 0.2,
  "max_tokens": 160
}
```

The parser reads `choices[0].message.content` and decodes it as JSON. If providers wrap JSON in whitespace, that is accepted. Markdown fences are not required and should be treated as invalid unless implementation later adds a small sanitizer.

## Failure Handling

Expected failures must keep the current strategy and return a normal local action:

- LLM disabled by environment.
- Missing API key.
- HTTP timeout or non-2xx response.
- Invalid JSON response.
- JSON with wrong types.
- Any exception raised by URL opening or response parsing.

The creature may store a short `last_llm_error` string for debugging, but errors should not be printed every tick. If logging is added, it should be rate-limited.

## Creature Profile

The creature type should be `"LLMCreature"` and have an obvious distinct color, for example cyan `(80, 220, 230)`. Its base attributes can be set inside `__init__` to avoid changing `config.py`:

```python
self.max_speed = 2.4
self.max_energy = 85.0
self.vision_radius = 210.0
```

These values fit the existing point-budget model after `World.spawn_creatures()` calls `clamp()`.

## File Changes

Planned files:

```text
creatures/llm_creature.py
tests/test_llm_creature.py
```

Optional documentation update after implementation:

```text
README.md
```

No `World` changes are required because `creature_loader.py` already discovers concrete `Creature` subclasses in `creatures/`.

## Testing Plan

Use standard-library `unittest` so the repo does not need a new dependency manifest.

Focused tests:

- Loading `LLMCreature` without environment variables creates a valid creature and returns an `Action`.
- Strategy parser accepts valid JSON and updates allowed fields.
- Strategy parser clamps out-of-range values and ignores unknown fields.
- Invalid JSON leaves the previous strategy unchanged.
- Interval logic does not attempt an LLM refresh before `LLM_CREATURE_INTERVAL`.
- A fake LLM client can force a strategy update and influence local decisions.
- Network or client exceptions are swallowed and fallback action remains valid.

Verification commands:

```bash
python -m unittest tests.test_llm_creature
python -m unittest discover
```

## Open Questions

- Whether to add `LLMCreature` profile/color entries to `config.py` for HUD consistency, or keep all creature-specific settings in `creatures/llm_creature.py`.
- Whether to expose the active strategy in the renderer sidebar later. This is out of scope for the first implementation because the current renderer does not display per-creature internal state.

