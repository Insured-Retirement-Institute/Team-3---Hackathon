from __future__ import annotations

import uuid


class AIService:
    async def extract_from_file(self, bucket: str, file_key: str) -> dict:
        return {
            "npn": uuid.uuid4().hex[:10],
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "broker_dealer": "",
            "license_states": [],
            "status": "pending",
            "document_url": f"s3://{bucket}/{file_key}",
        }
