"""
utils/agent.py
Gemini Flash (Google AI) — free tier, no credit card.
Used for:
  1. Parsing chimeric protein descriptions → structured domain segments
  2. Interpreting ESMFold results for natural proteins
  3. Interpreting chimeric design pipeline results

Key stored server-side in Streamlit secrets. Users never see it.
"""

import json, re
import urllib.request, urllib.error
from typing import Optional

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


def _call_gemini(prompt: str, system: str, api_key: str, max_tokens: int = 1500) -> str:
    """Call Gemini Flash API. Returns response text."""
    import json as _json
    body = _json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
    }).encode()
    req = urllib.request.Request(
        f"{GEMINI_URL}?key={api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = _json.loads(r.read().decode())
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini API error {e.code}: {e.read().decode()[:300]}")


# ── Chimeric prompt parsing ───────────────────────────────────────────────────

CHIMERIC_SYSTEM = """You are a protein engineering AI. Parse the user's chimeric protein 
description into structured JSON. Return ONLY a valid JSON array, no markdown, no commentary.

Each element must be:
{
  "label": "short descriptive name",
  "species": "human / C. elegans / mouse / etc.",
  "protein": "protein name",
  "domain": "domain or region e.g. ECD, TM1-TM4, SAP domain, latch",
  "uniprot_accession": "UniProt accession if known, else empty string",
  "residue_start": null or integer (1-indexed),
  "residue_end": null or integer (1-indexed),
  "notes": "any design notes"
}

Known accessions:
- Human alpha7 nAChR / CHRNA7: P36544 (ECD ~1-236, TM1-TM4 ~237-480)
- C. elegans unc-29: P12364 (latch ~170-210)
- C. elegans RIC-3: Q21375
- Human RIC-3: Q7Z7B1
- Human GluA2 AMPA receptor: P42262
- Human ACE2: Q9BYF1
- Human ASIC1a: P78348"""


def parse_chimeric_prompt(user_prompt: str, api_key: str) -> list[dict]:
    raw = _call_gemini(user_prompt, CHIMERIC_SYSTEM, api_key, max_tokens=800)
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


# ── Natural protein interpretation ────────────────────────────────────────────

NATURAL_SYSTEM = """You are an expert structural biologist interpreting ESMFold 
protein structure prediction results. Be clear, accurate, and concise.

Structure your response with exactly these headers:
## 🔬 Overall Assessment
## 📊 Confidence Scores Explained  
## 🧩 Structural Regions
## 💡 Biological Implications
## ⚠️ Caveats & Recommendations

3-5 sentences per section. No excessive bullet points."""


def interpret_structure(
    protein_name: str, sequence: str,
    mean_plddt: float, ptm: Optional[float],
    per_residue_plddt: list[float],
    api_key: str, organism: str = "", function_hint: str = "",
) -> str:
    prompt = f"""
Protein: {protein_name}
Organism: {organism or 'Unknown'}
Length: {len(sequence)} aa
Function: {function_hint or 'Not provided'}

ESMFold results:
- Mean pLDDT: {mean_plddt:.1f}/100
- pTM: {f"{ptm:.3f}" if ptm is not None else "N/A"}

Per-residue pLDDT summary:
{_plddt_summary(per_residue_plddt)}
""".strip()
    return _call_gemini(prompt, NATURAL_SYSTEM, api_key, max_tokens=1200)


# ── Chimeric design interpretation ────────────────────────────────────────────

CHIMERIC_SYSTEM_INTERP = """You are an expert in chimeric protein design and structural biology.
Analyse results from an ESM3-designed + ESMFold-validated chimeric protein pipeline.

Structure your response with:
## 🏗️ Chimeric Architecture Summary
## 📊 ESMFold Confidence Analysis
## 🔗 Junction & Linker Analysis
## 🧬 ESM3 Design Assessment
## 💡 Functional Predictions
## ⚠️ Design Caveats & Next Steps

Be specific about which domains are well-folded vs disordered, 
and whether junctions appear structurally compatible."""


def interpret_chimeric_design(
    segments: list[dict], linker_sequences: list[str],
    full_sequence: str, mean_plddt: float,
    ptm: Optional[float], per_residue_plddt: list[float],
    api_key: str,
) -> str:
    seg_text = "\n".join(
        f"- {s.get('label','?')} ({s.get('species','?')} {s.get('protein','?')}, "
        f"{s.get('domain','?')}): chimera residues {s.get('actual_start','?')}–{s.get('actual_end','?')}"
        for s in segments
    )
    linker_text = "\n".join(
        f"  Linker {i+1}: {lk} ({len(lk)} aa)"
        for i, lk in enumerate(linker_sequences)
    ) if linker_sequences else "  None (direct concatenation)"

    prompt = f"""
Chimeric protein from:
{seg_text}

ESM3-designed linkers:
{linker_text}

Total: {len(full_sequence)} aa

ESMFold:
- Mean pLDDT: {mean_plddt:.1f}/100
- pTM: {f"{ptm:.3f}" if ptm is not None else "N/A"}

pLDDT profile:
{_plddt_summary(per_residue_plddt)}
""".strip()
    return _call_gemini(prompt, CHIMERIC_SYSTEM_INTERP, api_key, max_tokens=1400)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _plddt_summary(per_residue: list[float], n_bins: int = 10) -> str:
    if not per_residue:
        return "No data."
    n = len(per_residue)
    bin_size = max(1, n // n_bins)
    lines = []
    for i in range(0, n, bin_size):
        chunk = per_residue[i: i + bin_size]
        avg = sum(chunk) / len(chunk)
        end = min(i + bin_size, n)
        icon = "🟦" if avg >= 90 else "🟩" if avg >= 70 else "🟨" if avg >= 50 else "🟥"
        lines.append(f"  {i+1:4d}–{end:4d}: {avg:5.1f}  {icon * int(avg/10)}{'⬜' * (10 - int(avg/10))}")
    return "\n".join(lines)
