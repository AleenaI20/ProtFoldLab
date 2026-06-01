"""
utils/esm3_design.py
ESM3 via EvolutionaryScale Forge — linker design & sequence generation.
Free research tier. Key stored server-side in Streamlit secrets.
Install: pip install esm
"""

from __future__ import annotations

MASK         = "_"
ESM3_MODEL   = "esm3-medium-2024-08"
FORGE_URL    = "https://forge.evolutionaryscale.ai"


def _client(token: str):
    try:
        from esm.sdk.forge import ESM3ForgeInferenceClient
    except ImportError:
        raise ImportError("Install ESM3: pip install esm")
    return ESM3ForgeInferenceClient(model=ESM3_MODEL, url=FORGE_URL, token=token)


def design_linkers(
    segments: list[dict],
    linker_lengths: list[int],
    token: str,
    num_designs: int = 3,
) -> list[dict]:
    """
    Design junction linker sequences between domain segments using ESM3
    masked language modelling.

    Args:
        segments:       list of dicts each with 'sub_sequence'
        linker_lengths: list of ints (one per junction), len = len(segments)-1
        token:          ESM3 Forge API token
        num_designs:    number of independent designs

    Returns:
        list of dicts: {design_id, full_sequence, linker_sequences}
    """
    try:
        from esm.sdk.api import ESMProtein, GenerationConfig
    except ImportError:
        raise ImportError("Install ESM3: pip install esm")

    client = _client(token)

    # Build masked scaffold
    scaffold_parts = []
    for i, seg in enumerate(segments):
        scaffold_parts.append(seg["sub_sequence"])
        if i < len(linker_lengths) and linker_lengths[i] > 0:
            scaffold_parts.append(MASK * linker_lengths[i])
    scaffold = "".join(scaffold_parts)

    designs = []
    for design_id in range(num_designs):
        result = client.generate(
            ESMProtein(sequence=scaffold),
            GenerationConfig(
                track="sequence",
                num_steps=max(8, len(scaffold) // 10),
                temperature=0.7,
            ),
        )
        full_seq = result.sequence

        # Extract linker sequences from generated output
        linkers, pos = [], 0
        for i, seg in enumerate(segments):
            pos += len(seg["sub_sequence"])
            if i < len(linker_lengths) and linker_lengths[i] > 0:
                linkers.append(full_seq[pos: pos + linker_lengths[i]])
                pos += linker_lengths[i]

        designs.append({
            "design_id": design_id,
            "full_sequence": full_seq,
            "linker_sequences": linkers,
        })

    return designs


def generate_variants(
    seed_sequence: str, token: str,
    num_variants: int = 3, mask_fraction: float = 0.15,
) -> list[dict]:
    """
    Randomly mask residues in a sequence and let ESM3 redesign them.
    Useful for optimising a hard-concatenated chimera.
    """
    try:
        from esm.sdk.api import ESMProtein, GenerationConfig
        import random
    except ImportError:
        raise ImportError("Install ESM3: pip install esm")

    client = _client(token)
    n = len(seed_sequence)
    n_mask = max(1, int(n * mask_fraction))
    variants = []

    for vid in range(num_variants):
        seq_list = list(seed_sequence)
        for pos in random.sample(range(n), n_mask):
            seq_list[pos] = MASK
        result = client.generate(
            ESMProtein(sequence="".join(seq_list)),
            GenerationConfig(track="sequence", num_steps=max(6, n_mask // 2), temperature=0.5),
        )
        variants.append({"variant_id": vid, "sequence": result.sequence})

    return variants
