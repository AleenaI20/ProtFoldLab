"""
utils/esmfold.py
Protein structure prediction via ESMFold.
Endpoint: https://api.esmatlas.com/foldSequence/v1/pdb/
  - Completely free, no API key, no authentication
  - Server limit: 400 aa per request
  - Longer sequences are split into overlapping chunks
Uses stdlib urllib only.
"""

import os, re, time
import numpy as np
from urllib.request import urlopen, Request
from urllib.error import URLError
from typing import Optional

ESMFOLD_URL = "https://api.esmatlas.com/foldSequence/v1/pdb/"
MAX_LEN     = 400   # server hard limit
OVERLAP     = 20    # overlap between chunks for long sequences
VALID_AA    = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")


def validate_sequence(sequence: str) -> tuple[bool, str]:
    seq = sequence.strip().upper()
    # Remove whitespace/numbers (common in pasted sequences)
    seq = re.sub(r"[\s\d]", "", seq)
    if not seq:
        return False, "Sequence is empty."
    invalid = set(seq) - set("ACDEFGHIKLMNPQRSTVWY")
    if invalid:
        return False, f"Invalid characters: {', '.join(sorted(invalid))}"
    return True, ""


def clean_sequence(sequence: str) -> str:
    """Strip whitespace, numbers, and convert to uppercase."""
    return re.sub(r"[\s\d]", "", sequence.strip().upper())


def predict_structure(sequence: str) -> dict:
    """
    Fold a protein sequence using ESMFold (free, no key).
    Handles chunking for sequences > 400 aa.
    Returns: {pdb_string, mean_plddt, ptm, per_residue_plddt, chunks}
    """
    seq = clean_sequence(sequence)
    chunks = _make_chunks(seq)
    pdb_parts = []

    for i, (label, chunk) in enumerate(chunks):
        print(f"  Chunk {i+1}/{len(chunks)}: {label} ({len(chunk)} aa)")
        pdb = _post(chunk)
        pdb_parts.append((label, pdb))
        if i < len(chunks) - 1:
            time.sleep(3)  # polite pause between chunks

    # For single chunk, return directly; for multi-chunk, merge
    if len(pdb_parts) == 1:
        pdb_string = pdb_parts[0][1]
    else:
        pdb_string = _merge_pdbs(pdb_parts)

    mean_plddt, per_res = _extract_plddt(pdb_string)
    ptm = _extract_ptm(pdb_string)

    return {
        "pdb_string":        pdb_string,
        "mean_plddt":        mean_plddt,
        "ptm":               ptm,
        "per_residue_plddt": per_res,
        "n_chunks":          len(chunks),
        "sequence_length":   len(seq),
    }


def plddt_label(score: float) -> str:
    if score >= 90: return "Very high (≥90) — confident within ~1 Å"
    if score >= 70: return "High (70–90) — reliable backbone"
    if score >= 50: return "Medium (50–70) — correct topology, uncertain side-chains"
    return "Low (<50) — likely disordered or unreliable region"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _make_chunks(seq: str, max_len: int = MAX_LEN, overlap: int = OVERLAP) -> list[tuple[str, str]]:
    if len(seq) <= max_len:
        return [("full", seq)]
    parts, step, i, idx = [], max_len - overlap, 0, 1
    while i < len(seq):
        end = min(i + max_len, len(seq))
        parts.append((f"part{idx}", seq[i:end]))
        if end == len(seq):
            break
        i += step
        idx += 1
    return parts


def _post(seq: str, retries: int = 3) -> str:
    """POST sequence to ESMFold. Returns PDB text."""
    req = Request(
        ESMFOLD_URL,
        data=seq.encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ProtFoldLab/3.0",
        },
        method="POST",
    )
    for attempt in range(1, retries + 1):
        try:
            with urlopen(req, timeout=180) as r:
                pdb = r.read().decode("utf-8")
            if "ATOM" not in pdb:
                raise ValueError(f"Not a valid PDB response: {pdb[:200]}")
            return pdb
        except (URLError, OSError, ValueError) as e:
            if attempt < retries:
                print(f"    Attempt {attempt} failed: {e} — retrying in 10s")
                time.sleep(10)
            else:
                raise RuntimeError(f"ESMFold failed after {retries} attempts: {e}")


def _merge_pdbs(pdb_parts: list[tuple[str, str]]) -> str:
    """
    Simple merge of multiple PDB chunks.
    Each chunk gets its own chain (A, B, C...).
    Note: For proper structural analysis, use the individual chunk PDBs.
    """
    merged = []
    chain_ids = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    atom_serial = 1
    for i, (label, pdb) in enumerate(pdb_parts):
        chain = chain_ids[i % len(chain_ids)]
        merged.append(f"REMARK  Chunk {i+1}: {label}")
        for line in pdb.splitlines():
            if line.startswith("ATOM") or line.startswith("HETATM"):
                # Replace chain ID
                line = line[:21] + chain + line[22:]
                # Renumber atoms
                line = line[:6] + f"{atom_serial:5d}" + line[11:]
                atom_serial += 1
                merged.append(line)
        merged.append("TER")
    merged.append("END")
    return "\n".join(merged)


def _extract_plddt(pdb_string: str) -> tuple[float, list[float]]:
    per_res, seen = [], set()
    for line in pdb_string.splitlines():
        if not line.startswith("ATOM") or line[12:16].strip() != "CA":
            continue
        key = (line[21], line[22:26].strip())
        if key in seen:
            continue
        seen.add(key)
        try:
            val = float(line[60:66].strip())
            per_res.append(val)
        except ValueError:
            pass
    if not per_res:
        return 0.0, []

    # ESM Atlas returns pLDDT on 0–1 scale; convert to 0–100
    if max(per_res) <= 1.0:
        per_res = [v * 100 for v in per_res]

    return round(float(np.mean(per_res)), 2), per_res


def _extract_ptm(pdb_string: str) -> Optional[float]:
    # ESM Atlas encodes pTM in REMARK lines e.g.:
    # REMARK  pTM: 0.832   or   REMARK  predicted_tm_score: 0.832
    for line in pdb_string.splitlines():
        low = line.lower()
        if "ptm" in low or "predicted_tm" in low or "tm_score" in low:
            # Try to extract any float from the line
            matches = re.findall(r"[\d]+\.[\d]+", line)
            if matches:
                val = float(matches[-1])
                # pTM is always 0–1
                if 0.0 <= val <= 1.0:
                    return round(val, 3)
    return None
