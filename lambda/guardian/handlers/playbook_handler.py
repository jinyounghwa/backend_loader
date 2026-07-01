"""Playbook API Handler for REST endpoints."""

import json
from typing import Dict, Any
from guardian.http_response import success_response, error_response


class PlaybookHandler:
    """REST API handler for playbook management and execution."""

    def __init__(self, playbook_service, execution_engine, builder_service, approval_service):
        """Initialize handler with services."""
        self.playbooks = playbook_service
        self.engine = execution_engine
        self.builder = builder_service
        self.approvals = approval_service

    def handle_request(self, event: Dict, context: Any) -> Dict:
        """Route requests to appropriate handler."""
        path = event.get('path', '')
        method = event.get('httpMethod', 'GET')

        # Playbook management endpoints
        if path == '/playbooks' and method == 'POST':
            return self.create_playbook(event)
        elif path == '/playbooks' and method == 'GET':
            return self.list_playbooks(event)
        elif '/playbooks/' in path and method == 'GET':
            playbook_id = self._extract_id(path, '/playbooks/')
            return self.get_playbook(playbook_id)
        elif '/playbooks/' in path and method == 'PUT':
            playbook_id = self._extract_id(path, '/playbooks/')
            return self.update_playbook(event, playbook_id)
        elif '/playbooks/' in path and method == 'DELETE':
            playbook_id = self._extract_id(path, '/playbooks/')
            return self.delete_playbook(playbook_id)

        # Playbook control endpoints
        elif 'enable' in path and method == 'POST':
            playbook_id = self._extract_id(path, '/playbooks/')
            return self.enable_playbook(playbook_id)
        elif 'disable' in path and method == 'POST':
            playbook_id = self._extract_id(path, '/playbooks/')
            return self.disable_playbook(playbook_id)
        elif 'validate' in path and method == 'POST':
            playbook_id = self._extract_id(path, '/playbooks/')
            return self.validate_playbook(event, playbook_id)
        elif 'execute' in path and method == 'POST':
            playbook_id = self._extract_id(path, '/playbooks/')
            return self.execute_playbook(event, playbook_id)

        # Execution management
        elif 'executions' in path and method == 'GET':
            execution_id = self._extract_id(path, '/executions/')
            return self.get_execution_status(execution_id)
        elif 'executions' in path and 'stop' in path and method == 'POST':
            execution_id = self._extract_id(path, '/executions/')
            return self.stop_execution(execution_id)
        elif 'executions' in path and 'rollback' in path and method == 'POST':
            execution_id = self._extract_id(path, '/executions/')
            return self.rollback_execution(execution_id)

        # Builder endpoints
        elif path == '/playbook-builder/actions' and method == 'GET':
            return self.get_action_templates()
        elif path == '/playbook-builder/triggers' and method == 'GET':
            return self.get_trigger_templates()
        elif path == '/playbook-builder/examples' and method == 'GET':
            return self.get_playbook_examples()

        # Approval endpoints
        elif path == '/playbook-approval/pending' and method == 'GET':
            return self.get_pending_approvals()
        elif 'approve' in path and method == 'POST':
            execution_id = self._extract_id(path, '/executions/')
            return self.approve_execution(event, execution_id)
        elif 'reject' in path and method == 'POST':
            execution_id = self._extract_id(path, '/executions/')
            return self.reject_execution(event, execution_id)

        return self._error_response(404, 'Endpoint not found')

    def create_playbook(self, event: Dict) -> Dict:
        """POST /playbooks - Create new playbook."""
        try:
            body = json.loads(event.get('body', '{}'))

            playbook = self.playbooks.create_playbook(
                name=body.get('name'),
                description=body.get('description', ''),
                triggers=body.get('triggers', []),
                actions=body.get('actions', []),
                priority=body.get('priority', 5)
            )

            return self._success_response(playbook)
        except Exception as e:
            return self._error_response(400, str(e))

    def list_playbooks(self, event: Dict) -> Dict:
        """GET /playbooks - List all playbooks."""
        enabled_only = event.get('queryStringParameters', {}).get('enabled_only') == 'true'
        playbooks = self.playbooks.list_playbooks(enabled_only=enabled_only)
        return self._success_response({'playbooks': playbooks})

    def get_playbook(self, playbook_id: str) -> Dict:
        """GET /playbooks/{playbook_id} - Get playbook details."""
        playbook = self.playbooks.get_playbook(playbook_id)
        if not playbook:
            return self._error_response(404, 'Playbook not found')
        return self._success_response(playbook)

    def update_playbook(self, event: Dict, playbook_id: str) -> Dict:
        """PUT /playbooks/{playbook_id} - Update playbook."""
        try:
            body = json.loads(event.get('body', '{}'))
            playbook = self.playbooks.update_playbook(playbook_id, body)

            if not playbook:
                return self._error_response(404, 'Playbook not found')

            return self._success_response(playbook)
        except Exception as e:
            return self._error_response(400, str(e))

    def delete_playbook(self, playbook_id: str) -> Dict:
        """DELETE /playbooks/{playbook_id} - Delete playbook."""
        success = self.playbooks.delete_playbook(playbook_id)
        if not success:
            return self._error_response(404, 'Playbook not found')
        return self._success_response({'deleted': True})

    def enable_playbook(self, playbook_id: str) -> Dict:
        """POST /playbooks/{playbook_id}/enable - Enable playbook."""
        success = self.playbooks.enable_playbook(playbook_id)
        if not success:
            return self._error_response(404, 'Playbook not found')
        return self._success_response({'enabled': True})

    def disable_playbook(self, playbook_id: str) -> Dict:
        """POST /playbooks/{playbook_id}/disable - Disable playbook."""
        success = self.playbooks.disable_playbook(playbook_id)
        if not success:
            return self._error_response(404, 'Playbook not found')
        return self._success_response({'disabled': True})

    def validate_playbook(self, event: Dict, playbook_id: str) -> Dict:
        """POST /playbooks/{playbook_id}/validate - Validate playbook."""
        playbook = self.playbooks.get_playbook(playbook_id)
        if not playbook:
            return self._error_response(404, 'Playbook not found')

        validation = self.playbooks.validate_playbook(playbook)
        return self._success_response(validation)

    def execute_playbook(self, event: Dict, playbook_id: str) -> Dict:
        """POST /playbooks/{playbook_id}/execute - Execute playbook for threat."""
        try:
            body = json.loads(event.get('body', '{}'))
            threat = body.get('threat', {})

            playbook = self.playbooks.get_playbook(playbook_id)
            if not playbook:
                return self._error_response(404, 'Playbook not found')

            # Check if approval required
            if playbook.get('approval_required', False):
                approval = self.approvals.request_approval(
                    str(id(threat)),
                    threat,
                    playbook,
                    playbook.get('actions', [])
                )
                return self._success_response({
                    'status': 'APPROVAL_REQUIRED',
                    'approval_id': approval['approval_id']
                })

            # Execute playbook
            execution = self.engine.execute_playbook(threat, playbook)
            self.playbooks.increment_execution_count(playbook_id)

            return self._success_response(execution)
        except Exception as e:
            return self._error_response(400, str(e))

    def get_execution_status(self, execution_id: str) -> Dict:
        """GET /playbooks/executions/{execution_id} - Get execution status."""
        execution = self.engine.get_playbook_execution_status(execution_id)
        if not execution:
            return self._error_response(404, 'Execution not found')
        return self._success_response(execution)

    def stop_execution(self, execution_id: str) -> Dict:
        """POST /playbooks/executions/{execution_id}/stop - Stop execution."""
        success = self.engine.stop_playbook_execution(execution_id)
        if not success:
            return self._error_response(404, 'Execution not found')
        return self._success_response({'stopped': True})

    def rollback_execution(self, execution_id: str) -> Dict:
        """POST /playbooks/executions/{execution_id}/rollback - Rollback execution."""
        result = self.engine.rollback_playbook_execution(execution_id)
        return self._success_response(result)

    def get_action_templates(self) -> Dict:
        """GET /playbook-builder/actions - Get action templates."""
        templates = self.builder.get_action_templates()
        return self._success_response({'actions': templates})

    def get_trigger_templates(self) -> Dict:
        """GET /playbook-builder/triggers - Get trigger templates."""
        templates = self.builder.get_trigger_templates()
        return self._success_response({'triggers': templates})

    def get_playbook_examples(self) -> Dict:
        """GET /playbook-builder/examples - Get playbook examples."""
        examples = self.builder.get_playbook_examples()
        return self._success_response({'examples': examples})

    def get_pending_approvals(self) -> Dict:
        """GET /playbook-approval/pending - Get pending approvals."""
        approvals = self.approvals.get_pending_approvals()
        return self._success_response({'approvals': approvals})

    def approve_execution(self, event: Dict, execution_id: str) -> Dict:
        """POST /playbook-approval/{execution_id}/approve - Approve execution."""
        try:
            body = json.loads(event.get('body', '{}'))
            result = self.approvals.approve_execution(
                execution_id,
                body.get('approver_id'),
                body.get('reason', '')
            )
            if not result['success']:
                return self._error_response(400, result['message'])
            return self._success_response(result)
        except Exception as e:
            return self._error_response(400, str(e))

    def reject_execution(self, event: Dict, execution_id: str) -> Dict:
        """POST /playbook-approval/{execution_id}/reject - Reject execution."""
        try:
            body = json.loads(event.get('body', '{}'))
            result = self.approvals.reject_execution(
                execution_id,
                body.get('approver_id'),
                body.get('reason', '')
            )
            if not result['success']:
                return self._error_response(400, result['message'])
            return self._success_response(result)
        except Exception as e:
            return self._error_response(400, str(e))

    def _extract_id(self, path: str, prefix: str) -> str:
        """Extract ID from path."""
        start = path.find(prefix) + len(prefix)
        end = path.find('/', start)
        if end == -1:
            end = len(path)
        return path[start:end]

    def _success_response(self, data: Dict) -> Dict:
        """Return success response."""
        return success_response(data)

    def _error_response(self, status_code: int, message: str) -> Dict:
        """Return error response."""
        return error_response(status_code, message)
