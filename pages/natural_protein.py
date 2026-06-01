"""
pages/natural_protein.py
Workflow: UniProt search → fetch → ESMFold (free, no key) → Gemini interprets
"""

import streamlit as st
import pandas as pd
from utils import uniprot, esmfold, agent
from utils.viewer import show_fold_results


def render():
    st.markdown("## 🔬 Natural Protein — Structure Prediction")
    st.markdown(
        "Search UniProt, pick a protein, and predict its 3D structure with "
        "**ESMFold** (free, no API key). Gemini AI interprets the results."
    )

    # Step 1: Search
    st.markdown("### Step 1 — Search UniProt")
    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("Search by name, gene, or accession",
                              placeholder="e.g.  human alpha7 nAChR  /  CHRNA7  /  P36544")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Search", use_container_width=True) and query:
            with st.spinner("Searching UniProt…"):
                try:
                    st.session_state["nat_results"] = uniprot.search_uniprot(query)
                except Exception as e:
                    st.error(f"Search failed: {e}")

    if st.session_state.get("nat_results"):
        df = pd.DataFrame(st.session_state["nat_results"]).rename(columns={
            "accession":"Accession","name":"Protein","organism":"Organism",
            "length":"Length (aa)","reviewed":"Swiss-Prot"
        })
        df["Swiss-Prot"] = df["Swiss-Prot"].map({True:"✅",False:""})
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Step 2: Fetch
    st.markdown("### Step 2 — Fetch sequence")
    c1, c2 = st.columns([3, 1])
    with c1:
        acc = st.text_input("UniProt Accession", placeholder="e.g. P36544",
                            value=st.session_state.get("nat_acc",""))
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📥 Fetch", use_container_width=True) and acc:
            st.session_state["nat_acc"] = acc.strip().upper()
            with st.spinner(f"Fetching {acc.strip().upper()}…"):
                try:
                    st.session_state["nat_prot"] = uniprot.fetch_sequence(acc.strip())
                    st.session_state.pop("nat_result", None)
                except Exception as e:
                    st.error(f"Fetch failed: {e}")

    prot = st.session_state.get("nat_prot")
    if not prot:
        return

    st.success(f"**{prot['name']}** · *{prot['organism']}* · {prot['length']} aa")
    with st.expander("Show sequence"):
        st.code(prot["sequence"])
    if prot.get("function"):
        with st.expander("UniProt function"):
            st.write(prot["function"])

    # Handle long sequences via chunking
    seq = prot["sequence"]
    if prot["length"] > esmfold.MAX_LEN:
        st.info(
            f"ℹ️ Sequence is {prot['length']} aa. ESMFold server limit is {esmfold.MAX_LEN} aa. "
            f"The sequence will be automatically split into overlapping chunks and folded separately."
        )
    fold_seq = seq

    # Step 3: Predict
    st.markdown("### Step 3 — Predict & interpret")
    if st.button("🚀 Run ESMFold", type="primary", use_container_width=True):
        _run(fold_seq, prot)
    elif "nat_result" in st.session_state:
        show_fold_results(
            st.session_state["nat_result"], prot["name"], fold_seq,
            st.session_state.get("nat_interp",""),
        )


def _run(seq, prot):
    valid, err = esmfold.validate_sequence(seq)
    if not valid:
        st.error(f"Sequence issue: {err}")
        return

    with st.spinner("🔬 ESMFold predicting structure (free API, ~1–3 min per chunk)…"):
        try:
            result = esmfold.predict_structure(seq)
            st.session_state["nat_result"] = result
        except Exception as e:
            st.error(f"ESMFold failed: {e}")
            return

    gemini_key = st.session_state.get("gemini_key","")
    if gemini_key:
        with st.spinner("🤖 Gemini interpreting results…"):
            try:
                interp = agent.interpret_structure(
                    protein_name=prot["name"], sequence=seq,
                    mean_plddt=result["mean_plddt"], ptm=result.get("ptm"),
                    per_residue_plddt=result["per_residue_plddt"],
                    api_key=gemini_key, organism=prot.get("organism",""),
                    function_hint=prot.get("function",""),
                )
            except Exception as e:
                interp = f"*(AI interpretation unavailable: {e})*"
    else:
        interp = "*(Gemini key not configured — add GEMINI_API_KEY to Streamlit secrets)*"

    st.session_state["nat_interp"] = interp
    show_fold_results(result, prot["name"], seq, interp)
