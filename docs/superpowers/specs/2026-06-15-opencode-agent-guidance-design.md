# Opencode Agent Guidance Design

## Goal

Add a root-level `agent.md` for opencode. The file should guide opencode to act as a classroom practice coach for `swarm_arena`, helping a student complete one creature-improvement cycle during a single lesson.

The student-facing course material remains in `courseware.html` and is out of scope for this change.

## Audience

The audience is opencode, not the student. The guidance should tell opencode how to conduct the conversation, what questions to ask, what project files to respect, and when to help with code or training commands.

## Conversation Flow

The guidance should require opencode to move through four stages:

1. Observation: ask which creature the student observed and what behavior, weakness, or opportunity they noticed.
2. Technical route choice: help the student choose one of three routes:
   - Rule-based behavior from natural language rules such as "when X is observed, do Y".
   - Parameter optimization with the genetic algorithm.
   - Behavior policy optimization with Q-learning.
3. Optimization and validation: make a small change, run or observe the simulation, and compare results against the original observation.
4. Publication: give the creature a unique name and record the student's own name as author.

## Project Boundaries

The guidance should preserve the teaching package boundaries:

- Prefer modifying or creating only the student's own file under `creatures/`.
- Do not modify core engine files such as `world.py`, `main.py`, or `creature.py` unless the teacher explicitly asks.
- Use existing commands such as `python main.py`, `python train.py --method ga`, and `python train.py --method rl` when appropriate.
- Treat `courseware.html` as student-facing material for a later task.

## Tone

The file should be direct and operational. It should help opencode ask the next useful question rather than dumping a full lecture. It should discourage doing all work for the student: opencode should preserve the student's observation, route choice, creature name, and author identity.

## Success Criteria

- A future opencode session can read `agent.md` and run the classroom cycle without needing this chat.
- The guidance includes all four teacher-requested stages.
- The three technical routes are differentiated clearly.
- Publication requires both a unique creature name and student author attribution.
