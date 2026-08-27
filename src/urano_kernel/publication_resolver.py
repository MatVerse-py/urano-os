"""Lawful scientific-publication resolver for the URANO local bridge.

Design goals:
- stdlib-only;
- resolve DOI metadata without scraping publisher HTML;
- prefer legal open-access locations and repository copies;
- never bypass paywalls, CAPTCHAs, authentication, robots, or access controls;
- emit explicit access states and analysis handoffs for connected research tools.

Environment:
- UNPAYWALL_EMAIL: optional. Enables Unpaywall lookup when configured.
- CROSSREF_MAILTO: optional. Identifies the client to Crossref's polite pool.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
USER_AGENT = "MatVerse-URANO-PublicationBridge/1.0"
TIMEOUT_SECONDS = 12


@dataclass(frozen=True)
class AccessLocation:
    source: str
    url: str
    kind: str
    version: str | None = None
    license: str | None = None
    is_open_access: bool = False


class ResolverError(RuntimeError):
    pass


def extract_doi(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = DOI_RE.search(value.strip())
    if not match:
        return None
    return match.group(0).rstrip(".,;:)]}").lower()


def _json_get(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    req = Request(url, headers=request_headers, method="GET")
    try:
        with urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read()
    except HTTPError as exc:
        raise ResolverError(f"http_{exc.code}") from exc
    except URLError as exc:
        raise ResolverError("network_error") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResolverError("invalid_json") from exc
    if not isinstance(data, dict):
        raise ResolverError("unexpected_payload")
    return data


def _crossref(doi: str) -> dict[str, Any]:
    mailto = os.environ.get("CROSSREF_MAILTO", "").strip()
    suffix = "?" + urlencode({"mailto": mailto}) if mailto else ""
    data = _json_get(f"https://api.crossref.org/works/{quote(doi, safe='')}{suffix}")
    message = data.get("message")
    return message if isinstance(message, dict) else {}


def _openalex(doi: str) -> dict[str, Any]:
    canonical = f"https://doi.org/{doi}"
    params = urlencode({"filter": f"doi:{canonical}", "per-page": 1})
    data = _json_get(f"https://api.openalex.org/works?{params}")
    results = data.get("results")
    if isinstance(results, list) and results and isinstance(results[0], dict):
        return results[0]
    return {}


def _unpaywall(doi: str) -> dict[str, Any]:
    email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if not email:
        return {}
    params = urlencode({"email": email})
    return _json_get(f"https://api.unpaywall.org/v2/{quote(doi, safe='/')}?{params}")


def _first_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def _authors_from_crossref(record: dict[str, Any]) -> list[str]:
    authors: list[str] = []
    for item in record.get("author", []) if isinstance(record.get("author"), list) else []:
        if not isinstance(item, dict):
            continue
        given = str(item.get("given") or "").strip()
        family = str(item.get("family") or "").strip()
        name = " ".join(part for part in (given, family) if part)
        if name:
            authors.append(name)
    return authors


def _locations_from_openalex(record: dict[str, Any]) -> list[AccessLocation]:
    locations: list[AccessLocation] = []
    raw_locations = record.get("locations")
    if not isinstance(raw_locations, list):
        return locations
    for item in raw_locations:
        if not isinstance(item, dict) or not item.get("is_oa"):
            continue
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        host = str(source.get("display_name") or source.get("host_organization_name") or "OpenAlex location")
        version = item.get("version") if isinstance(item.get("version"), str) else None
        license_value = item.get("license") if isinstance(item.get("license"), str) else None
        pdf_url = item.get("pdf_url") if isinstance(item.get("pdf_url"), str) else None
        landing = item.get("landing_page_url") if isinstance(item.get("landing_page_url"), str) else None
        if pdf_url:
            locations.append(AccessLocation(host, pdf_url, "pdf", version, license_value, True))
        if landing and landing != pdf_url:
            locations.append(AccessLocation(host, landing, "landing_page", version, license_value, True))
    return locations


def _locations_from_unpaywall(record: dict[str, Any]) -> list[AccessLocation]:
    locations: list[AccessLocation] = []
    raw = record.get("oa_locations")
    if not isinstance(raw, list):
        return locations
    for item in raw:
        if not isinstance(item, dict):
            continue
        host = str(item.get("host_type") or "Unpaywall")
        version = item.get("version") if isinstance(item.get("version"), str) else None
        license_value = item.get("license") if isinstance(item.get("license"), str) else None
        pdf_url = item.get("url_for_pdf") if isinstance(item.get("url_for_pdf"), str) else None
        landing = item.get("url_for_landing_page") if isinstance(item.get("url_for_landing_page"), str) else None
        if pdf_url:
            locations.append(AccessLocation(host, pdf_url, "pdf", version, license_value, True))
        if landing and landing != pdf_url:
            locations.append(AccessLocation(host, landing, "landing_page", version, license_value, True))
    return locations


def _dedupe_locations(locations: list[AccessLocation]) -> list[AccessLocation]:
    seen: set[str] = set()
    result: list[AccessLocation] = []
    for location in locations:
        if location.url in seen:
            continue
        seen.add(location.url)
        result.append(location)
    return result


def resolve_publication(value: str) -> dict[str, Any]:
    doi = extract_doi(value)
    if not doi:
        return {
            "ok": False,
            "access_state": "IDENTIFIER_REQUIRED",
            "error": "No DOI found. Supply a DOI or a URL containing a DOI.",
            "input": value,
        }

    errors: dict[str, str] = {}
    crossref: dict[str, Any] = {}
    openalex: dict[str, Any] = {}
    unpaywall: dict[str, Any] = {}

    for name, fn in (("crossref", _crossref), ("openalex", _openalex), ("unpaywall", _unpaywall)):
        try:
            result = fn(doi)
        except ResolverError as exc:
            errors[name] = str(exc)
            result = {}
        if name == "crossref":
            crossref = result
        elif name == "openalex":
            openalex = result
        else:
            unpaywall = result

    title = _first_text(crossref.get("title")) or _first_text(openalex.get("title"))
    journal = _first_text(crossref.get("container-title"))
    authors = _authors_from_crossref(crossref)
    published = crossref.get("published") or crossref.get("published-print") or crossref.get("published-online")

    locations = _dedupe_locations(
        _locations_from_openalex(openalex) + _locations_from_unpaywall(unpaywall)
    )
    oa_urls = [asdict(location) for location in locations]

    primary_url = f"https://doi.org/{doi}"
    if locations:
        access_state = "OPEN_ACCESS_FOUND"
    elif crossref or openalex:
        access_state = "METADATA_ONLY_OR_RESTRICTED"
    else:
        access_state = "UNRESOLVED"

    query = title or doi
    analysis_handoffs = [
        {
            "id": "consensus",
            "kind": "plugin",
            "operation": "paper_search",
            "query": query,
            "note": "Invoke through the connected Consensus tool in ChatGPT; the local bridge does not impersonate connector authentication.",
        },
        {
            "id": "hugging_face",
            "kind": "plugin",
            "operation": "paper_search",
            "query": query,
            "note": "Use for related ML papers/models/datasets when applicable.",
        },
        {
            "id": "github",
            "kind": "connector",
            "operation": "search",
            "query": f'"{doi}" {title or ""}'.strip(),
            "note": "Search for code, replication packages, issues, or artifacts linked to the publication.",
        },
        {
            "id": "google_drive",
            "kind": "connector",
            "operation": "search",
            "query": title or doi,
            "note": "Search the user-authorized corpus for prior analyses or local copies.",
        },
    ]

    return {
        "ok": bool(crossref or openalex or unpaywall),
        "input": value,
        "doi": doi,
        "canonical_url": primary_url,
        "access_state": access_state,
        "policy": {
            "bypass_paywall": False,
            "bypass_captcha": False,
            "bypass_authentication": False,
            "strategy": "metadata_api_then_legal_open_access_location_then_user_authorized_access",
        },
        "metadata": {
            "title": title,
            "journal": journal,
            "authors": authors,
            "published": published,
            "type": crossref.get("type"),
            "publisher": crossref.get("publisher"),
            "abstract": crossref.get("abstract"),
            "is_open_access": bool(locations),
            "openalex_id": openalex.get("id"),
        },
        "access_locations": oa_urls,
        "analysis_links": {
            "doi": primary_url,
            "crossref_api": f"https://api.crossref.org/works/{quote(doi, safe='')}",
            "openalex_search": "https://api.openalex.org/works?" + urlencode({"filter": f"doi:https://doi.org/{doi}"}),
            "google_scholar": "https://scholar.google.com/scholar?" + urlencode({"q": doi}),
        },
        "analysis_handoffs": analysis_handoffs,
        "resolver_errors": errors,
    }
