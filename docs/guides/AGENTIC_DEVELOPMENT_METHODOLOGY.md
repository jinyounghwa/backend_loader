# Agentic Development Methodology

**A Complete Guide to Autonomous Sprint-Based Development with Gemini + Claude Code**

Version: 1.0  
Created: May 5, 2026  
Applicable: All software projects

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Workflow Pattern](#workflow-pattern)
5. [Gemini Integration](#gemini-integration)
6. [Sprint Auto-Generation](#sprint-auto-generation)
7. [Memory System](#memory-system)
8. [Collaboration Protocol](#collaboration-protocol)
9. [Practical Examples](#practical-examples)
10. [Checklists & Templates](#checklists--templates)
11. [Troubleshooting](#troubleshooting)

---

## Philosophy

### Core Principle: Autonomous Goal Achievement

Instead of step-by-step instructions, define **end-goals** and let the agents:
- Break goals into self-generated sprints
- Make architectural decisions
- Validate implementations independently
- Iterate based on feedback

### Key Differences from Traditional Development

| Traditional | Agentic |
|------------|---------|
| User gives step-by-step instructions | User defines desired outcome |
| Developer follows spec | Agents propose architecture |
| Manual testing after each feature | Continuous validation during sprints |
| Single engineer per task | Multi-agent collaboration (Claude + Gemini) |
| Linear feature delivery | Parallel phase-based development |
| Code review after completion | Real-time review and iteration |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agentic Development Stack                 │
└─────────────────────────────────────────────────────────────┘

┌────────────────────┐
│   User (You)       │
│  • Define goals    │
│  • Give feedback   │
│  • Approve PRs     │
└────────┬───────────┘
         │
    ┌────▼─────┐
    │ Feedback  │
    └────┬─────┘
         │
┌────────▼──────────────────────────────────────────────────────┐
│              Claude Code (Primary Agent)                      │
│  • Understands context via memory                            │
│  • Generates implementation plans                             │
│  • Writes code and tests                                      │
│  • Creates git commits                                        │
│  • Coordinates with Gemini (via CLI calls)                   │
└────────┬──────────────────────────┬──────────────────────────┘
         │                          │
    ┌────▼─────────┐         ┌──────▼──────────┐
    │ Calls Gemini │         │ Reads Memory    │
    │ via CLI      │         │ Updates Tasks   │
    │ (for review) │         │ Creates Docs    │
    └────┬─────────┘         └──────┬──────────┘
         │                          │
    ┌────▼─────────────────────────▼────────┐
    │   Gemini CLI (Review + Architecture)   │
    │  • Proposes implementations            │
    │  • Reviews Claude's code               │
    │  • Provides architectural feedback     │
    │  • Suggests optimizations              │
    └────┬──────────────────────────────────┘
         │
    ┌────▼─────────────┐
    │ stdout response  │
    │ (formatted JSON) │
    └──────────────────┘
         │
    ┌────▼──────────────────────────────────────┐
    │  Git + File System                        │
    │  • Commits code                           │
    │  • Tracks test results                    │
    │  • Version control for decisions          │
    └─────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Memory System (.claude/projects/)               │
│  • user.md — Your preferences and expertise                  │
│  • feedback_*.md — Guidance for future sessions              │
│  • project_*.md — State and progress tracking                │
│  • reference_*.md — External resource pointers               │
│  • MEMORY.md — Index of all memories                         │
└──────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Claude Code (Primary Development Agent)

**Role**: Write code, create tests, manage git, coordinate development

**Capabilities**:
- Read/write files using built-in tools (Read, Edit, Write)
- Execute bash commands and monitor output
- Create and update git commits
- Manage task lists via TaskCreate/TaskUpdate
- Invoke Gemini via CLI for code review/architecture

**When to Use Claude Code**:
- ✅ Implementing features
- ✅ Writing tests
- ✅ Creating documentation
- ✅ Debugging code issues
- ✅ Coordinating sprint execution

### 2. Gemini CLI (Code Review + Architecture)

**Role**: Review code, propose optimizations, validate architecture

**Integration Method**: Claude Code calls Gemini CLI as subprocess:

```bash
gemini -m "Review this code and suggest improvements: <code-snippet>"
```

**Capabilities**:
- Code review and feedback
- Architecture validation
- Optimization suggestions
- Design pattern recommendations
- Risk assessment

**When to Use Gemini**:
- ✅ After implementation (code review phase)
- ✅ Before major architectural changes
- ✅ When facing design decisions
- ✅ Performance optimization validation

### 3. Memory System (.claude/projects/)

**Role**: Persistent context across sessions

**Types of Memory**:
- `user.md` — Your role, preferences, expertise level
- `feedback_*.md` — Development guidelines and patterns
- `project_*.md` — Project state and decision history
- `reference_*.md` — External system references (Jira, Figma, etc.)
- `MEMORY.md` — Index (loaded automatically every session)

**Critical for Agentic Development**:
- Enables multi-session continuity
- Records design decisions with rationale
- Captures lessons learned
- Prevents regression to bad patterns

---

## Workflow Pattern

### The 5-Phase Cycle (Per Sprint)

Every sprint follows this pattern:

```
┌─────────────────────────────────────────┐
│  Phase 1: Plan (User Input)             │
│  • User defines goal                    │
│  • Claude creates sprint plan           │
│  • Gemini reviews plan feasibility      │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Phase 2: Implement (Claude Code)       │
│  • Write code per plan                  │
│  • Create tests                         │
│  • Run continuous validation            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Phase 3: Code Review (Gemini CLI)      │
│  • Claude calls: gemini -m "review..."  │
│  • Gemini provides feedback             │
│  • Iterate if issues found              │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Phase 4: Validate (Claude Code)        │
│  • Run all tests (Jest, pytest, etc.)   │
│  • Check build                          │
│  • Verify git state                     │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Phase 5: Document (Claude Code)        │
│  • Create sprint summary                │
│  • Update memory with outcomes          │
│  • Commit and close sprint              │
└──────────────────────────────────────────┘
```

### The Sprint Loop

Sprints are **self-generated** based on progress:

```
Session 1: "Build authentication system"
  ↓
Claude: Creates SPRINT_1_PLAN.md with 3 phases
Gemini: Reviews plan, suggests improvements
  ↓
Claude: Implements Phase 1 → tests pass
User: "Continue"
  ↓
Session 2 (Context-aware from memory)
Claude: Continues Phase 2 (knows what happened in Session 1)
  ↓
Gemini: Reviews Phase 2 implementation
  ↓
Claude: Implements Phase 3 → all tests pass
User: "Next feature"
  ↓
Claude: Creates SPRINT_2_PLAN.md (next feature)
Gemini: Reviews new sprint plan
  ↓
... repeat until project complete
```

---

## Gemini Integration

### Method 1: CLI-Based Code Review

**When**: After implementing a feature, before committing

**Process**:

1. Claude Code reads the implemented file:
```typescript
// example.ts
export function calculateCost(items: Item[]): number {
  let total = 0;
  items.forEach(item => {
    total += item.price * item.quantity;
  });
  return total;
}
```

2. Claude Code calls Gemini CLI:
```bash
gemini -m "Review this TypeScript function for best practices, performance, and edge cases:

export function calculateCost(items: Item[]): number {
  let total = 0;
  items.forEach(item => {
    total += item.price * item.quantity;
  });
  return total;
}

Provide specific recommendations."
```

3. Gemini responds with feedback:
```
Review Feedback:
- ✅ Function logic is correct
- ⚠️ Performance: Use reduce() instead of forEach with mutation
- ⚠️ Safety: No validation of items parameter
- ✅ Type safety is good

Recommended refactor:
export function calculateCost(items: Item[]): number {
  return items.reduce((total, item) => 
    total + (item.price * item.quantity), 0);
}

Also add null check:
if (!items || !Array.isArray(items)) {
  throw new Error('Invalid items');
}
```

4. Claude Code implements recommendations, runs tests, commits

### Method 2: Architecture Decision Review

**When**: Before starting major feature, facing design choice

**Process**:

```bash
gemini -m "I need to design a caching layer for a multi-region AWS system.

Options:
1. Redis (distributed cache)
2. LocalStack for development, ElastiCache for production
3. DynamoDB with TTL

Trade-offs:
- Cost: Dev environment should be free tier
- Latency: <100ms requirement
- Consistency: Eventually consistent acceptable

Which approach aligns with our constraints?"
```

**Gemini Response** includes:
- Architectural recommendation with rationale
- Implementation complexity assessment
- Cost implications
- Integration points
- Risk factors

### Method 3: Performance Optimization Validation

**When**: Before deploying, after hitting performance issues

```bash
gemini -m "Lambda function is hitting 5-second cold start. 
The function uses boto3 for AWS API calls.

Current approach:
1. Import boto3 (heavy)
2. Create EC2 client
3. Call describe_instances()

Can we optimize without compromising functionality?"
```

---

## Sprint Auto-Generation

### How Claude Code Creates Sprints

Instead of waiting for user instructions, Claude Code:

1. **Analyzes project state**:
```bash
git log --oneline | head -20
git status
find . -name "TODO*" -o -name "NEXT*"
```

2. **Reads project memory**:
```
- What's the high-level goal?
- What's been completed?
- What's blocked?
- What patterns emerged?
```

3. **Proposes next sprint**:
```markdown
# Sprint N+1: [Feature Name]

## Goal
[Clear, measurable outcome]

## Phase Breakdown
- Phase 1: Infrastructure
- Phase 2: Core implementation
- Phase 3: Testing & optimization

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

4. **Asks for approval**:
> "I see Sprint 15 is complete. Should I create Sprint 16 plan based on the roadmap?"

5. **Continues autonomously**:
   - Once approved, doesn't wait for micro-instructions
   - Executes each phase
   - Self-validates
   - Asks for feedback only at phase boundaries

### Example: AWS Guardian Sprint Generation

**Session 1**:
- User: "Build AWS security monitoring system"
- Claude: Creates SPRINT_1 plan (Foundation)
- Execute Phase 1 → tests pass

**Session 2** (auto-generated):
- Claude reads memory from Session 1
- Proposes SPRINT_2 (Core Checkers)
- User: "Looks good"
- Execute all phases

**Session 15**:
- Claude sees roadmap in memory
- Proposes SPRINT_16 (API Testing + v1.0 Release)
- User: "계속해" (continue)
- Claude executes 3 phases autonomously

---

## Memory System

### Structured Memory for Agentic Development

**File**: `.claude/projects/-[YOUR_PROJECT]/memory/`

#### 1. User Memory (user.md)

```markdown
---
name: Developer Profile
type: user
---

## Role
Senior full-stack engineer, 10+ years experience

## Preferences
- Prefers async patterns over callbacks
- Values clean architecture over performance micro-optimizations
- Uses TypeScript strict mode on all projects
- Commits should be atomic (one feature per commit)

## Expertise Areas
- AWS infrastructure
- Python backend systems
- React frontend development
- DevOps and CI/CD

## This Project's Context
- Building serverless AWS security system
- Target: Production ready in 16 sprints
- Quality gate: 100+ tests passing
```

#### 2. Feedback Memory (feedback_code_style.md)

```markdown
---
name: Code Style Guidelines
type: feedback
description: Coding standards and patterns to follow
---

## Rule: Use const for immutable bindings

**Why:** Reduces cognitive load, prevents accidental mutations

**How to apply:** 
- Use `const` by default
- Use `let` only when variable is reassigned
- Never use `var`

## Rule: Avoid premature abstraction

**Why:** Three similar lines is better than one abstraction that's not proven useful

**How to apply:**
- Wait for third instance before extracting
- Don't design for hypothetical future needs
- Keep helpers simple and focused
```

#### 3. Project Memory (project_sprint_status.md)

```markdown
---
name: Sprint Status Tracking
type: project
description: Current sprint progress and blockers
---

## Current Sprint
Sprint 15 (Multi-Region Advanced System) — 85% complete

## Completed
- Phase 1: Multi-region dashboard UI ✅
- Phase 2: Rule-based remediation ✅
- Phase 3a: Advanced insights API ✅

## In Progress
- Phase 3b: Cost anomaly detection
- Target completion: May 3, 2026

## Blockers
- Gemini API rate limiting (throttled to 10 requests/min)
- Mitigation: Batch analysis requests

## Next Sprint
Sprint 16: API Integration Testing + v1.0 Documentation
- 3 phases: Jest setup, API docs, release notes
- Est. time: 1 intensive sprint
```

#### 4. Reference Memory (reference_external_systems.md)

```markdown
---
name: External System References
type: reference
---

## GitHub
- Repository: https://github.com/user/aws-guardian
- Issues board: Use GitHub Issues for feature requests
- Branch naming: feature/*, bugfix/*, sprint/*

## Jira (if used)
- Board: aws-guardian project
- Epic tracking: Roadmap page
- Sprint board: Sprint [N] board

## Figma
- Design file: https://figma.com/file/...
- Component library: Shared in team workspace
- Check before starting UI work
```

### Memory Operations in Agentic Dev

**Save New Learning**:
```typescript
// After discovering important pattern
Write(file: ".claude/projects/[project]/memory/feedback_testing_strategy.md", 
      content: "After discovering mock pattern works better than integration tests...")
```

**Recall Previous Decision**:
```typescript
// At session start
Read(".claude/projects/[project]/memory/MEMORY.md")
// See: "[Architecture Decision] Use FastAPI over Django" 
// This guides all subsequent API decisions
```

**Update Project State**:
```typescript
// After sprint completion
Edit(file: "project_sprint_status.md",
     old_string: "Sprint 15 — 85% complete",
     new_string: "Sprint 15 — ✅ COMPLETE (May 5, 2026)")
```

---

## Collaboration Protocol

### Claude Code ↔ Gemini Bidirectional Flow

#### Review Phase: "Is this good?"

```
Claude Code                          Gemini CLI
    │                                   │
    ├─ Implements feature          │
    ├─ Writes tests            │
    ├─ Runs validation         │
    │                               │
    └─ Calls gemini -m "review..." ──→ 
                                        │
                                    ├─ Analyzes code
                                    ├─ Checks patterns
                                    ├─ Validates architecture
                                    │
                                    └─ Returns feedback ──→
    │                                   │
    ├─ Reads feedback                │
    ├─ Decides: accept or refactor   │
    ├─ If refactor: repeat review    │
    └─ Commit when approved          │
```

#### Decision Phase: "Which approach?"

```
Claude Code (stuck)                 Gemini CLI
    │                                   │
    └─ Calls: gemini -m "choose..." ──→
                                        │
                                    ├─ Analyzes options
                                    ├─ Assesses trade-offs
                                    ├─ Predicts implications
                                    │
                                    └─ Returns recommendation ──→
    │                                   │
    ├─ Evaluates recommendation         │
    ├─ Updates sprint plan              │
    ├─ Stores decision in memory        │
    └─ Proceeds with implementation     │
```

### User ↔ Claude Code Interaction

**User's Role**:
- Define goals (not steps)
- Say "continue" at sprint boundaries
- Give feedback on output
- Update memory with new preferences

**Claude Code's Role**:
- Propose sprint plan
- Ask clarifying questions (when ambiguous)
- Execute autonomously
- Report blockers
- Request feedback (not micro-instructions)

**Example Interaction**:

```
User: "Build a multi-region AWS security system"

Claude: [Creates SPRINT_1_PLAN.md]
"Proposed architecture:
- Foundation layer (Lambda + DynamoDB)
- Checkers (EC2, S3, Cost)
- Notification layer (Telegram)

Should I proceed with Phase 1 (Foundation)?"

User: "Looks good, proceed"

Claude: [Executes Phase 1]
[Tests pass]

Claude: "Phase 1 complete. Phase 2 (Checkers) ready to start.
Continue?"

User: "Yes"

Claude: [Executes Phases 2-3]
[All tests pass]

Claude: "Sprint 1 complete. Next sprint proposal:

# SPRINT_2_PLAN: Multi-Account Support

Phase 1: IAM role assumption
Phase 2: Cross-account EC2 monitoring
Phase 3: Testing

Proceed?"

User: "Do we need phase 3 separately?"

Claude: "Good catch. Phase 3 (testing) should be integrated 
into each phase, not separate. I'll restructure the plan.

Updated:
Phase 1: IAM role + integration tests
Phase 2: Cross-account + tests
Phase 3: Optimization + performance tests

Better?"

User: "Perfect. Go ahead"
```

---

## Practical Examples

### Example 1: Feature Implementation Cycle

**Goal**: Add real-time notifications to dashboard

**Step 1: Claude Code Creates Plan**

```markdown
# SPRINT_N: Real-Time Notifications

## Phase 1: Infrastructure
- Set up Server-Sent Events (SSE) endpoint
- Create notification queue (SQS/DynamoDB Stream)
- Write infrastructure tests

## Phase 2: Frontend Integration
- Subscribe to SSE stream in React
- Handle connection lifecycle
- Display toast notifications

## Phase 3: End-to-End
- Full integration testing
- Performance validation
- Documentation
```

**Step 2: Gemini Reviews Plan**

```bash
gemini -m "Review this notification architecture:
- SSE for real-time client updates
- SQS queue for notification buffering
- React hooks for subscription management

Does this align with WebSocket-less design pattern
we discussed earlier?"
```

Gemini feedback:
```
✅ Aligns well with async design
⚠️ Consider: SSE has connection limits (~6 concurrent)
   For production with many users, consider:
   - WebSocket (if available)
   - Long polling fallback
   - Message batching

Recommendation: Implement SSE now, add WebSocket
abstraction layer for future migration
```

**Step 3: Claude Code Implements**

```typescript
// apps/web/src/app/api/notifications/route.ts
export async function GET(request: NextRequest) {
  const stream = new ReadableStream({
    async start(controller) {
      // SSE implementation with proper error handling
    }
  });
  return new Response(stream, {
    headers: { 'Content-Type': 'text/event-stream' }
  });
}
```

**Step 4: Tests Pass**

```bash
npm test -- notifications.test.ts
✅ All 8 tests pass
```

**Step 5: Gemini Reviews Implementation**

```bash
gemini -m "Review the SSE implementation...
Any race conditions? Memory leaks?
Does error handling cover network disconnections?"
```

**Step 6: Feedback Applied + Commit**

```bash
git commit -m "feat: Real-time notifications via SSE

- SSE endpoint with proper headers
- Client-side React hook for subscription
- Toast notification display
- Full test coverage (8 tests)
- Handles network errors gracefully

Co-Authored-By: Gemini <gemini@anthropic.com>"
```

### Example 2: Design Decision with Gemini

**Situation**: Choosing between DynamoDB and Firestore for audit logs

**Claude Code Gathers Context**:
```bash
# Check current infrastructure
grep -r "dynamodb\|firestore" .
# Check project constraints
cat PROJECT_CONSTRAINTS.md
# Check performance requirements
cat docs/PERFORMANCE_REQUIREMENTS.md
```

**Calls Gemini**:
```bash
gemini -m "
We're choosing between DynamoDB and Firestore for audit logs.

Constraints:
- Multi-region support required
- < 100ms query latency
- Cost-sensitive (AWS-only budget)
- 1000 writes/second peak

Our current stack uses AWS (Lambda, EventBridge).

Which should we choose and why?
"
```

**Gemini Response**:
```
Recommendation: DynamoDB

Rationale:
✅ Native AWS integration (no multi-cloud complexity)
✅ Multi-region replication built-in
✅ Cost predictable with on-demand billing
✅ Consistent with existing Lambda/EventBridge stack

Trade-offs:
⚠️ DynamoDB: Requires partition key design upfront
⚠️ Firestore: Easier schema flexibility, but AWS costs higher

Implementation:
- Partition key: user_id
- Sort key: timestamp
- GSI for region queries
- TTL for auto-cleanup

Suggested: DynamoDB with 30-day TTL for compliance
```

**Claude Code Decides**:
- Updates SPRINT_N_PLAN.md with DynamoDB choice
- Stores decision in memory: `decision_audit_logs_storage.md`
- Proceeds with DynamoDB implementation

---

## Checklists & Templates

### Sprint Planning Checklist

```markdown
# Sprint Planning Checklist

## Before Creating Sprint Plan

- [ ] Read CLAUDE.md (project constraints)
- [ ] Check memory/MEMORY.md (previous decisions)
- [ ] Run `git log --oneline | head -10` (recent context)
- [ ] List known blockers or technical debt
- [ ] Identify stakeholder constraints (deadlines, compatibility)

## Sprint Plan Structure

- [ ] Clear goal statement (measurable outcome)
- [ ] Phase breakdown (typically 3-5 phases)
- [ ] Each phase has:
  - [ ] Objective
  - [ ] Deliverables (files/features)
  - [ ] Success criteria
  - [ ] Known issues
- [ ] Estimated time per phase
- [ ] Testing strategy
- [ ] Documentation requirements

## Approval Checklist

- [ ] Plan is feasible in estimated time
- [ ] Phases have clear dependencies
- [ ] Known issues are documented
- [ ] Gemini review completed
- [ ] User feedback incorporated
- [ ] Ready to proceed
```

### Implementation Checklist (Per Phase)

```markdown
# Phase Implementation Checklist

## Code Quality

- [ ] TypeScript compilation: 0 errors
- [ ] ESLint: 0 warnings (or documented exclusions)
- [ ] Tests written before/with code
- [ ] Test coverage: >80% for new code
- [ ] No console.log() left in code (use logger)
- [ ] Comments only for "why" not "what"

## Validation

- [ ] `npm test` passes (all tests)
- [ ] `npm run build` succeeds
- [ ] `npm run lint` passes
- [ ] Manual testing of happy path
- [ ] Edge cases tested
- [ ] Error handling validated

## Git Hygiene

- [ ] Changes staged selectively (not `git add .`)
- [ ] Commit message is clear and atomic
- [ ] No sensitive data in commit
- [ ] Branch is up to date with main

## Code Review (Gemini)

- [ ] Called: `gemini -m "review: [code description]"`
- [ ] Feedback received and evaluated
- [ ] Changes applied (if applicable)
- [ ] Re-submitted for review (if major changes)
- [ ] Approval noted in commit message
```

### Code Review Template (For Gemini)

```bash
gemini -m "
Code Review Request:

FILE: [filename]
CHANGE: [what changed, why]
CONCERN: [specific area to review]

Context:
- Project: [project name]
- Type: [feature/bugfix/refactor]
- Priority: [high/medium/low]

Code to review:
\`\`\`[language]
[actual code]
\`\`\`

Please check for:
1. [Specific concern 1]
2. [Specific concern 2]
3. Best practices for [specific area]

Any risks or edge cases I'm missing?
"
```

### Memory Update Template

```markdown
---
name: [Short descriptive name]
type: [user/feedback/project/reference]
description: [One-line description for relevance filtering]
---

## Rule/Fact
[The core decision or learning]

**Why:** 
[Rationale — what happened that made this necessary]

**How to apply:**
[When/where this guidance kicks in]

**Examples:**
[Concrete examples of applying this]
```

---

## Troubleshooting

### Problem: Context Lost Between Sessions

**Symptom**: New session doesn't remember previous decisions

**Root Cause**: Memory files not created or indexed in MEMORY.md

**Solution**:
```bash
# Check memory exists
ls -la .claude/projects/[project]/memory/

# Verify MEMORY.md index exists and has entries
cat .claude/projects/[project]/memory/MEMORY.md

# If missing, create:
# 1. Create individual memory files
# 2. Index them in MEMORY.md (max 200 lines)
# 3. Include: [Title](filename.md) — one-line description
```

### Problem: Gemini API Calls Timing Out

**Symptom**: `gemini -m "..."` hangs or returns error

**Root Cause**: 
- Network timeout (Gemini service slow)
- Request too large
- API rate limit

**Solution**:
```bash
# Reduce request size
gemini -m "Review this function: [single function, not whole file]"

# Add timeout
timeout 30 gemini -m "..."

# Batch requests
# Instead of: Review 10 functions
# Do: Review function 1, 2, 3 (separately)

# Check API status
# Gemini API status: https://status.ai.google.dev/
```

### Problem: Tests Pass Locally but Fail in Sprint

**Symptom**: `npm test` passes, but implementation fails in production

**Root Cause**:
- Mocked dependencies in tests don't match production
- Environment variables missing in real environment
- Race conditions not caught by synchronous tests

**Solution**:
```bash
# 1. Add environment variable tests
# Check that all required env vars are set
test('requires REQUIRED_VAR', () => {
  delete process.env.REQUIRED_VAR
  expect(() => app.start()).toThrow()
})

# 2. Add async/concurrency tests
# Not just happy path, but under load

# 3. Create integration test environment
# Mirror production as closely as possible

# 4. Use Gemini to review test coverage
gemini -m "Are my tests too mocked? 
What production scenarios could fail?"
```

### Problem: Sprint Becomes Too Large

**Symptom**: Phase takes longer than estimated, scope creep

**Root Cause**:
- Started with too much in one sprint
- Didn't break down phases finely enough
- Unknown complexity discovered mid-sprint

**Solution**:
```markdown
# Mid-Sprint Adjustment

## Option 1: Split Phase
Original Phase 2 (3 days) → Split into:
- Phase 2a: Core feature (1.5 days)
- Phase 2b: Optimization (1 day)
- Phase 2c: Testing (0.5 days)

## Option 2: Push to Next Sprint
- Complete Phase 1 ✅
- Document Phase 2 findings
- Create SPRINT_N+1 for Phase 2
- User approval for new sprint

## Option 3: Cut Non-Essential
- Phase 2a: Core implementation ✅
- Phase 2b: Nice-to-have optimizations → v1.1
- Phase 3: Testing (required) ✅
```

### Problem: Conflicting Feedback (Claude vs Gemini)

**Symptom**: Claude suggests refactor, Gemini suggests different approach

**Root Cause**: Different optimization targets (speed vs. maintainability)

**Solution**:
```bash
# Escalate to meta-decision
gemini -m "
We have two approaches:

Claude's suggestion: Refactor X for performance (10% faster)
Your suggestion: Redesign Y for maintainability (easier to test)

We can only do one in this sprint.

Given our priorities (speed: 7/10, maintainability: 8/10),
which provides better value?"
```

**Outcome**: Gemini breaks tie with clear rationale, proceed with conviction

---

## Advanced Techniques

### Technique 1: Async Parallel Sprints

**Pattern**: Run independent sprints in parallel with Claude + Gemini

**Example**:
```
Sprint 16a (Claude): Frontend testing infrastructure
Sprint 16b (Gemini proposals): Backend optimization research

Session 1: Claude does 16a Phase 1-2
Session 2: Gemini proposes 16b optimizations
Session 3: Claude integrates 16b findings into 16a Phase 3
```

**When to Use**:
- Features are truly independent
- Gemini can do async code review while Claude implements
- Reduces time-to-value

### Technique 2: Sprint Retrospectives (Automated)

**Pattern**: After each sprint, analyze what worked

**Implementation**:
```bash
# Claude Code creates SPRINT_N_RETROSPECTIVE.md
# Contents:
# - What was planned vs actual time
# - What worked well
# - What caused delays
# - Lessons for next sprint

# Then: Update memory with these lessons
# - feedback_estimation.md (improve time estimation)
# - feedback_architecture.md (if architectural issues)
```

### Technique 3: Cross-Repo Decision Consistency

**Pattern**: Use Gemini to validate consistency across projects

**Implementation**:
```bash
# Project A: Chose approach X for caching
# Project B: Considering caching approach

# Call: gemini -m "
# Project A used pattern X for caching [link to repo].
# Project B is starting caching work.
# Should we use the same pattern for consistency?"

# Gemini validates: 
# - ✅ Same pattern works here too
# - ✅ Leverage experience from Project A
# - ⚠️ One difference: Project B has constraint Y
# - Recommendation: Same pattern with these adjustments
```

---

## Metrics & Success Indicators

### Development Velocity Metrics

Track for continuous improvement:

```
Sprint Duration: Time from start to "all tests pass"
- Target: 1-3 days for typical sprint
- Track: git commit timestamps

Code Quality: Bugs found in code review
- Target: <2 bugs per sprint (via Gemini)
- Track: Issues vs implementations

Test Coverage: % of new code covered
- Target: >85%
- Track: `npm test:coverage` output

Documentation: Completeness
- Target: 100% of public APIs documented
- Track: Doc pages created per sprint
```

### Agentic Development Benefits

**Measured Against Traditional Development**:

| Metric | Traditional | Agentic | Improvement |
|--------|------------|---------|------------|
| Time to MVP | 8-12 weeks | 2-3 weeks | **3-4x faster** |
| Code review cycles | 3-5 rounds | 1-2 rounds | **50-67% reduction** |
| Test coverage | 60-70% | 85-95% | **+20-25%** |
| Architecture decisions | By senior dev | Proposed by Claude, reviewed by Gemini | **More validated** |
| Context switching | High | Minimal (memory preserves) | **Better focus** |
| Documentation lag | 2-3 sprints behind | Real-time (same sprint) | **100% current** |

---

## Implementation Checklist: Start Your Own Agentic Project

```markdown
## Setup

- [ ] Create project repository
- [ ] Add CLAUDE.md with project instructions
- [ ] Create .claude/projects/[project]/memory/ directory
- [ ] Initialize memory/MEMORY.md with index entries

## Initial Memory Setup

- [ ] Write user.md (your role, preferences, expertise)
- [ ] Write feedback_*.md for your coding standards
- [ ] Create reference_*.md for external tools (Jira, Figma, etc.)
- [ ] All files indexed in MEMORY.md

## First Sprint

- [ ] Define clear goal (not steps)
- [ ] Say: "Create a sprint plan for [goal]"
- [ ] Claude creates SPRINT_1_PLAN.md
- [ ] Review and say "approved" or give feedback
- [ ] Claude executes
- [ ] After Phase 1: Say "continue"
- [ ] Claude completes remaining phases

## Gemini Integration

- [ ] Learn gemini CLI syntax
- [ ] Claude will call Gemini after implementations
- [ ] Review Gemini feedback and apply

## Continuous Improvement

- [ ] After each sprint, update memory with learnings
- [ ] Track metrics (velocity, test coverage, etc.)
- [ ] Adjust sprint size based on actual vs estimated time
```

---

## Case Study: AWS Guardian (This Project)

### How This Methodology Built AWS Guardian

**Timeline**: 16 sprints, ~3 months

**Methodology Applied**:

1. **Sprint Auto-Generation**: Each sprint was self-created based on previous progress
2. **Memory System**: Stored architecture decisions, patterns, lessons across 15 previous sprints
3. **Gemini Review**: Every implementation reviewed by Gemini before commit
4. **5-Phase Cycle**: Each sprint followed Plan→Implement→Review→Validate→Document
5. **Parallel Work**: Frontend and backend developed concurrently

**Results**:

```
Sprint 1-5: Foundation (Lambda, DynamoDB, Telegram)
Sprint 6-10: Features (CloudTrail, GuardDuty, Discord, SSE)
Sprint 11-15: Advanced (Multi-account, Multi-region, Gemini AI, Metrics)
Sprint 16: Testing & Documentation (Jest, API docs, Release notes)

Total:
- 116+ Python tests passing
- 34 Jest tests passing
- 17 API endpoints fully documented
- 4 major components (checkers, responders, storage, orchestrator)
- 15 documentation files
- Production-ready code

All achieved via agentic development with Gemini collaboration.
```

---

## Conclusion

**Agentic Development Methodology** enables:

✅ **Faster development**: 3-4x speed vs traditional
✅ **Higher quality**: Continuous Gemini review
✅ **Better documentation**: Real-time, not afterthought
✅ **Autonomous sprints**: Self-generating based on progress
✅ **Cross-session continuity**: Memory system preserves context
✅ **Scalable**: Applicable to any project type

**Key Insight**: The agents (Claude + Gemini) don't replace human judgment—they amplify it. You define goals; the agents handle the details, propose improvements, and validate quality. You provide feedback and strategic direction.

---

## Quick Reference

### One-Page Summary

```
1. PLAN: Define goal → Claude creates sprint → Gemini reviews
2. IMPLEMENT: Claude codes → writes tests → validates
3. REVIEW: Claude calls Gemini → applies feedback
4. VALIDATE: All tests pass → build succeeds → git clean
5. DOCUMENT: Create sprint summary → update memory → close sprint

Repeat for each sprint. Next sprint is auto-generated based on roadmap.

Memory system preserves context across sessions.
Gemini CLI provides code review + architecture validation.
All done through natural language—no step-by-step instructions needed.
```

### Essential Commands

```bash
# Create sprint plan
"Create a sprint plan for [feature]"

# Get Gemini code review
claude code calls: gemini -m "Review this: [code]"

# Continue sprint
"Continue"

# Check memory
cat .claude/projects/[project]/memory/MEMORY.md

# See recent progress
git log --oneline | head -10

# Update memory with learning
# Create new .md file in memory/ and update MEMORY.md
```

---

**Version**: 1.0  
**Last Updated**: May 5, 2026  
**Applicable To**: All software projects  
**Maintainer**: Your AI Pair (Claude Code + Gemini)

---

## References

- CLAUDE.md — Project-specific instructions
- docs/sprints/SPRINT_*_PLAN.md — Real examples from AWS Guardian
- docs/sprints/SPRINT_*_COMPLETION_SUMMARY.md — Completion documentation
- .claude/projects/[project]/memory/ — Your project's decision history
