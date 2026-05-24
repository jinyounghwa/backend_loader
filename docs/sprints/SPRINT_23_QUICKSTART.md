# Sprint 23 Quickstart Guide

**Last Updated**: May 8, 2026  
**Sprint**: Sprint 23 (v1.3 Implementation)  
**Duration**: 3-4 sessions (~12 hours)  
**Status**: Ready to start

---

## 🚀 5-Minute Startup

```bash
# 1. Verify current state (30 seconds)
cd /Users/younghwa.jin/Documents/backend_loader
git status  # Should be clean
git log --oneline | head -3

# 2. Check test baseline (1 minute)
python3 -m pytest tests/test_*.py --co -q | wc -l  # Should be ~116
PYTHONPATH="./lambda:./tests/lambda" python3 -m pytest tests/lambda/test_handler_harness.py -q  # Quick sanity check

# 3. Verify v1.2 release (1 minute)
git tag | grep v1.2
git log --oneline | grep "Sprint 22"

# 4. Review Sprint 23 plan (2-3 minutes)
cat docs/sprints/SPRINT_23_PLAN.md | head -100
```

**Expected Output**:
```
✅ Git status clean
✅ 116 unit tests available
✅ v1.2 tag exists
✅ Test baseline passing
```

---

## 📋 Phase Checklist

### Phase 1: Architecture Design (Session 1)

**Time**: ~2 hours

**Deliverables**:
- [ ] Redis integration architecture finalized
- [ ] aioboto3 migration strategy documented
- [ ] Multi-account support design complete
- [ ] Create `docs/sprints/SPRINT_23_DESIGN.md`

**Key Files to Read**:
```bash
cat docs/sprints/SPRINT_23_PLAN.md | grep -A 50 "Phase 1:"
```

**Commands to Run**:
```bash
# Verify Redis is available (if using AWS)
aws elasticache describe-cache-clusters

# Check aioboto3 is in requirements (will add during implementation)
grep aioboto3 lambda/requirements.txt  # Should be empty now

# Check Python version
python3 --version  # Should be 3.12.x
```

---

### Phase 2: Core Implementation (Sessions 2-3)

**Time**: ~6 hours

**Sub-Phases**:

#### 2.1 Redis Integration (1.5 hours)

**Steps**:
1. Create `lambda/guardian/cache/base.py` - Abstract interface
2. Create `lambda/guardian/cache/redis.py` - Redis backend
3. Update `lambda/guardian/cache/__init__.py` - Factory pattern
4. Test with mock Redis

**Test Command**:
```bash
python3 -m pytest tests/test_redis_cache.py -v
```

#### 2.2 aioboto3 Migration (2 hours)

**Steps**:
1. Add aioboto3 to `lambda/requirements.txt`
2. Update `lambda/guardian/aws_client_provider.py`
3. Update all 6 checkers to use async context managers
4. Update orchestrator for true async

**Checkers to Update** (in order):
```
1. CostChecker (simplest)
2. S3Checker
3. EC2Checker
4. CloudTrailChecker
5. IAMChecker
6. GuardDutyChecker
```

**Test Command**:
```bash
python3 -m pytest tests/test_aioboto3_migration.py -v
PYTHONPATH="./lambda:./tests/lambda" python3 -m pytest tests/lambda/ -q
```

#### 2.3 Multi-Account Support (2 hours)

**Steps**:
1. Create Terraform for cross-account IAM
2. Update orchestrator to handle `account_ids` parameter
3. Implement role assumption logic
4. Implement results aggregation

**Test Command**:
```bash
python3 -m pytest tests/test_multi_account.py -v
```

---

### Phase 3: Testing & Verification (Session 4)

**Time**: ~2 hours

**Milestones**:
- [ ] All 194+ unit tests passing
- [ ] 16 new cache tests passing
- [ ] 6 new aioboto3 tests passing
- [ ] 8 new multi-account tests passing
- [ ] Performance benchmarks showing improvements
- [ ] No regressions in existing tests

**Test Commands**:
```bash
# Run full test suite
python3 -m pytest tests/test_*.py -v  # Should be 100/100

# Run Lambda tests
PYTHONPATH="./lambda:./tests/lambda" python3 -m pytest tests/lambda/ -v  # Should be 80+/82

# Run performance tests
python3 -m pytest tests/test_performance_v1.3.py -v

# Check for type errors
python3 -m mypy lambda/guardian/ --ignore-missing-imports
```

**Expected Results**:
```
test_redis_cache.py: 6 passed
test_aioboto3_migration.py: 6 passed
test_multi_account.py: 8 passed
test_performance_v1.3.py: 8 passed
tests/test_*.py: 116 passed (no regressions)
tests/lambda/: 77+ passed
============ 201+ passed in X.XXs ============
```

---

### Phase 4: Documentation & Release (Part of Session 4)

**Time**: ~1 hour

**Deliverables**:
- [ ] `docs/sprints/SPRINT_23_DESIGN.md` - Architecture document
- [ ] `docs/REDIS_SETUP.md` - Redis configuration guide
- [ ] `docs/MULTI_ACCOUNT_GUIDE.md` - Multi-account setup
- [ ] `docs/AIOBOTO3_MIGRATION.md` - Migration reference
- [ ] `docs/sprints/SPRINT_23_COMPLETION.md` - Final report

**Command to Create Report Template**:
```bash
cat > docs/sprints/SPRINT_23_COMPLETION.md << 'EOF'
# Sprint 23 Completion Report

**Status**: ✅ COMPLETE
**Date**: 2026-05-XX
**Version**: v1.3
**Duration**: 3-4 sessions

## Deliverables
- ✅ Redis integration complete
- ✅ aioboto3 migration complete
- ✅ Multi-account support complete

## Test Results
- Total tests: 201+
- Passed: 201+ (100%)
- Performance: Improved by 2-3x

## Next: Sprint 24 (v1.3 Release)
EOF
```

---

## 🔧 Development Environment

### Required Tools
```bash
# Verify versions
python3 --version          # Should be 3.12.x
docker --version           # Should be 20.10.x+
docker-compose --version   # Should be 1.29.x+
aws --version              # Should be 2.x
git --version              # Should be 2.x

# Check Python packages
pip list | grep -E "pytest|aioboto3|boto3|redis"
```

### Environment Variables (for local testing)

```bash
# Create .env.local for local development
cat > .env.local << 'EOF'
# Redis (local testing)
REDIS_URL=redis://localhost:6379

# AWS (local testing with LocalStack)
AWS_ENV=localstack
AWS_ENDPOINT_URL=http://localhost:4566

# Cache
CACHE_BACKEND=redis

# Logging
LOG_LEVEL=DEBUG
EOF

# Load environment
export $(cat .env.local | xargs)
```

---

## 📊 Progress Tracking

### By Phase

```markdown
# Phase 1: Design (2 hours)
- [ ] Redis architecture finalized
- [ ] aioboto3 migration strategy documented
- [ ] Multi-account design documented
- Session: ___

# Phase 2: Implementation (6 hours)
## 2.1 Redis (1.5 hours)
- [ ] base.py created
- [ ] redis.py created
- [ ] __init__.py updated
- [ ] Tests passing (6/6)
- Session: ___

## 2.2 aioboto3 (2 hours)
- [ ] requirements.txt updated
- [ ] aws_client_provider.py updated
- [ ] CostChecker updated
- [ ] S3Checker updated
- [ ] EC2Checker updated
- [ ] CloudTrailChecker updated
- [ ] IAMChecker updated
- [ ] GuardDutyChecker updated
- [ ] Tests passing (6/6)
- Session: ___

## 2.3 Multi-Account (2 hours)
- [ ] Cross-account IAM setup
- [ ] orchestrator.py updated
- [ ] Role assumption implemented
- [ ] Results aggregation implemented
- [ ] Tests passing (8/8)
- Session: ___

# Phase 3: Testing (2 hours)
- [ ] All 194+ tests passing
- [ ] Performance tests showing improvements
- [ ] No regressions detected
- [ ] Type checking clean
- Session: ___

# Phase 4: Documentation (1 hour)
- [ ] Design document created
- [ ] Setup guides created
- [ ] Completion report created
- [ ] All documentation reviewed
- Session: ___
```

---

## 🎯 Key Metrics to Track

### Performance Baselines

**Before (v1.2)**:
- Cold start: ~2300ms
- Single region check: ~300ms
- Multi-region (4x): ~3000ms
- Cache hit: ~50ms
- Test suite: 116/116 (100%)

**Target (v1.3)**:
- Cold start: <2500ms (no regression)
- Single region check: <300ms (same)
- Multi-region (4x): <3000ms (same)
- Redis cache hit: <10ms (5x faster)
- aioboto3 checks: <1000ms per check (same or faster)
- Multi-account checks: <5s for 3 accounts (true parallelization)
- Test suite: 201+/201+ (100%)

### Coverage

**Code Coverage** (should maintain 85%+):
```bash
python3 -m pytest tests/ --cov=lambda/guardian --cov-report=term-missing
```

**Test Categories**:
```
Unit Tests:           116 tests
Cache Tests:          16 tests (new)
aioboto3 Tests:       6 tests (new)
Multi-Account Tests:  8 tests (new)
Lambda Tests:         77 tests
Lambda Perf Tests:    3 tests
Deprecation Tests:    5 tests
Cache Perf Tests:     8 tests (new)
Total:               201+ tests
```

---

## 🐛 Troubleshooting

### Redis Connection Issues

```bash
# Check if Redis is running (local testing)
docker run -d -p 6379:6379 redis:7.0

# Check connection
redis-cli ping  # Should return PONG

# Test from Python
python3 << 'EOF'
import redis
r = redis.Redis(host='localhost', port=6379)
print(r.ping())  # Should print True
EOF
```

### aioboto3 Import Errors

```bash
# Install aioboto3
pip install aioboto3

# Verify installation
python3 -c "import aioboto3; print(aioboto3.__version__)"

# If import fails, fall back to boto3 is fine
python3 -c "import boto3; print('boto3 fallback OK')"
```

### Test Failures

```bash
# Run with verbose output
python3 -m pytest tests/test_redis_cache.py -vv -s

# Check test dependencies
pip list | grep -E "pytest|mock|asyncio"

# View test logs
tail -100 /tmp/pytest.log
```

---

## 📚 Reference Docs

**In This Repo**:
- `docs/sprints/SPRINT_23_PLAN.md` - Detailed plan
- `CLAUDE.md` - Project rules
- `v1.2_RELEASE_NOTES.md` - Previous release
- `docs/DEPLOYMENT_GUIDE_v1.2.md` - Deployment procedures

**External References**:
- Redis docs: https://redis.io/documentation
- aioboto3: https://github.com/terrycain/aioboto3
- Python asyncio: https://docs.python.org/3/library/asyncio.html

---

## 🎓 Learning Goals

By end of Sprint 23, understand:
1. **Redis caching** - Distributed cache patterns
2. **Async Python** - asyncio, context managers, gather
3. **AWS IAM** - Cross-account role assumption
4. **Design patterns** - Factory pattern, fallback strategy
5. **Performance optimization** - Parallelization benefits

---

## ✅ Session Sign-Off Template

```markdown
## Session X Sign-Off

**Date**: 2026-05-XX
**Duration**: 2 hours
**Phase**: [Design/Implementation/Testing/Documentation]

### Completed
- [ ] [Task 1]
- [ ] [Task 2]

### Tests Passed
- [X] 116 unit tests
- [X] 77 Lambda tests
- [ ] [New tests if any]

### Blockers
None

### Next Session
[Describe what's next]
```

---

## 🚨 Critical Checklist

Do NOT skip these before each commit:

```bash
# 1. Run all tests
python3 -m pytest tests/test_*.py tests/lambda/ -q

# 2. Check for syntax errors
python3 -m py_compile lambda/guardian/**/*.py

# 3. Verify no breaking changes
git diff --stat

# 4. Review commit message
git log --oneline | head -3

# 5. Push and verify
git push origin main
git log --oneline -1
```

---

## 📞 Quick Help

**Need to review plan?**
```bash
cat docs/sprints/SPRINT_23_PLAN.md | less
```

**Need to check current progress?**
```bash
git log --oneline --grep="Sprint 23" 
```

**Need to see what tests are available?**
```bash
python3 -m pytest tests/ --collect-only -q | head -50
```

**Need to run a specific test?**
```bash
python3 -m pytest tests/test_redis_cache.py::TestRedisCache::test_redis_get_set -vv
```

---

**You're ready to start Sprint 23!** 🚀

Next: Review Phase 1 and start architecture design.
