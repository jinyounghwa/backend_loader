# 🤖 Agentic Workflow: Claude Code ↔ Gemini CLI Bidirectional Collaboration

> **"Intelligent iteration through structured dialogue between AI agents"**

---

## Overview

This framework enables **true agentic collaboration** between Claude Code and Gemini CLI:

```
Claude Code (implementation)
    ↓ proposes
Gemini CLI (analysis)
    ↓ provides feedback
Claude Code (iterates)
    ↓ proposes improved version
Gemini CLI (reviews)
    ↓ signs off
✅ CONVERGED
```

Instead of one-way analysis, this creates a **feedback loop** where:
1. Claude Code proposes changes
2. Gemini reviews and suggests improvements
3. Claude Code implements based on feedback
4. Loop continues until **convergence**

---

## When to Use

**USE Agentic Workflow for:**
- Complex refactorings with unclear direction
- Architecture decisions needing validation
- Multi-file changes with interdependencies
- Feature implementations requiring iteration
- Performance optimizations needing trade-off analysis

**Skip for:**
- Simple bug fixes
- One-off tool changes
- Straightforward documentation updates

---

## The Workflow

### Phase 1: Propose
Claude Code creates a proposal and saves it for Gemini review.

```bash
./scripts/agentic-loop.sh propose \
  --task "refactor Lambda handler for performance" \
  --file lambda/guardian/handler.py \
  --description "Split monolithic handler into modules using orchestrator pattern"
```

**Output:**
- Proposal ID (timestamp)
- Saved in `~/.agentic/logs/{session}/proposal-{id}/`

### Phase 2: Review
Gemini analyzes the proposal across multiple aspects.

```bash
# Full review
./scripts/agentic-loop.sh review

# Focused review
./scripts/agentic-loop.sh review --aspect code
./scripts/agentic-loop.sh review --aspect arch
./scripts/agentic-loop.sh review --aspect perf
```

**Gemini evaluates:**
- ✅ Strengths (what's good)
- ❌ Issues (what breaks)
- 💡 Suggestions (how to improve)
- ✔️ Verdict (ready? needs work?)

### Phase 3: Iterate
Claude Code implements feedback and loops back to Phase 1.

```bash
# View history and feedback
./scripts/agentic-loop.sh iterate --show-feedback

# Based on feedback, Claude Code:
# 1. Makes changes
# 2. Commits changes
# 3. Proposes again
./scripts/agentic-loop.sh propose --task "improved handler v2" --file handler.py
```

### Phase 4: Converge
When Gemini signs off, declare convergence.

```bash
./scripts/agentic-loop.sh converge
```

**Gemini decides:**
- **READY** ✅ → Proceed to implementation
- **NEEDS_WORK** ⚠️ → Return to iterate phase
- **BLOCKED** 🛑 → Escalate issue

---

## Session Management

### Start a Session
```bash
./scripts/agentic-loop.sh start
```

Creates timestamped session directory: `~/.agentic/logs/20260428-143022/`

### Check Status
```bash
./scripts/agentic-loop.sh status
```

Shows:
- Session ID and location
- Iteration count
- Current status (active/ready/iterating)
- All proposals and reviews

### View History
```bash
./scripts/agentic-loop.sh history
```

Lists last 20 sessions with metadata.

---

## Example: Complete Iteration Cycle

### Scenario: Refactor Handler for Cold Start Optimization

**Step 1: Claude Code proposes**
```bash
./scripts/agentic-loop.sh propose \
  --task "Lambda cold start optimization" \
  --file lambda/guardian/handler.py \
  --description "
  Current issues:
  - Imports inside handler (slow)
  - boto3 clients recreated per invocation
  - No singleton pattern
  
  Proposed fix:
  - Global scope imports
  - AWS client provider singleton
  - Orchestrator pattern for check distribution
  "
```

**Output:**
```
✓ Proposal saved: 1714334400
Session directory: ~/.agentic/logs/20260428-143022
```

**Step 2: Claude Code implements initial version**
```bash
# Implement based on the proposal description
# Files created:
# - aws_client_provider.py (singleton)
# - orchestrator.py (coordinator)
# - handler.py (refactored)
```

**Step 3: Gemini reviews code quality**
```bash
./scripts/agentic-loop.sh review --aspect code
```

**Output (Gemini feedback):**
```
Strengths:
✅ Clean separation of concerns
✅ Singleton pattern correctly implemented
✅ Error handling present

Issues:
❌ Missing type hints in aws_client_provider.py
❌ orchestrator.py hardcodes timeout value
❌ No logging for orchestrator errors

Suggestions:
💡 Add typing.Dict, typing.Optional for clarity
💡 Make timeout configurable via environment
💡 Add orchestrator-level error handler with retry

Ready? NO - Please address issues, then resubmit
```

**Step 4: Claude Code iterates**
```bash
# Fix issues based on feedback:
# 1. Add type hints
# 2. Parametrize timeout
# 3. Add error handling
# 4. Run tests

./scripts/agentic-loop.sh propose \
  --task "Lambda cold start optimization v2" \
  --file lambda/guardian/orchestrator.py \
  --description "Added type hints, made timeout configurable, improved error handling"
```

**Step 5: Gemini reviews architecture**
```bash
./scripts/agentic-loop.sh review --aspect arch
```

**Output (Gemini signs off):**
```
Strengths:
✅ Clean architecture with clear responsibility boundaries
✅ Dependency injection pattern enables testability
✅ Orchestrator coordinates checks efficiently

Issues: (NONE - all resolved)

Suggestions:
💡 Consider adding check priorities for throttling
💡 Document timeout reasoning in code comments

Ready? YES - This is production-ready code. Implement it.
```

**Step 6: Convergence**
```bash
./scripts/agentic-loop.sh converge
```

**Output:**
```
✅ CONVERGED - Ready to implement
Status updated: ready
```

**Step 7: Finalization**
```bash
# Merge changes to main development branch
git add lambda/guardian/{handler,orchestrator,aws_client_provider}.py
git commit -m "feat: Lambda cold start optimization via singleton + orchestrator pattern"
```

---

## Session Directory Structure

```
~/.agentic/
├── logs/
│   └── 20260428-143022/              ← Session (timestamp)
│       ├── metadata.json             ← Session metadata
│       ├── session.log               ← Full transcript
│       ├── proposal-1714334400/      ← Iteration 1
│       │   ├── metadata.json
│       │   ├── description.txt
│       │   └── proposed.py
│       ├── review-1714334450/        ← Review 1
│       │   └── feedback.txt
│       ├── proposal-1714334500/      ← Iteration 2
│       │   ├── metadata.json
│       │   ├── description.txt
│       │   └── proposed.py
│       ├── review-1714334550/        ← Review 2
│       │   └── feedback.txt
│       └── final-review-1714334600/  ← Convergence
│           └── convergence.txt
└── history/                          ← Archive of old sessions
```

---

## Integration with Claude Code

### Within a Claude Code Session

When Claude Code needs agentic review:

```bash
# Claude Code makes changes
# ...

# Propose for review
./scripts/agentic-loop.sh propose \
  --task "Feature: Add DynamoDB GSI for efficient queries" \
  --file terraform/dynamodb.tf

# Get Gemini feedback
./scripts/agentic-loop.sh review --aspect arch

# If feedback suggests changes:
# 1. Implement changes
# 2. Re-propose
# 3. Re-review
# 4. Repeat until converged

# Once satisfied
./scripts/agentic-loop.sh converge

# Then commit to git
git add terraform/dynamodb.tf
git commit -m "feat: DynamoDB GSI optimization (agentic review approved)"
```

### Session Across Multiple Claude Code Sessions

Agentic sessions **persist** across Claude Code sessions:

```
Session 1 (Claude Code):
  ./scripts/agentic-loop.sh propose --task "Phase 1"
  ./scripts/agentic-loop.sh review

Session 2 (Claude Code, next day):
  ./scripts/agentic-loop.sh history              ← Find session ID
  cd ~/.agentic/logs/{session_id}
  ./scripts/agentic-loop.sh iterate --show-feedback
  # Implement based on feedback
  ./scripts/agentic-loop.sh propose --task "Phase 1 v2"
  ./scripts/agentic-loop.sh converge
```

---

## Best Practices

### 1. Clear Task Names
```bash
# ✅ Good
--task "Refactor handler for cold start optimization"

# ❌ Vague
--task "code cleanup"
```

### 2. Detailed Descriptions
```bash
# ✅ Good
--description "
Current issues:
- Imports inside handler (slow)
- No singleton pattern

Proposed fix:
- Global scope imports
- AWS client provider singleton
"

# ❌ Vague
--description "make it faster"
```

### 3. File-Based Proposals
```bash
# ✅ Always include file for code review
./scripts/agentic-loop.sh propose --file actual_implementation.py

# ❌ Don't rely only on description
./scripts/agentic-loop.sh propose --description "here's my code..." (hard to parse)
```

### 4. Focused Reviews
```bash
# ✅ Review specific aspect
./scripts/agentic-loop.sh review --aspect perf

# ❌ Generic reviews may miss details
./scripts/agentic-loop.sh review
```

### 5. Stop Early
```bash
# Know when to stop iterating
# 3-4 iterations is usually enough
# If >5 iterations: step back and reassess approach
```

### 6. Document Convergence
```bash
# When converged, add agentic review badge to commit message
git commit -m "feat: Refactor X (agentic:approved)"
```

---

## Troubleshooting

### "No proposal found"
```bash
# You must propose before reviewing
./scripts/agentic-loop.sh propose --task "..." --file ...
./scripts/agentic-loop.sh review  # Now this works
```

### "Gemini review failed"
```bash
# Check Gemini CLI is working
./scripts/gemini-ask.sh "test prompt" code_review

# Check logs
tail -f ~/.gemini/logs/claude-gemini.log
```

### "Session not found"
```bash
# Sessions expire after 7 days in ~/.agentic/logs/
# List all sessions:
./scripts/agentic-loop.sh history

# Enter specific session:
cd ~/.agentic/logs/{session_id}
./scripts/agentic-loop.sh status
```

---

## Metrics

Track agentic effectiveness:

```bash
# Count total sessions
ls -1d ~/.agentic/logs/*/ | wc -l

# Average iterations per session
for dir in ~/.agentic/logs/*/; do
  jq '.iterations' "$dir/metadata.json"
done | awk '{sum+=$1} END {print "Avg:", sum/NR}'

# Convergence rate
ls -1d ~/.agentic/logs/*/ | while read d; do
  jq '.converged' "$d/metadata.json"
done | grep -c "true" | awk '{print "Converged: " $1 "/" NR}'
```

---

## Future Enhancements

- [ ] **Parallel Reviews**: Get multiple Gemini reviews in one session
- [ ] **A/B Testing**: Compare two proposals side-by-side
- [ ] **Auto-Commit**: Automatically commit converged code
- [ ] **Metrics Dashboard**: Track agentic session statistics
- [ ] **Slack Integration**: Notify on convergence via Slack
- [ ] **Web UI**: Visual session browser and feedback viewer

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `agentic-loop.sh start` | Initialize new session |
| `agentic-loop.sh propose --task "X" --file Y` | Save proposal |
| `agentic-loop.sh review` | Get full Gemini review |
| `agentic-loop.sh review --aspect code` | Review code quality |
| `agentic-loop.sh iterate` | Show iteration history |
| `agentic-loop.sh converge` | Final sign-off |
| `agentic-loop.sh status` | Session state |
| `agentic-loop.sh history` | Past sessions |

---

## Key Insight

**Agentic workflow ≠ One-shot code generation**

Traditional flow:
```
Ask Claude → Get code → Done (hope it works)
```

Agentic flow:
```
Propose → Feedback → Iterate → Improve → Converge → Ship
```

By structuring iteration as a dialogue between two AI agents, we:
- ✅ Catch issues early
- ✅ Improve code quality through iteration
- ✅ Document rationale (why we chose this approach)
- ✅ Maintain audit trail (all versions and feedback)
- ✅ Reduce risk (reviewed before implementation)

---

**Status**: ✅ Ready to use  
**Last Updated**: 2026-04-28  
**Maintenance**: Update after each major iteration
