# Sprint 23 Plan - Type Safety & Documentation

**Project**: AWS Guardian - Lambda Backend  
**Planned Date**: Next Session After Sprint 22  
**Duration**: Single Session (3-4 hours)  
**Status**: 📋 PLANNED

---

## Context

Sprint 22 successfully completed code quality refactoring and SAM template creation. Current status:
- ✅ 42/42 core tests passing (stable baseline)
- ✅ All 6 checkers have consolidated error handling
- ✅ All public methods have comprehensive docstrings
- ✅ SAM template validates successfully
- ❌ Type hints incomplete (15+ issues identified)
- ❌ Documentation minimal (setup, architecture, API)

**Sprint 23 Focus**: Type safety through mypy + comprehensive documentation

---

## Objectives

### Primary (MUST DO)
- [ ] Install mypy and configure for project
- [ ] Create py.typed marker file
- [ ] Fix all mypy errors in core code
- [ ] Create CONTRIBUTING.md with setup & testing guide
- [ ] Document async/sync dual pattern in ARCHITECTURE.md
- [ ] Verify 42+ core tests still passing

### Secondary (SHOULD DO)
- [ ] Set up pre-commit hooks for mypy
- [ ] Add type hints to all private methods
- [ ] Document cache TTL strategy
- [ ] Create API.md with endpoint documentation

---

## Phase 1: Type Safety Setup (1-1.5 hours)

### 1.1 Install mypy and Dependencies

Create `requirements-dev.txt`:
```
mypy==1.13.0
types-boto3[dynamodb,s3,ec2,iam,cloudtrail,ce,ssm,guardduty]==1.0.2
types-python-dateutil==2.8.20.14
```

Command:
```bash
source venv/bin/activate
pip install -r requirements-dev.txt
```

**Effort**: 5 minutes

### 1.2 Create mypy Configuration

Create `mypy.ini`:
```ini
[mypy]
python_version = 3.12
warn_return_any = True
check_untyped_defs = True
no_implicit_optional = True
```

**Effort**: 10 minutes

### 1.3 Create py.typed Marker

```bash
touch lambda/guardian/py.typed
```

**Effort**: 2 minutes

### 1.4 Run mypy Baseline

```bash
mypy lambda/guardian --ignore-missing-imports
```

**Expected**: 15-25 type errors (baseline)

**Effort**: 5 minutes

---

## Phase 2: Fix Type Hint Issues (1.5-2 hours)

Priority order:
1. lambda/guardian/handler.py (~5 issues)
2. lambda/guardian/aws_client_provider.py (~3 issues)
3. lambda/guardian/checkers/base.py (~2 issues)
4. lambda/guardian/parallel_orchestrator.py (~3 issues)
5. lambda/guardian/checkers/*.py (~4 issues each)

**Effort**: 1.5 hours

---

## Phase 3: Documentation (1.5-2 hours)

### 3.1 Create CONTRIBUTING.md

Sections:
- Getting Started (setup, venv)
- Running Tests (core, with coverage, all)
- Code Style (black, isort, mypy, pylint)
- Adding New Checkers
- Mock Detection Pattern

**Effort**: 45 minutes

### 3.2 Update ARCHITECTURE.md

Sections:
- System Overview (flow diagram)
- Async/Sync Dual Implementation
- Mock Detection Explanation
- Cache Strategy
- Error Handling
- Checker Details (all 6)

**Effort**: 45 minutes

---

## Phase 4: Testing & Verification (30 minutes)

### 4.1 Run Type Checking

```bash
mypy lambda/guardian
# Expected: 0 errors
```

### 4.2 Run Core Tests

```bash
python3 -m pytest tests/lambda -k "not harness and not performance" -v
# Expected: 42 passed
```

### 4.3 Documentation Check

```bash
ls -la CONTRIBUTING.md docs/ARCHITECTURE.md
wc -l CONTRIBUTING.md docs/ARCHITECTURE.md
```

---

## Success Criteria

### Must Have
- ✓ mypy installed and configured
- ✓ 0 mypy errors in lambda/guardian/
- ✓ py.typed marker file created
- ✓ CONTRIBUTING.md complete (200+ lines)
- ✓ ARCHITECTURE.md complete (300+ lines)
- ✓ 42+ core tests still passing

### Should Have
- ✓ Pre-commit hooks configured
- ✓ All private methods typed

---

## Time Estimate

| Task | Estimate |
|------|----------|
| Phase 1: mypy setup | 20 min |
| Phase 2: Fix type hints | 90 min |
| Phase 3: Documentation | 90 min |
| Phase 4: Testing | 30 min |
| **TOTAL** | **~230 minutes (3.8 hours)** |

---

**Prepared**: May 17, 2026  
**Status**: Ready for Implementation  
**Expected Duration**: 3-4 hours  
**Next Sprint**: Sprint 24 - Performance Baseline & Optimization
