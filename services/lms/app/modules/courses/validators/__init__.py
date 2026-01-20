# app/modules/courses/validators/__init__.py
"""Course content validators"""

from app.modules.courses.validators.editor_schema import validate_editor_json

__all__ = ["validate_editor_json"]
