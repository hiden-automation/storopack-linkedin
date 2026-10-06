"""Cliente mínimo do produto gratuito "Share on LinkedIn" (escopo w_member_social)."""

from pathlib import Path

import requests

from . import config

API = "https://api.linkedin.com/v2"


class LinkedInError(RuntimeError):
    pass


def _headers() -> dict:
    if not config.LINKEDIN_ACCESS_TOKEN or not config.LINKEDIN_PERSON_URN:
        raise LinkedInError("LINKEDIN_ACCESS_TOKEN e LINKEDIN_PERSON_URN são obrigatórios")
    return {
        "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _check(resp: requests.Response, what: str) -> requests.Response:
    if resp.status_code >= 400:
        hint = " (token expirado? rode scripts/linkedin_auth.py)" if resp.status_code == 401 else ""
        raise LinkedInError(f"{what}: HTTP {resp.status_code} {resp.text[:400]}{hint}")
    return resp


def upload_image(path: Path) -> str:
    body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": config.LINKEDIN_PERSON_URN,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ],
        }
    }
    resp = _check(
        requests.post(f"{API}/assets?action=registerUpload", json=body, headers=_headers(), timeout=30),
        "registerUpload",
    )
    value = resp.json()["value"]
    upload_url = value["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    _check(
        requests.put(
            upload_url,
            data=path.read_bytes(),
            headers={"Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}", "Content-Type": "image/png"},
            timeout=120,
        ),
        "upload da imagem",
    )
    return value["asset"]


def create_image_post(text: str, asset: str, title: str) -> str:
    body = {
        "author": config.LINKEDIN_PERSON_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [{"status": "READY", "media": asset, "title": {"text": title}}],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    resp = _check(requests.post(f"{API}/ugcPosts", json=body, headers=_headers(), timeout=30), "ugcPosts")
    return resp.headers.get("X-RestLi-Id") or resp.json().get("id", "")
