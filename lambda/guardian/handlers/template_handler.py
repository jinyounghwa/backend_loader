"""Rule Template Management Lambda Handler for Sprint 34 Phase 1

Handles REST API operations for rule templates:
- GET /templates (list all templates)
- GET /templates/{template_id} (get specific template)
- POST /templates (create new template)
- PUT /templates/{template_id} (update template)
- DELETE /templates/{template_id} (delete template)
"""

import json
import os
from typing import Dict, Any
from guardian.http_response import success_response, error_response
from storage.rule_template import TemplateRepository, RuleTemplate, BUILTIN_TEMPLATES


def get_template_table_name() -> str:
    """Get template table name from environment or SAM exports"""
    return os.environ.get("RULE_TEMPLATE_TABLE", "aws-guardian-rule-templates")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for template management API"""
    try:
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        body = event.get("body", "{}")

        if isinstance(body, str):
            body = json.loads(body) if body else {}

        repo = TemplateRepository(get_template_table_name())

        # Initialize built-in templates on first request
        repo.bootstrap_builtin_templates()

        # Route handlers
        if http_method == "GET" and path == "/templates":
            return list_templates(repo)

        elif http_method == "GET" and "/templates/" in path:
            template_id = path.split("/")[-1]
            return get_template(repo, template_id)

        elif http_method == "POST" and path == "/templates":
            return create_template(repo, body)

        elif http_method == "PUT" and "/templates/" in path:
            template_id = path.split("/")[-1]
            return update_template(repo, template_id, body)

        elif http_method == "DELETE" and "/templates/" in path:
            template_id = path.split("/")[-1]
            return delete_template(repo, template_id)

        else:
            return error_response(400, "Invalid request")

    except Exception as e:
        print(f"Error in template handler: {e}")
        return error_response(500, str(e))


def list_templates(repo: TemplateRepository) -> Dict[str, Any]:
    """List all templates"""
    try:
        templates = repo.list_templates()
        items = [
            {
                "template_id": t.template_id,
                "template_name": t.template_name,
                "description": t.description,
                "rule_type": t.rule_type,
                "tags": t.tags,
                "version": t.version,
                "created_at": t.created_at.isoformat(),
            }
            for t in templates
        ]
        return success_response({"templates": items})
    except Exception as e:
        print(f"Error listing templates: {e}")
        return error_response(500, str(e))


def get_template(repo: TemplateRepository, template_id: str) -> Dict[str, Any]:
    """Get a specific template"""
    try:
        template = repo.get_template(template_id)
        if not template:
            return error_response(404, f"Template {template_id} not found")

        return success_response({
            "template_id": template.template_id,
            "template_name": template.template_name,
            "description": template.description,
            "rule_type": template.rule_type,
            "condition_schema": template.condition_schema,
            "action_schema": template.action_schema,
            "example_condition": template.example_condition,
            "example_action": template.example_action,
            "tags": template.tags,
            "version": template.version,
            "created_at": template.created_at.isoformat(),
        })
    except Exception as e:
        print(f"Error getting template: {e}")
        return error_response(500, str(e))


def create_template(repo: TemplateRepository, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new template"""
    try:
        required_fields = [
            "template_name",
            "description",
            "rule_type",
            "condition_schema",
            "action_schema",
            "example_condition",
            "example_action",
        ]

        for field in required_fields:
            if field not in body:
                return error_response(400, f"Missing required field: {field}")

        template = RuleTemplate(
            template_id="",  # Will be generated
            template_name=body["template_name"],
            description=body["description"],
            rule_type=body["rule_type"],
            condition_schema=body["condition_schema"],
            action_schema=body["action_schema"],
            example_condition=body["example_condition"],
            example_action=body["example_action"],
            tags=body.get("tags", []),
            version=1,
        )

        created_template = repo.create_template(template)
        return success_response(
            {
                "template_id": created_template.template_id,
                "template_name": created_template.template_name,
                "version": created_template.version,
                "message": "Template created successfully",
            },
            status_code=201,
        )
    except Exception as e:
        print(f"Error creating template: {e}")
        return error_response(500, str(e))


def update_template(repo: TemplateRepository, template_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing template"""
    try:
        template = repo.get_template(template_id)
        if not template:
            return error_response(404, f"Template {template_id} not found")

        # Create new version
        for field in ["template_name", "description", "condition_schema", "action_schema", "example_condition", "example_action"]:
            if field in body:
                setattr(template, field, body[field])

        if "tags" in body:
            template.tags = body["tags"]

        # Increment version and update
        template.version += 1
        repo.update_template(template)

        return success_response({
            "template_id": template.template_id,
            "version": template.version,
            "message": "Template updated successfully",
        })
    except Exception as e:
        print(f"Error updating template: {e}")
        return error_response(500, str(e))


def delete_template(repo: TemplateRepository, template_id: str) -> Dict[str, Any]:
    """Delete a template"""
    try:
        template = repo.get_template(template_id)
        if not template:
            return error_response(404, f"Template {template_id} not found")

        repo.delete_template(template_id)
        return success_response({
            "message": f"Template {template_id} deleted successfully"
        })
    except Exception as e:
        print(f"Error deleting template: {e}")
        return error_response(500, str(e))
