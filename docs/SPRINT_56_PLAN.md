# Sprint 56: Custom Response Playbooks

> **Goal**: User-defined automated remediation playbooks and orchestration engine for flexible, organization-specific threat response

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Sprint Duration | 1 session |
| Test Target | 15 tests (reaching ~912 cumulative) |
| Phases | 1 (Custom Response Playbooks) |
| Priority | Flexible automation, user-defined workflows, playbook execution |

---

## Context

**Completed (Sprints 49-54)**:
- Sprint 49: RemediationOrchestrator (15 tests) ✅
- Sprint 50: SmartRemediationEngine (15 tests) ✅
- Sprint 51: Real-time Response System (19 tests) ✅
- Sprint 52: Dashboard Integration (14 tests) ✅
- Sprint 53: Multi-Account Orchestration (15 tests) ✅
- Sprint 54: Advanced Threat Correlation (15 tests) ✅
- **Cumulative**: 881 tests PASS

**Current Sprint (Next)**:
- Sprint 55: Compliance & Audit Features (16 tests planned)
  - Target: 897 tests cumulative

**Future Sprint (This)**:
- Sprint 56 Phase 1: Custom Response Playbooks (15 tests)
  - Build playbook definition and storage
  - Implement playbook execution engine
  - Create playbook builder UI API
  - Enable organization-specific automation

---

## Sprint 56 Phase 1: Custom Response Playbooks (15 tests)

### Objective
Enable security teams to define, manage, and execute custom remediation playbooks - automated workflows that execute specific sequences of actions based on threat conditions, allowing organizations to tailor threat response to their unique infrastructure and policies.

### Implementation Files

#### 1. PlaybookDefinitionService Class
**File**: `lambda/guardian/services/playbook_definition_service.py`

```python
class PlaybookDefinitionService:
    def __init__(self, audit_logger=None):
        """Initialize playbook service."""
        self.audit = audit_logger
        self.playbooks = {}
    
    def create_playbook(self, name, description, triggers, actions, priority):
        """
        Create new remediation playbook.
        
        Playbook structure:
        {
            'playbook_id': UUID,
            'name': str,
            'description': str,
            'enabled': bool,
            'priority': int (1-10, higher = run first),
            'triggers': [
                {
                    'threat_type': str,
                    'severity_range': [min, max],
                    'account_ids': [optional],
                    'conditions': {...}
                }
            ],
            'actions': [
                {
                    'order': int,
                    'action_type': str (stop_ec2, isolate_network, etc),
                    'parameters': {...},
                    'skip_on_failure': bool,
                    'notification': bool
                }
            ],
            'approval_required': bool,
            'approval_group': str (optional)
        }
        """
    
    def update_playbook(self, playbook_id, updates):
        """Update existing playbook."""
    
    def delete_playbook(self, playbook_id):
        """Delete playbook."""
    
    def get_playbook(self, playbook_id):
        """Get playbook details."""
    
    def list_playbooks(self, enabled_only=False):
        """List all playbooks or only enabled ones."""
    
    def enable_playbook(self, playbook_id):
        """Enable playbook for automatic execution."""
    
    def disable_playbook(self, playbook_id):
        """Disable playbook temporarily."""
    
    def validate_playbook(self, playbook):
        """Validate playbook structure and action syntax."""
```

#### 2. PlaybookExecutionEngine Class
**File**: `lambda/guardian/engines/playbook_execution_engine.py`

```python
class PlaybookExecutionEngine:
    def __init__(self, orchestrator=None, audit_logger=None):
        """Initialize playbook execution engine."""
        self.orchestrator = orchestrator
        self.audit = audit_logger
        self.executions = {}
    
    def match_applicable_playbooks(self, threat):
        """
        Find playbooks matching threat condition.
        Returns: [(playbook, priority), ...] sorted by priority
        """
    
    def execute_playbook(self, threat, playbook):
        """
        Execute playbook for threat.
        Returns execution result with action outcomes.
        """
    
    def execute_action(self, action_config, threat, context):
        """
        Execute single action within playbook.
        - EC2 actions: stop, terminate, snapshot
        - Network actions: isolate, restrict_sg
        - S3 actions: block_public, enable_versioning
        - IAM actions: revoke_roles, disable_keys
        - Custom actions: call webhook/lambda
        """
    
    def get_execution_history(self, threat_id):
        """Get all playbook executions for threat."""
    
    def get_playbook_execution_status(self, execution_id):
        """Get real-time execution status."""
    
    def stop_playbook_execution(self, execution_id):
        """Stop in-progress playbook execution."""
    
    def rollback_playbook_execution(self, execution_id):
        """Rollback completed playbook actions."""
    
    def get_execution_summary(self):
        """Get aggregate playbook execution statistics."""
```

#### 3. PlaybookBuilderService Class
**File**: `lambda/guardian/services/playbook_builder_service.py`

```python
class PlaybookBuilderService:
    def __init__(self):
        """Initialize playbook builder."""
        self.templates = {}
        self.actions = {}
    
    def get_action_templates(self):
        """
        Return available action templates.
        
        Standard actions:
        - ec2_stop: Stop EC2 instance
        - ec2_terminate: Terminate EC2 instance
        - ec2_snapshot: Create snapshot before action
        - network_isolate: Restrict security group
        - network_restrict_sg: Add deny rule to SG
        - s3_block_public: Block public access
        - s3_enable_versioning: Enable versioning
        - iam_revoke_roles: Remove IAM roles
        - iam_disable_keys: Disable access keys
        - sns_notify: Send SNS notification
        - lambda_invoke: Invoke Lambda function
        - webhook_post: POST to webhook URL
        """
    
    def get_trigger_templates(self):
        """
        Return available trigger templates.
        
        Trigger types:
        - threat_type_match: Match by threat type
        - severity_range: Match by severity
        - account_filter: Match by account
        - resource_type: Match by resource type
        - custom_condition: Custom field matching
        """
    
    def validate_action(self, action_type, parameters):
        """Validate action configuration."""
    
    def validate_trigger(self, trigger_type, conditions):
        """Validate trigger configuration."""
    
    def get_playbook_examples(self):
        """Return example playbooks for common scenarios."""
    
    def suggest_playbook_actions(self, threat_type):
        """Suggest actions based on threat type."""
```

#### 4. PlaybookApprovalService Class
**File**: `lambda/guardian/services/playbook_approval_service.py`

```python
class PlaybookApprovalService:
    def __init__(self, audit_logger=None):
        """Initialize approval service."""
        self.audit = audit_logger
        self.approvals = {}
    
    def request_approval(self, execution_id, threat, playbook, actions):
        """Request approval for playbook execution."""
    
    def approve_execution(self, execution_id, approver_id, reason):
        """Approve pending execution."""
    
    def reject_execution(self, execution_id, approver_id, reason):
        """Reject execution."""
    
    def get_pending_approvals(self):
        """Get list of pending approval requests."""
    
    def get_approval_status(self, execution_id):
        """Get approval status for execution."""
    
    def configure_approval_group(self, playbook_id, approval_group):
        """Configure which team approves this playbook."""
```

#### 5. Playbook API Handler
**File**: `lambda/guardian/handlers/playbook_handler.py`

```python
def lambda_handler(event, context):
    """
    Playbook management and execution API endpoints.
    
    Routes:
    - POST /playbooks - Create new playbook
    - GET /playbooks - List all playbooks
    - GET /playbooks/{playbook_id} - Get playbook details
    - PUT /playbooks/{playbook_id} - Update playbook
    - DELETE /playbooks/{playbook_id} - Delete playbook
    - POST /playbooks/{playbook_id}/enable - Enable playbook
    - POST /playbooks/{playbook_id}/disable - Disable playbook
    - POST /playbooks/{playbook_id}/validate - Validate playbook
    - POST /playbooks/{playbook_id}/execute - Execute playbook for threat
    - GET /playbooks/executions/{execution_id} - Get execution status
    - POST /playbooks/executions/{execution_id}/stop - Stop execution
    - GET /playbook-builder/actions - Get action templates
    - GET /playbook-builder/triggers - Get trigger templates
    - POST /playbook-approval/request - Request approval
    - POST /playbook-approval/{execution_id}/approve - Approve execution
    """
```

### Test Files

#### Backend Tests (8 tests)
**File**: `tests/backend/test_playbook_engine.py`

```python
class TestPlaybookDefinitionService:
    def test_create_playbook(self):
        """✅ Create new remediation playbook."""
    
    def test_update_playbook(self):
        """✅ Update existing playbook."""
    
    def test_validate_playbook(self):
        """✅ Validate playbook structure."""

class TestPlaybookExecutionEngine:
    def test_match_applicable_playbooks(self):
        """✅ Find playbooks matching threat."""
    
    def test_execute_playbook(self):
        """✅ Execute playbook for threat."""
    
    def test_execute_action_sequence(self):
        """✅ Execute action sequence in order."""
    
    def test_rollback_playbook_execution(self):
        """✅ Rollback completed actions."""

class TestPlaybookBuilderService:
    def test_get_action_templates(self):
        """✅ Return available action templates."""
```

#### Integration Tests (7 tests)
**File**: `tests/integration/test_playbook_integration.py`

```python
class TestPlaybookIntegration:
    def test_end_to_end_playbook_execution(self):
        """✅ Complete threat → playbook match → execution flow."""
    
    def test_multi_action_playbook_execution(self):
        """✅ Execute playbook with multiple sequential actions."""
    
    def test_conditional_action_execution(self):
        """✅ Skip actions based on conditions."""
    
    def test_playbook_approval_workflow(self):
        """✅ Execute with approval workflow."""
    
    def test_parallel_playbook_execution(self):
        """✅ Execute multiple playbooks concurrently."""
    
    def test_playbook_execution_with_notification(self):
        """✅ Send notifications during execution."""
    
    def test_custom_webhook_action_execution(self):
        """✅ Execute custom webhook actions."""
```

### Key Design Decisions

1. **Trigger-Based Matching**
   - Playbooks matched by threat type, severity, account
   - Priority ordering ensures correct execution sequence
   - Multiple playbooks can match same threat (all execute in priority order)

2. **Action Sequencing**
   - Actions execute in defined order (dependency ordering)
   - Each action can skip on failure or stop execution
   - Rollback state captured for recovery

3. **Flexible Action Types**
   - Standard AWS actions (EC2, Network, S3, IAM)
   - SNS/Lambda integration for extensibility
   - Webhook support for custom integrations

4. **Approval Workflows**
   - Optional approval gates on playbook level
   - Approval group assignment for delegation
   - Audit trail of all approvals/rejections

5. **Safe Execution**
   - Playbook validation before execution
   - Dry-run capability (without committing changes)
   - Rollback mechanism for recovery

---

## Testing Strategy

### Unit Tests (8)
- Playbook creation and validation
- Action template retrieval
- Trigger matching logic
- Execution sequencing
- Approval workflow

### Integration Tests (7)
- End-to-end playbook execution
- Multi-action sequences
- Conditional action execution
- Approval workflows
- Parallel playbook execution
- Notification delivery
- Custom webhook actions

### Test Coverage

| Component | Coverage |
|-----------|----------|
| Playbook definition | ✅ |
| Playbook execution | ✅ |
| Action templating | ✅ |
| Trigger matching | ✅ |
| Approval workflows | ✅ |
| Multi-account playbooks | ✅ |

---

## Implementation Checklist

- [ ] Create `lambda/guardian/services/playbook_definition_service.py`
- [ ] Create `lambda/guardian/engines/playbook_execution_engine.py`
- [ ] Create `lambda/guardian/services/playbook_builder_service.py`
- [ ] Create `lambda/guardian/services/playbook_approval_service.py`
- [ ] Create `lambda/guardian/handlers/playbook_handler.py`

- [ ] Create `tests/backend/test_playbook_engine.py` (8 tests)
- [ ] Create `tests/integration/test_playbook_integration.py` (7 tests)

- [ ] Run all 15 tests: `pytest tests/backend/test_playbook_engine.py tests/integration/test_playbook_integration.py -v`

- [ ] Create git commit:
  ```
  feat: Sprint 56 Phase 1 - Custom Response Playbooks (15 tests)
  ```

- [ ] Create SPRINT_56_COMPLETION.md documentation

---

## Success Criteria

- ✅ All 15 tests passing
- ✅ Cumulative test count: 912 (897 + 15)
- ✅ Code coverage: >90% for playbook components
- ✅ Playbook creation and validation working
- ✅ Playbook execution with action sequencing
- ✅ Trigger matching functional
- ✅ Approval workflows implemented
- ✅ Multi-action playbooks with rollback
- ✅ Action templates and examples available
- ✅ Git commit with appropriate message
- ✅ SPRINT_56_COMPLETION.md documentation created

---

## Files to Create

| File | Type | Tests |
|------|------|-------|
| `lambda/guardian/services/playbook_definition_service.py` | NEW | Playbook storage/management |
| `lambda/guardian/engines/playbook_execution_engine.py` | NEW | Playbook execution |
| `lambda/guardian/services/playbook_builder_service.py` | NEW | Builder templates |
| `lambda/guardian/services/playbook_approval_service.py` | NEW | Approval workflows |
| `lambda/guardian/handlers/playbook_handler.py` | NEW | API handler |
| `tests/backend/test_playbook_engine.py` | NEW | 8 tests |
| `tests/integration/test_playbook_integration.py` | NEW | 7 tests |
| `docs/SPRINT_56_COMPLETION.md` | NEW | Documentation |

---

## Next Sprint (Sprint 57+)

After Sprint 56 completion:
- Real-time Threat Dashboard (WebSocket updates, live event streaming)
- Machine Learning threat correlation (predictive threat analysis, attack pattern learning)
- Playbook marketplace and sharing (community playbooks, organization library)

---

## Context & Motivation

**Why Custom Playbooks?**

Organizations have unique:
1. **Infrastructure**: Different resource configurations, naming conventions, dependencies
2. **Policies**: Different approval thresholds, escalation paths, team responsibilities
3. **Integrations**: Custom tools, workflows, notification systems
4. **Threat Models**: Different threat landscapes based on industry/risk profile

SmartRemediationEngine provides severity-to-strategy mapping, but Custom Playbooks allow:
- **Flexibility**: Define exact sequence of actions for each threat type
- **Automation**: Reduce manual intervention and decision delays
- **Customization**: Align remediation with organizational policies
- **Integration**: Connect to existing tools and workflows

**Integration with Existing Systems:**
- Playbooks triggered by ThreatDetectionService
- Actions executed via RemediationOrchestrator
- Execution tracked in AuditTrailService
- Approvals integrated with PlaybookApprovalService

**Expected Benefits:**
- Reduce MTTR (Mean Time To Remediation) by 50%+ with automated playbooks
- Improve consistency of threat response across teams
- Enable rapid response customization without code changes
- Provide self-service automation to security teams

---

## Architecture Flow

```
Threat Detection
    ↓
SmartRemediationEngine (severity → strategy)
    ↓
PlaybookExecutionEngine
    ├─ match_applicable_playbooks(threat)
    │   └─ Find all playbooks matching threat condition
    │   └─ Sort by priority
    │
    ├─ For each matched playbook (in priority order):
    │   ├─ Check approval requirement
    │   │   └─ If required: PlaybookApprovalService
    │   │       └─ Wait for approval or timeout
    │   │
    │   ├─ execute_action_sequence()
    │   │   ├─ For each action (in order):
    │   │   │   ├─ Validate action parameters
    │   │   │   ├─ Execute action
    │   │   │   ├─ Check result
    │   │   │   └─ Log to AuditTrailService
    │   │   │
    │   │   ├─ If action fails:
    │   │   │   ├─ Decide: skip_on_failure?
    │   │   │   ├─ If skip: continue next action
    │   │   │   └─ If stop: halt playbook
    │   │   │
    │   │   └─ If all successful: mark completed
    │   │
    │   └─ Send notifications (if configured)
    │
    └─ Return execution summary

PlaybookBuilderService (templates)
    ├─ get_action_templates()
    │   └─ EC2, Network, S3, IAM, SNS, Lambda, Webhook
    │
    ├─ get_trigger_templates()
    │   └─ Threat type, severity, account, resource type
    │
    └─ suggest_playbook_actions()
        └─ Suggest actions based on threat type

DashboardDataService (visualization)
    ├─ get_playbook_execution_history()
    ├─ get_playbook_effectiveness()
    └─ get_playbook_execution_timeline()
```

---

## Example Playbooks

### Playbook 1: Unauthorized EC2 Response
```
Trigger: threat_type = "Unauthorized EC2" AND severity >= 7
Priority: 5
Actions:
  1. ec2_snapshot (backup before termination)
  2. ec2_isolate_network (restrict security group)
  3. iam_revoke_roles (remove instance role)
  4. sns_notify (alert security team)
  5. ec2_terminate (only if snapshot successful)
Approval: Required if critical resource
```

### Playbook 2: Public Bucket Remediation
```
Trigger: threat_type = "Public Bucket" AND severity >= 6
Priority: 7
Actions:
  1. s3_block_public (immediate public access block)
  2. s3_enable_versioning (prevent accidental deletions)
  3. sns_notify (alert storage team)
  4. webhook_post (create ticket in ITSM)
Approval: Not required (safe action)
```

### Playbook 3: Credential Compromise
```
Trigger: threat_type = "Credential Compromise" AND severity >= 9
Priority: 1 (highest)
Actions:
  1. iam_disable_keys (disable access keys immediately)
  2. iam_revoke_roles (remove temporary credentials)
  3. network_isolate (restrict network access)
  4. sns_notify_urgent (critical alert)
  5. lambda_invoke (custom compliance check)
Approval: Required (CEO notification)
```

---

## Summary

Sprint 56 delivers custom response playbooks that enable:

- **Flexible Automation**: Define custom remediation workflows for your organization
- **Action Sequencing**: Execute actions in specific order with conditional logic
- **Approval Workflows**: Require approval for high-impact actions
- **Extensibility**: Integrate with webhooks and custom Lambda functions
- **Rollback Capability**: Recover from over-aggressive remediation

This empowers security teams to:
- Reduce MTTR by automating threat response
- Tailor remediation to organizational policies
- Reduce manual intervention and decision delays
- Maintain consistency across all threat responses
- Rapidly adapt to new threat types without code changes

**Target**: 912 cumulative tests (897 + 15)
