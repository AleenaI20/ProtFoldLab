"""
ProtFoldLab — Agentic Protein Folding & Chimeric Design Lab
============================================================
APIs (all free, keys stored server-side in Streamlit secrets):
  - ESMFold   : api.esmatlas.com  (no key needed at all)
  - ESM3      : forge.evolutionaryscale.ai (free key, server-side)
  - Gemini    : generativelanguage.googleapis.com (free key, server-side)
  - UniProt   : rest.uniprot.org  (no key needed at all)
"""

import streamlit as st

st.set_page_config(
    page_title="ProtFoldLab",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load server-side secrets (invisible to users) ─────────────────────────────
try:
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    ESM_KEY    = st.secrets["ESM_FORGE_KEY"]
except Exception:
    # Fallback for local dev: set these in .streamlit/secrets.toml
    GEMINI_KEY = ""
    ESM_KEY    = ""

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
        "- ⚙️ ProteinMPNN — NVIDIA NIM\n"
    )
    st.divider()
    st.markdown(
        "**No sign-up required.** "
        "Just describe your protein and run."
    )
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
