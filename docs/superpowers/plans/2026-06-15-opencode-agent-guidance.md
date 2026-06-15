# Opencode Agent Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a root-level `agent.md` that instructs opencode to coach students through one creature-improvement cycle.

**Architecture:** This is a documentation-only change. The new `agent.md` is an opencode-facing instruction file that preserves project boundaries and points to the existing creature, GA, and RL workflows.

**Tech Stack:** Markdown, Python project commands already present in this repository.

---

### Task 1: Add Opencode Classroom Coach Guidance

**Files:**
- Create: `agent.md`
- Verify: `docs/superpowers/specs/2026-06-15-opencode-agent-guidance-design.md`

- [x] **Step 1: Create `agent.md`**

Write a Markdown file with these sections:

- Purpose and role: opencode is a classroom practice coach.
- Scope boundaries: do not edit `courseware.html` in this task, prefer student creature files under `creatures/`, avoid core engine edits.
- Four-stage lesson cycle: observation, technical route choice, optimization/validation, publication.
- Technical route guidance: rule-based behavior, GA parameter optimization, Q-learning behavior policy optimization.
- Conversation discipline: ask one useful question at a time, keep student ownership of observations, naming, and author identity.
- Verification and publication checklist.

- [x] **Step 2: Verify the file content**

Run:

```bash
sed -n '1,260p' agent.md
```

Expected: The output includes the four requested stages, all three technical routes, and publication with creature name plus student author.

- [x] **Step 3: Check worktree scope**

Run:

```bash
git status --short
```

Expected: The new `agent.md` appears, along with this plan/spec and unrelated pre-existing user changes. No core engine file is modified by this task.
