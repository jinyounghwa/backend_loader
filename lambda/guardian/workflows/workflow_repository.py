"""Repository for storing and retrieving remediation workflows"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WorkflowRepository:
    """Store and manage custom remediation workflows"""

    def __init__(self):
        """Initialize workflow repository"""
        self.workflows_by_id = {}
        self.workflows_by_threat_type = {}

    def save_workflow(self, workflow: Dict) -> bool:
        """
        Save a workflow to repository

        Args:
            workflow: Workflow object with workflow_id and threat_type

        Returns:
            True if saved successfully
        """
        try:
            workflow_id = workflow.get('workflow_id')
            threat_type = workflow.get('trigger_threat_type', 'general')

            if not workflow_id:
                logger.error("Workflow must have workflow_id")
                return False

            self.workflows_by_id[workflow_id] = workflow

            if threat_type not in self.workflows_by_threat_type:
                self.workflows_by_threat_type[threat_type] = []

            if workflow_id not in [w.get('workflow_id') for w in self.workflows_by_threat_type[threat_type]]:
                self.workflows_by_threat_type[threat_type].append(workflow)

            logger.info(f"Saved workflow {workflow_id} for threat type {threat_type}")
            return True

        except Exception as e:
            logger.error(f"Error saving workflow: {str(e)}")
            return False

    def get_workflow(self, workflow_id: str) -> Optional[Dict]:
        """
        Retrieve a workflow by ID

        Args:
            workflow_id: Workflow ID to retrieve

        Returns:
            Workflow object or None if not found
        """
        try:
            workflow = self.workflows_by_id.get(workflow_id)

            if workflow:
                logger.info(f"Retrieved workflow {workflow_id}")
            else:
                logger.warning(f"Workflow {workflow_id} not found")

            return workflow

        except Exception as e:
            logger.error(f"Error retrieving workflow: {str(e)}")
            return None

    def list_workflows_by_threat_type(self, threat_type: str) -> List[Dict]:
        """
        Get all workflows applicable to a threat type

        Args:
            threat_type: Threat type to filter workflows

        Returns:
            List of workflows for the threat type
        """
        try:
            workflows = self.workflows_by_threat_type.get(threat_type, [])

            logger.info(f"Found {len(workflows)} workflows for threat type {threat_type}")
            return workflows

        except Exception as e:
            logger.error(f"Error listing workflows: {str(e)}")
            return []

    def update_workflow(self, workflow_id: str, updates: Dict) -> bool:
        """
        Update an existing workflow

        Args:
            workflow_id: Workflow ID to update
            updates: Dictionary of fields to update

        Returns:
            True if updated successfully
        """
        try:
            if workflow_id not in self.workflows_by_id:
                logger.error(f"Workflow {workflow_id} not found for update")
                return False

            workflow = self.workflows_by_id[workflow_id]
            old_threat_type = workflow.get('trigger_threat_type', 'general')

            workflow.update(updates)
            workflow['updated_at'] = datetime.now(timezone.utc).isoformat()

            new_threat_type = workflow.get('trigger_threat_type', 'general')

            if old_threat_type != new_threat_type:
                if old_threat_type in self.workflows_by_threat_type:
                    self.workflows_by_threat_type[old_threat_type] = [
                        w for w in self.workflows_by_threat_type[old_threat_type]
                        if w.get('workflow_id') != workflow_id
                    ]

                if new_threat_type not in self.workflows_by_threat_type:
                    self.workflows_by_threat_type[new_threat_type] = []

                self.workflows_by_threat_type[new_threat_type].append(workflow)

            logger.info(f"Updated workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating workflow: {str(e)}")
            return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete a workflow from repository

        Args:
            workflow_id: Workflow ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            if workflow_id not in self.workflows_by_id:
                logger.warning(f"Workflow {workflow_id} not found for deletion")
                return False

            workflow = self.workflows_by_id.pop(workflow_id)
            threat_type = workflow.get('trigger_threat_type', 'general')

            if threat_type in self.workflows_by_threat_type:
                self.workflows_by_threat_type[threat_type] = [
                    w for w in self.workflows_by_threat_type[threat_type]
                    if w.get('workflow_id') != workflow_id
                ]

            logger.info(f"Deleted workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting workflow: {str(e)}")
            return False

    def list_all_workflows(self) -> List[Dict]:
        """
        Get all workflows in repository

        Returns:
            List of all workflows
        """
        try:
            workflows = list(self.workflows_by_id.values())
            logger.info(f"Found {len(workflows)} total workflows")
            return workflows

        except Exception as e:
            logger.error(f"Error listing all workflows: {str(e)}")
            return []
