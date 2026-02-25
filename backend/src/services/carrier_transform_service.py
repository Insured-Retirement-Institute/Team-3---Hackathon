"""
Transform advisor + states into a carrier request payload using the format defined in YAML,
via AWS Bedrock Claude (e.g. Claude 3.5 Sonnet). The YAML describes the expected request
(and optionally response) structure; Claude outputs JSON matching that format.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default Bedrock Claude model (3.5 Sonnet; use env for 4.5 or other variants)
BEDROCK_MODEL_ID = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "anthropic.claude-3-5-sonnet-v2:0")
BEDROCK_REGION = os.getenv("AWS_REGION", "us-east-1")


def _get_bedrock_runtime():
    import boto3
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _bedrock_available() -> bool:
    try:
        _get_bedrock_runtime()
        return True
    except Exception:
        return False


def _invoke_claude(system_prompt: str, user_content: str) -> str:
    client = _get_bedrock_runtime()
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    response = client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    result = json.loads(response["body"].read())
    for block in result.get("content", []):
        if block.get("type") == "text":
            return block.get("text", "").strip()
    return ""


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse a JSON object from the model output (may be wrapped in markdown)."""
    text = text.strip()
    # Strip markdown code block if present
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find first { ... }
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


async def transform_to_carrier_format(
    carrier_id: str,
    format_yaml: str,
    advisor: Dict[str, Any],
    submitted_states: list,
) -> Optional[Dict[str, Any]]:
    """
    Use Bedrock Claude to transform advisor + states into a request payload
    that matches the structure described in format_yaml. Returns JSON dict or None on failure.
    """
    if not format_yaml or not format_yaml.strip():
        return None
    if not _bedrock_available():
        logger.warning("Bedrock not available (credentials/region); skipping YAML transform for %s", carrier_id)
        return None

    system_prompt = """You are a data mapper. You will be given:
1) A YAML specification of the expected request body for a carrier API (request schema).
2) Source data: an advisor object and a list of requested states.

Your task: output exactly one valid JSON object that is the HTTP request body for the carrier API.
The JSON must conform to the structure and field names described in the YAML. Map advisor fields
and states to the expected keys. Use only the fields present in the YAML. If the YAML shows
nested objects or arrays, produce that structure. Output nothing else except the JSON object
(no explanation, no markdown)."""

    user_content = f"""YAML request format:
{format_yaml}

Source data:
- advisor: {json.dumps(advisor, default=str)}
- submitted_states: {json.dumps(submitted_states)}

Produce the carrier API request body as a single JSON object:"""

    try:
        out = _invoke_claude(system_prompt, user_content)
        if not out:
            logger.warning("Bedrock returned empty response for carrier %s", carrier_id)
            return None
        payload = _extract_json_from_text(out)
        if payload is None:
            logger.warning("Could not parse JSON from Bedrock response for carrier %s: %s", carrier_id, out[:200])
            return None
        return payload
    except Exception as e:
        logger.exception("Bedrock transform failed for carrier %s: %s", carrier_id, e)
        return None
