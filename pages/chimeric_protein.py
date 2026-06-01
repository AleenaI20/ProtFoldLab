"""
pages/chimeric_protein.py
Full agentic chimeric design pipeline:
  Gemini parse → UniProt fetch → ESM3 linkers → ESMFold → Gemini interpret
All APIs free. Keys server-side only.
"""

import streamlit as st
import pandas as pd
from utils import uniprot, esmfold, agent, esm3_design
from utils.viewer import show_fold_results

EXAMPLES = [
    "Human alpha7 nAChR ECD + TM1-TM4 + SAP domain + C. elegans unc-29 latch",
    "Human GluA2 ligand-binding domain fused to ASIC1a transmembrane domain",
    "C. elegans RIC-3 chaperone domain fused to human alpha7 nAChR ECD",
]


def render():
    st.markdown("## 🧪 Chimeric Protein — Design & Predict")
    st.markdown(
        "Describe your chimeric protein in plain language. "
        "**Gemini** parses domains · **UniProt** fetches sequences · "
        "**ESM3** designs linkers · **ESMFold** predicts structure · "
        "**Gemini** interprets"
    )

    with st.expander("📋 Full pipeline"):
        st.code("""
[You] Plain language description
  ↓
[Gemini AI] Parse domains & UniProt accessions
  ↓
[UniProt REST] Fetch sequences (free, no key)
  ↓
[ESM3 Forge] Design optimal junction linkers   ← DESIGN
  ↓
Assemble: domain1 + linker1 + domain2 + ...
  ↓
[ESMFold] Predict 3D structure (free, no key)  ← PREDICT
  ↓
[Gemini AI] Interpret results
        """, language="")

    # Example prompts
    cols = st.columns(len(EXAMPLES))
    for i, (col, ex) in enumerate(zip(cols, EXAMPLES)):
        with col:
            if st.button(f"📋 Example {i+1}", key=f"ex{i}", use_container_width=True):
                st.session_state["chim_prompt"] = ex
                for k in ["chim_segs","chim_assembled","chim_designs",
                           "chim_result","chim_interp"]:
                    st.session_state.pop(k, None)

    # Step 1: Describe
    st.markdown("### Step 1 — Describe your chimeric protein")
    prompt = st.text_area("Description", value=st.session_state.get("chim_prompt",""),
                          height=80, placeholder=EXAMPLES[0])

    if st.button("🤖 Parse with Gemini AI", type="primary"):
        if not prompt.strip():
            st.warning("Enter a description first.")
            return
        gemini_key = st.session_state.get("gemini_key","")
        if not gemini_key:
            st.error("Gemini API key not configured in Streamlit secrets.")
            return
        st.session_state["chim_prompt"] = prompt
        for k in ["chim_segs","chim_assembled","chim_designs","chim_result","chim_interp"]:
            st.session_state.pop(k, None)
        with st.spinner("🤖 Gemini parsing description…"):
            try:
                segs = agent.parse_chimeric_prompt(prompt, gemini_key)
                st.session_state["chim_segs"] = segs
            except Exception as e:
                st.error(f"Parsing failed: {e}")
                return

    # Step 2: Review segments
    segs = st.session_state.get("chim_segs")
    if not segs:
        return

    st.markdown("### Step 2 — Review & edit domain segments")
    edited = []
    for i, seg in enumerate(segs):
        with st.expander(f"**Segment {i+1}: {seg.get('label','Domain')}**", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                label   = st.text_input("Label",          seg.get("label",""),            key=f"l{i}")
                species = st.text_input("Species",         seg.get("species",""),          key=f"sp{i}")
                protein = st.text_input("Protein",         seg.get("protein",""),          key=f"pr{i}")
            with c2:
                domain  = st.text_input("Domain/region",  seg.get("domain",""),           key=f"d{i}")
                acc     = st.text_input("UniProt accession", seg.get("uniprot_accession",""), key=f"a{i}")
                cs, ce  = st.columns(2)
                with cs:
                    rs = st.number_input("Start (0=full)", int(seg.get("residue_start") or 0), min_value=0, key=f"rs{i}")
                with ce:
                    re_ = st.number_input("End (0=full)",  int(seg.get("residue_end")   or 0), min_value=0, key=f"re{i}")
            edited.append({
                "label": label, "species": species, "protein": protein,
                "domain": domain, "uniprot_accession": acc.strip().upper(),
                "residue_start": int(rs) if rs > 0 else None,
                "residue_end":   int(re_) if re_ > 0 else None,
            })

    # Step 3: Linker settings
    st.markdown("### Step 3 — Linker & pipeline settings")
    n = len(edited)
    use_esm3 = st.toggle("Use ESM3 to design linker sequences", value=True,
                          help="Designs biologically plausible junction residues between domains")
    linker_lengths = []
    if n > 1:
        st.markdown("**Linker lengths (aa) between each domain pair:**")
        lcs = st.columns(n - 1)
        for i in range(n - 1):
            with lcs[i]:
                lk = st.number_input(f"Linker {i+1}→{i+2}", 0, 30, 5, key=f"lk{i}",
                                     help="0 = direct join, no linker")
                linker_lengths.append(int(lk))
    n_designs = st.slider("ESM3 linker designs to generate", 1, 5, 2) if use_esm3 else 1

    # Step 4: Run
    st.markdown("### Step 4 — Run full pipeline")
    if st.button("🚀 Run Full Pipeline", type="primary", use_container_width=True):
        _run_pipeline(edited, linker_lengths, use_esm3, n_designs)
    elif "chim_result" in st.session_state:
        _show_results()


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _run_pipeline(edited, linker_lengths, use_esm3, n_designs):
    gemini_key = st.session_state.get("gemini_key","")
    esm_key    = st.session_state.get("esm_key","")

    # 1. Fetch sequences
    with st.spinner("📥 Fetching sequences from UniProt…"):
        assembled = _fetch(edited)
        if not assembled:
            return
    st.session_state["chim_assembled"] = assembled
    _show_table(assembled["segments"])

    segs_with_seqs = assembled["segments"]
    linker_seqs = []

    # 2. ESM3 linker design
    if use_esm3 and esm_key and sum(linker_lengths) > 0:
        with st.spinner(f"🧬 ESM3 designing {n_designs} linker variant(s)…"):
            try:
                designs = esm3_design.design_linkers(
                    segs_with_seqs, linker_lengths, esm_key, n_designs
                )
                st.session_state["chim_designs"] = designs
                st.markdown("#### ESM3 Linker Designs")
                for d in designs:
                    with st.expander(f"Design {d['design_id']+1}"):
                        for j, lk in enumerate(d["linker_sequences"]):
                            st.code(f"Linker {j+1}: {lk}  ({len(lk)} aa)")

                chosen = 0
                if len(designs) > 1:
                    chosen = st.selectbox("Select design to fold", range(len(designs)),
                                          format_func=lambda i: f"Design {i+1}")
                linker_seqs = designs[chosen]["linker_sequences"]
                fold_seq = designs[chosen]["full_sequence"]
            except Exception as e:
                st.warning(f"ESM3 linker design failed ({e}). Using direct concatenation.")
                fold_seq = "".join(s["sub_sequence"] for s in segs_with_seqs)
    else:
        fold_seq = "".join(s["sub_sequence"] for s in segs_with_seqs)
        if use_esm3 and not esm_key:
            st.info("ESM3 key not configured — using direct domain concatenation.")

    # Annotate actual positions
    pos = 0
    for i, seg in enumerate(segs_with_seqs):
        seg["actual_start"] = pos + 1
        pos += len(seg["sub_sequence"])
        seg["actual_end"] = pos
        if linker_seqs and i < len(linker_seqs):
            pos += len(linker_seqs[i])

    st.info(f"Chimeric sequence: **{len(fold_seq)} aa**")
    with st.expander("View assembled sequence"):
        st.code(fold_seq)

    # 3. ESMFold
    valid, err = esmfold.validate_sequence(fold_seq)
    if not valid:
        st.error(f"Sequence error: {err}")
        return

    with st.spinner("🔬 ESMFold predicting structure (free API)…"):
        try:
            result = esmfold.predict_structure(fold_seq)
            st.session_state["chim_result"]      = result
            st.session_state["chim_fold_seq"]    = fold_seq
            st.session_state["chim_linker_seqs"] = linker_seqs
        except Exception as e:
            st.error(f"ESMFold failed: {e}")
            return

    # 4. Gemini interpretation
    if gemini_key:
        with st.spinner("🤖 Gemini interpreting chimeric design…"):
            try:
                interp = agent.interpret_chimeric_design(
                    segments=segs_with_seqs,
                    linker_sequences=linker_seqs,
                    full_sequence=fold_seq,
                    mean_plddt=result["mean_plddt"],
                    ptm=result.get("ptm"),
                    per_residue_plddt=result["per_residue_plddt"],
                    api_key=gemini_key,
                )
            except Exception as e:
                interp = f"*(Interpretation unavailable: {e})*"
    else:
        interp = "*(Gemini key not configured)*"

    st.session_state["chim_interp"] = interp
    _show_results()


def _show_results():
    result   = st.session_state["chim_result"]
    fold_seq = st.session_state.get("chim_fold_seq","")
    linkers  = st.session_state.get("chim_linker_seqs",[])
    interp   = st.session_state.get("chim_interp","")
    assembled = st.session_state.get("chim_assembled",{})
    segments  = assembled.get("segments",[])

    show_fold_results(
        result, "Chimeric Protein", fold_seq, interp,
        segments=segments, linker_sequences=linkers,
    )

    # Download FASTA of chimera
    if fold_seq:
        st.download_button(
            "⬇️ Download chimera FASTA",
            data=f">ProtFoldLab_chimera\n{fold_seq}",
            file_name="chimera.fasta", mime="text/plain",
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch(segments):
    full_seq, seg_info, errors = "", [], []
    prog = st.progress(0, "Fetching from UniProt…")
    for i, seg in enumerate(segments):
        acc = seg.get("uniprot_accession","").strip()
        if not acc:
            q = f"{seg.get('protein','')} {seg.get('species','')}".strip()
            if not q:
                errors.append(f"Segment '{seg['label']}': no accession or name.")
                prog.progress((i+1)/len(segments)); continue
            try:
                hits = uniprot.search_uniprot(q, 3)
                if hits:
                    acc = hits[0]["accession"]
                    st.info(f"'{seg['label']}' → auto-resolved to {acc}")
                else:
                    errors.append(f"'{seg['label']}': no UniProt hit for '{q}'.")
                    prog.progress((i+1)/len(segments)); continue
            except Exception as e:
                errors.append(f"'{seg['label']}': search error ({e}).")
                prog.progress((i+1)/len(segments)); continue
        try:
            prot = uniprot.fetch_sequence(acc)
        except Exception as e:
            errors.append(f"'{seg['label']}' ({acc}): fetch failed ({e}).")
            prog.progress((i+1)/len(segments)); continue

        s, e_ = seg.get("residue_start"), seg.get("residue_end")
        full = prot["sequence"]
        sub = uniprot.extract_domain(full, s, e_) if s and e_ else \
              full[s-1:] if s else full[:e_] if e_ else full

        start = len(full_seq) + 1
        full_seq += sub
        seg_info.append({
            **seg, "accession": acc,
            "protein_full_name": prot["name"],
            "organism": prot.get("organism",""),
            "sub_sequence": sub,
            "actual_start": start, "actual_end": len(full_seq),
        })
        prog.progress((i+1)/len(segments))
    prog.empty()
    for err in errors: st.error(err)
    if not full_seq:
        st.error("No sequences assembled.")
        return None
    return {"full_sequence": full_seq, "segments": seg_info}


def _show_table(segments):
    rows = [{
        "Segment": s.get("label","?"),
        "Accession": s.get("accession",""),
        "Protein": s.get("protein_full_name",""),
        "Species": s.get("organism",""),
        "Domain": s.get("domain",""),
        "Position": f"{s['actual_start']}–{s['actual_end']}",
        "Length": s["actual_end"]-s["actual_start"]+1,
    } for s in segments]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
