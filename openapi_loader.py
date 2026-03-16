"""
Parses Swagger 2.0 specs from the SP-API models repo into MCP tool definitions.
"""

import json
from pathlib import Path


def _swagger_type_to_json_schema(param_type, param_format=None, items=None):
    """Convert Swagger type to JSON Schema type."""
    type_map = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
    }
    schema = {"type": type_map.get(param_type, "string")}
    if param_format:
        schema["format"] = param_format
    if param_type == "array" and items:
        schema["items"] = {"type": items.get("type", "string")}
    return schema


def _build_tool_name(method, path, spec_prefix):
    """Build a unique tool name from method + path."""
    # e.g. GET /orders/v0/orders -> orders_getOrders
    parts = [p for p in path.split("/") if p and not p.startswith("{")]
    # Use last meaningful path segment
    name_parts = []
    for p in parts:
        # Skip version segments like v0, v1
        if p in ("v0", "v1", "v2"):
            continue
        name_parts.append(p)

    path_name = "_".join(name_parts[-2:]) if len(name_parts) > 1 else "_".join(name_parts)
    return f"{spec_prefix}_{method}_{path_name}".replace("-", "_")


def load_spec(spec_path: str) -> list[dict]:
    """
    Load a Swagger 2.0 spec and return a list of tool definitions.

    Each tool has:
      - name: unique tool name
      - description: from the operation summary/description
      - parameters: JSON Schema for input
      - method: HTTP method
      - path: API path with {param} placeholders
      - host: API host from spec
    """
    with open(spec_path) as f:
        spec = json.load(f)

    host = spec.get("host", "sellingpartnerapi-na.amazon.com")
    schemes = spec.get("schemes", ["https"])
    base_url = f"{schemes[0]}://{host}"
    base_path = spec.get("basePath", "")
    spec_title = spec.get("info", {}).get("title", "")

    # Derive a short prefix from the file name
    prefix = Path(spec_path).stem.split("_")[0].split("V")[0]

    tools = []

    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method in ("parameters", "x-amzn-api-sandbox"):
                continue

            op_id = operation.get("operationId", "")
            summary = operation.get("summary", "")
            description = operation.get("description", summary)

            tool_name = op_id if op_id else _build_tool_name(method, path, prefix)

            # Build parameter schema
            properties = {}
            required = []

            for param in operation.get("parameters", []):
                p_name = param.get("name", "")
                p_in = param.get("in", "")
                p_required = param.get("required", False)
                p_desc = param.get("description", "")
                p_type = param.get("type", "string")
                p_format = param.get("format")
                p_items = param.get("items")

                if p_in == "body":
                    # Body params: accept as JSON string
                    properties[p_name] = {
                        "type": "string",
                        "description": f"{p_desc} (JSON body)",
                    }
                else:
                    schema = _swagger_type_to_json_schema(p_type, p_format, p_items)
                    schema["description"] = p_desc
                    if "enum" in param:
                        schema["enum"] = param["enum"]
                    properties[p_name] = schema

                if p_required:
                    required.append(p_name)

            input_schema = {
                "type": "object",
                "properties": properties,
            }
            if required:
                input_schema["required"] = required

            tools.append({
                "name": tool_name,
                "description": f"[{spec_title}] {description[:500]}",
                "inputSchema": input_schema,
                "method": method.upper(),
                "path": f"{base_path}{path}",
                "base_url": base_url,
            })

    return tools
