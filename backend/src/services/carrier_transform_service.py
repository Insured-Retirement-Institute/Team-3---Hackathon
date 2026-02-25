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

# Default Bedrock Claude model (use env to override). Fallback list if primary is invalid in account.
BEDROCK_MODEL_ID = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
BEDROCK_MODEL_FALLBACKS = [
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
]
BEDROCK_REGION = os.getenv("AWS_REGION", "us-east-1")

# Built-in nested format YAML (meta/agent/appointment) so Bedrock can generate nested payloads too
BUILTIN_NESTED_FORMAT_YAML = """
meta:
  carrier_id: string
agent:
  advisor_id: string
  npn: string
  name:
    first: string
    last: string
  contacts:
    - type: email
      value: string
    - type: phone
      value: string
  broker_dealer: string
  license_states: list of strings
appointment:
  states: list of state codes
""".strip()


# Store last error for debugging (e.g. NoCredentialsError, AccessDenied)
_last_bedrock_error: Optional[str] = None
# Store last error from invoke/transform (e.g. AccessDeniedException, ValidationException)
_last_transform_error: Optional[str] = None


def _get_bedrock_runtime():
    import boto3
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _bedrock_available() -> bool:
    global _last_bedrock_error
    _last_bedrock_error = None
    try:
        _get_bedrock_runtime()
        return True
    except Exception as e:
        _last_bedrock_error = f"{type(e).__name__}: {str(e)}"
        logger.warning("Bedrock unavailable: %s", _last_bedrock_error)
        return False


def get_bedrock_debug_info() -> dict:
    """Return info for debugging Bedrock connectivity (no secrets). Performs a fresh client check."""
    global _last_bedrock_error
    info = {
        "aws_access_key_id_set": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "aws_secret_access_key_set": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
        "aws_region": BEDROCK_REGION,
        "bedrock_model_id": BEDROCK_MODEL_ID,
        "bedrock_client_ok": False,
        "bedrock_error": None,
    }
    try:
        _get_bedrock_runtime()
        info["bedrock_client_ok"] = True
        _last_bedrock_error = None
    except Exception as e:
        _last_bedrock_error = f"{type(e).__name__}: {str(e)}"
        info["bedrock_error"] = _last_bedrock_error
    return info


def get_last_transform_error() -> Optional[str]:
    """Return the last error from transform_to_carrier_format (invoke_model or parse failure)."""
    return _last_transform_error


def _invoke_claude(system_prompt: str, user_content: str) -> str:
    client = _get_bedrock_runtime()
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    model_ids = [BEDROCK_MODEL_ID] + [m for m in BEDROCK_MODEL_FALLBACKS if m != BEDROCK_MODEL_ID]
    last_error = None
    for model_id in model_ids:
        try:
            response = client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            result = json.loads(response["body"].read())
            for block in result.get("content", []):
                if block.get("type") == "text":
                    return block.get("text", "").strip()
            return ""
        except Exception as e:
            last_error = e
            if "ValidationException" in type(e).__name__ or "invalid" in str(e).lower():
                logger.warning("Model %s failed (%s), trying fallback", model_id, e)
                continue
            raise
    if last_error:
        raise last_error
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

    global _last_transform_error
    _last_transform_error = None
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
        _last_transform_error = f"{type(e).__name__}: {str(e)}"
        logger.exception("Bedrock transform failed for carrier %s: %s", carrier_id, e)
        return None
