"""
onet_client.py

A tiny, defensive client for the O*NET Web Services API (v2). Used by the
architecture generator to enrich a role with the competencies the U.S.
Department of Labor's O*NET database rates as important for that occupation.

O*NET data is licensed Creative Commons Attribution 4.0 - free for commercial
use with attribution. This client requires a free API key (username) from
https://services.onetcenter.org/developer/signup.

Every function fails soft: if there is no key, no network, or no match, it
returns None or an empty list rather than raising, so the generator can always
fall back to the local knowledge base.
"""

import urllib.request
import urllib.parse
import json
import base64

BASE = "https://api-v2.onetcenter.org"


def _get(path, api_key, timeout=6):
    """Authenticated GET returning parsed JSON, or None on any failure."""
    if not api_key:
        return None
    url = f"{BASE}/{path}"
    # O*NET uses HTTP Basic auth; the API key is the username, password blank.
    token = base64.b64encode(f"{api_key}:".encode()).decode()
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "User-Agent": "hiring-process-architecture-audit",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def find_occupation(role_title, api_key):
    """Resolve a free-text role title to the best-matching O*NET occupation.
    Returns {'code', 'title'} or None."""
    if not role_title or not api_key:
        return None
    q = urllib.parse.quote(role_title)
    data = _get(f"online/search?keyword={q}&end=1", api_key)
    if not data:
        return None
    occ = data.get("occupation") or []
    if not occ:
        return None
    first = occ[0]
    return {"code": first.get("code"), "title": first.get("title")}


def important_skills(soc_code, api_key, top_n=8):
    """Return the most important skills for an occupation as a list of
    {'name', 'importance'}, highest first. Empty list on any failure."""
    if not soc_code or not api_key:
        return []
    data = _get(f"online/occupations/{soc_code}/details/skills?end={top_n}", api_key)
    if not data:
        return []
    out = []
    for el in data.get("element", []):
        out.append({"name": el.get("name", ""), "importance": el.get("importance")})
    return out


def enrich_role(role_title, api_key, top_n=8):
    """Convenience: resolve a role and return its important skills together.
    Returns {'occupation', 'skills'} where either may be empty/None on failure."""
    occ = find_occupation(role_title, api_key)
    if not occ:
        return {"occupation": None, "skills": []}
    skills = important_skills(occ["code"], api_key, top_n)
    return {"occupation": occ, "skills": skills}
