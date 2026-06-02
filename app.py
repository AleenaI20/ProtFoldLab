"""
ProtFoldLab — Agentic Protein Folding & Chimeric Design Lab
Works on: Hugging Face Spaces, Streamlit Cloud, or locally.
Keys loaded server-side — users never see or enter them.
"""

import os
import streamlit as st

st.set_page_config(
    page_title="ProtFoldLab",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load secrets (HF Spaces env vars OR Streamlit secrets) ───────────────────
def _get_secret(key: str) -> str:
    """Try Streamlit secrets first, then environment variables (HF Spaces)."""
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")

GEMINI_KEY = _get_secret("GEMINI_API_KEY")
ESM_KEY    = _get_secret("ESM_FORGE_KEY")

st.session_state["gemini_key"] = GEMINI_KEY
st.session_state["esm_key"]    = ESM_KEY

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🧬 ProtFoldLab")
    st.caption("Agentic Protein Folding & Chimeric Design")
    st.divider()
    st.markdown(
        "**Powered by (all free)**\n"
        "- 🔬 ESMFold — Meta AI / ESM Atlas\n"
        "- 🧬 ESM3 — EvolutionaryScale Forge\n"
        "- 🤖 Gemini Flash — Google AI\n"
        "- 📦 UniProt REST API\n"
    )
    st.divider()
    st.markdown("**No sign-up required.** Just describe your protein and run.")
    st.divider()
    st.caption("ProtFoldLab v3.0")

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("# 🧬 ProtFoldLab")
st.markdown("**Agentic Protein Structure Prediction & Chimeric Design**")
st.divider()

mode = st.radio(
    "Choose workflow:",
    [
        "🔬 Natural Protein — predict structure from UniProt",
        "🧪 Chimeric Protein — design & fold with ESM3 + ESMFold",
    ],
    horizontal=True,
)

if mode.startswith("🔬"):
    from pages import natural_protein
    natural_protein.render()
else:
    from pages import chimeric_protein
    chimeric_protein.render()
