"""
utils/uniprot.py
Fetch protein sequences from UniProt REST API.
Uses stdlib urllib only — no extra dependencies.
"""

import os, time
from io import StringIO
from urllib.request import urlopen, Request
from urllib.error import URLError

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"
HEADERS = {"User-Agent": "ProtFoldLab/3.0"}


def _get(url: str, retries: int = 3) -> str:
    req = Request(url, headers=HEADERS)
    for attempt in range(1, retries + 1):
        try:
            with urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8").strip()
        except (URLError, OSError) as e:
            if attempt < retries:
                time.sleep(3)
            else:
                raise


def search_uniprot(query: str, max_results: int = 8) -> list[dict]:
    """Search UniProt, return list of {accession, name, organism, length, reviewed}."""
    import json, urllib.parse
    params = urllib.parse.urlencode({
        "query": query, "format": "json",
        "size": max_results,
        "fields": "accession,protein_name,organism_name,length,reviewed",
    })
    raw = _get(f"{UNIPROT_BASE}/search?{params}")
    data = json.loads(raw)
    parsed = []
    for r in data.get("results", []):
        try:
            name = (
                r.get("proteinDescription", {})
                .get("recommendedName", {})
                .get("fullName", {}).get("value", "")
                or r.get("proteinDescription", {})
                .get("submittedName", [{}])[0]
                .get("fullName", {}).get("value", "Unknown")
            )
            parsed.append({
                "accession": r["primaryAccession"],
                "name": name,
                "organism": r.get("organism", {}).get("scientificName", ""),
                "length": r.get("sequence", {}).get("length", 0),
                "reviewed": r.get("entryType", "") == "UniProtKB reviewed (Swiss-Prot)",
            })
        except Exception:
            continue
    return parsed


def fetch_sequence(accession: str) -> dict:
    """Fetch full sequence + metadata for a UniProt accession."""
    import json
    accession = accession.strip().upper()
    raw = _get(f"{UNIPROT_BASE}/{accession}?format=json")
    data = json.loads(raw)

    try:
        name = data["proteinDescription"]["recommendedName"]["fullName"]["value"]
    except (KeyError, TypeError):
        try:
            name = data["proteinDescription"]["submittedName"][0]["fullName"]["value"]
        except Exception:
            name = accession

    function_text = ""
    for comment in data.get("comments", []):
        if comment.get("commentType") == "FUNCTION":
            texts = comment.get("texts", [])
            if texts:
                function_text = texts[0].get("value", "")
                break

    return {
        "accession": accession,
        "name": name,
        "organism": data.get("organism", {}).get("scientificName", ""),
        "sequence": data.get("sequence", {}).get("value", ""),
        "length": data.get("sequence", {}).get("length", 0),
        "function": function_text,
    }


def fetch_fasta(accession: str) -> str:
    """Return raw FASTA string."""
    return _get(f"{UNIPROT_BASE}/{accession.strip().upper()}.fasta")


def extract_domain(sequence: str, start: int, end: int) -> str:
    """Extract subsequence (1-indexed, inclusive)."""
    return sequence[start - 1: end]
