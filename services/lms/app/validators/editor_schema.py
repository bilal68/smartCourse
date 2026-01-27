# app/validators/editor_schema.py
"""Validator for editor JSON schema"""

import logging
from typing import Any, Dict, Set

from app.core.content_constants import (
    ALLOWED_NODE_TYPES,
    EDITOR_SCHEMA_VERSION,
    MAX_EDITOR_NODES,
    MAX_TEXT_CHARS,
    MIN_TEXT_CHARS,
)

logger = logging.getLogger(__name__)


class EditorSchemaValidator:
    """Validates editor JSON structure and content"""

    def __init__(self):
        self.errors: list[str] = []
        self.node_count = 0
        self.text_char_count = 0

    def validate(self, data: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate editor JSON schema
        
        Returns:
            (is_valid, list_of_errors)
        """
        self.errors = []
        self.node_count = 0
        self.text_char_count = 0

        try:
            # Check schema version
            if not isinstance(data, dict):
                self.errors.append("Content must be a JSON object")
                return False, self.errors

            schema = data.get("schema")
            if schema != EDITOR_SCHEMA_VERSION:
                self.errors.append(
                    f'Invalid schema version: "{schema}". Expected: "{EDITOR_SCHEMA_VERSION}"'
                )
                return False, self.errors

            # Check doc structure
            doc = data.get("doc")
            if not doc:
                self.errors.append("Missing required field: doc")
                return False, self.errors

            if not isinstance(doc, dict):
                self.errors.append("Field 'doc' must be an object")
                return False, self.errors

            if doc.get("type") != "doc":
                self.errors.append("Root doc node must have type: 'doc'")
                return False, self.errors

            # Validate doc content
            if "content" not in doc:
                self.errors.append("Field 'doc.content' is required")
                return False, self.errors

            content = doc.get("content", [])
            if not isinstance(content, list):
                self.errors.append("Field 'doc.content' must be an array")
                return False, self.errors

            # Walk and validate all nodes
            self._validate_nodes(content)

            # Check text constraints
            if self.text_char_count < MIN_TEXT_CHARS:
                self.errors.append(
                    f"Content too short: {self.text_char_count} chars "
                    f"(minimum: {MIN_TEXT_CHARS})"
                )

            if self.text_char_count > MAX_TEXT_CHARS:
                self.errors.append(
                    f"Content too long: {self.text_char_count} chars "
                    f"(maximum: {MAX_TEXT_CHARS})"
                )

            if self.node_count > MAX_EDITOR_NODES:
                self.errors.append(
                    f"Too many nodes: {self.node_count} "
                    f"(maximum: {MAX_EDITOR_NODES})"
                )

            return len(self.errors) == 0, self.errors

        except Exception as e:
            logger.exception(f"Schema validation error: {e}")
            self.errors.append(f"Unexpected validation error: {str(e)}")
            return False, self.errors

    def _validate_nodes(self, nodes: list, path: str = "doc.content") -> None:
        """Recursively validate all nodes"""
        if not isinstance(nodes, list):
            self.errors.append(f"Node array at {path} must be a list")
            return

        for idx, node in enumerate(nodes):
            node_path = f"{path}[{idx}]"
            self._validate_single_node(node, node_path)

    def _validate_single_node(self, node: Any, path: str) -> None:
        """Validate a single node"""
        if not isinstance(node, dict):
            self.errors.append(f"Node at {path} must be an object")
            return

        self.node_count += 1
        if self.node_count > MAX_EDITOR_NODES:
            return  # Stop validation if we exceed limit

        node_type = node.get("type")
        if not node_type:
            self.errors.append(f"Node at {path} missing 'type' field")
            return

        if node_type not in ALLOWED_NODE_TYPES:
            self.errors.append(
                f"Invalid node type '{node_type}' at {path}. "
                f"Allowed: {', '.join(sorted(ALLOWED_NODE_TYPES))}"
            )
            return

        # Validate type-specific attributes
        if node_type == "heading":
            self._validate_heading(node, path)
        elif node_type == "text":
            self._validate_text(node, path)

        # Recursively validate nested content
        if "content" in node:
            nested_content = node.get("content")
            if isinstance(nested_content, list):
                self._validate_nodes(nested_content, f"{path}.content")

    def _validate_heading(self, node: Dict[str, Any], path: str) -> None:
        """Validate heading node"""
        attrs = node.get("attrs", {})
        if not isinstance(attrs, dict):
            self.errors.append(f"Heading attrs at {path} must be an object")
            return

        level = attrs.get("level")
        if level is None:
            self.errors.append(f"Heading at {path} missing 'attrs.level'")
            return

        if not isinstance(level, int) or level < 1 or level > 6:
            self.errors.append(
                f"Invalid heading level at {path}: {level} (allowed: 1-6)"
            )

    def _validate_text(self, node: Dict[str, Any], path: str) -> None:
        """Validate text node"""
        text = node.get("text", "")
        if not isinstance(text, str):
            self.errors.append(f"Text value at {path} must be a string")
            return

        self.text_char_count += len(text)


def validate_editor_json(data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate editor JSON structure
    
    Returns:
        (is_valid, list_of_errors)
    """
    validator = EditorSchemaValidator()
    return validator.validate(data)
