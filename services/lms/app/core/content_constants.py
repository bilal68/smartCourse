# app/core/content_constants.py
"""Constants for content upload and validation"""

# File size limits
MAX_ARTICLE_JSON_SIZE = 2 * 1024 * 1024  # 2 MB

# Editor schema validation limits
MAX_EDITOR_NODES = 50_000
MAX_TEXT_CHARS = 200_000
MIN_TEXT_CHARS = 100

# URL signing timeouts
UPLOAD_EXPIRY_SECONDS = 600  # 10 minutes
GET_EXPIRY_SECONDS = 600  # 10 minutes

# Supported content formats
SUPPORTED_CONTENT_FORMATS = ["EDITOR_JSON"]

# Supported storage providers
SUPPORTED_STORAGE_PROVIDERS = ["S3", "MINIO", "LOCAL"]

# Allowed node types in editor schema
ALLOWED_NODE_TYPES = {
    "doc",
    "heading",
    "paragraph",
    "text",
    "bulletList",
    "orderedList",
    "listItem",
    "codeBlock",
    "blockquote",
    "hardBreak",
}

# Required fields in editor JSON
EDITOR_SCHEMA_VERSION = "smartcourse.editor.v1"
