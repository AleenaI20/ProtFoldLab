"""
utils/viewer.py — Interactive 3D protein viewer (py3Dmol inline HTML)
utils/display.py — Shared Streamlit result display
"""

import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from utils import esmfold as esm


def render_3d_structure(pdb_string: str, height: int = 520) -> None:
    pdb = (pdb_string
           .replace("\\", "\\\\")
           .replace("`", "\\`")
           .replace("$", "\\$"))
    html = f"""<!DOCTYPE html><html>
<head>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/3Dmol/2.1.0/3Dmol-min.js"></script>
  <style>
    body{{margin:0;background:#0d1117}}
    #v{{width:100%;height:{height}px;position:relative}}
    #c{{position:absolute;top:8px;right:8px;z-index:10;display:flex;flex-direction:column;gap:4px}}
    button{{background:rgba(255,255,255,.15);color:#fff;border:1px solid rgba(255,255,255,.3);
      padding:4px 10px;border-radius:6px;cursor:pointer;font-size:12px}}
    button:hover{{background:rgba(255,255,255,.28)}}
    #lg{{position:absolute;bottom:8px;left:8px;z-index:10;background:rgba(0,0,0,.6);
      border-radius:8px;padding:8px 12px;color:#fff;font-size:11px;line-height:1.9}}
  </style>
</head>
<body>
<div id="v">
  <div id="c">
    <button onclick="ss('cartoon')">Cartoon</button>
    <button onclick="ss('stick')">Stick</button>
    <button onclick="ss('surface')">Surface</button>
    <button onclick="ss('sphere')">Sphere</button>
    <button onclick="viewer.zoomTo()">Reset</button>
    <button onclick="sp=!sp;viewer.spin(sp)">Spin</button>
  </div>
  <div id="lg"><b>pLDDT</b><br>
    <span style="color:#0053D6">■</span> ≥90 Very high<br>
    <span style="color:#65CBF3">■</span> 70–90 High<br>
    <span style="color:#FFDB13">■</span> 50–70 Medium<br>
    <span style="color:#FF7D45">■</span> &lt;50 Low
  </div>
</div>
<script>
var sp=false;
var viewer=$3Dmol.createViewer(document.getElementById('v'),{{backgroundColor:'#0d1117'}});
viewer.addModel(`{pdb}`,'pdb');
function applyPLDDT(){{
  viewer.setStyle({{}},{{cartoon:{{colorscheme:{{prop:'b',gradient:'linear',
    min:0,max:100,colors:['#FF7D45','#FFDB13','#65CBF3','#0053D6']}}}}}});
}}
function ss(s){{
  viewer.removeAllSurfaces();viewer.setStyle({{}},{{}});
  if(s==='cartoon') applyPLDDT();
  else if(s==='stick') viewer.setStyle({{}},{{stick:{{colorscheme:'ssJmol'}}}});
  else if(s==='surface'){{viewer.setStyle({{}},{{cartoon:{{}}}});
    viewer.addSurface($3Dmol.SurfaceType.VDW,{{opacity:0.75,colorscheme:'ssJmol'}});}}
  else if(s==='sphere') viewer.setStyle({{}},{{sphere:{{colorscheme:'ssJmol'}}}});
  viewer.render();
}}
applyPLDDT();viewer.zoomTo();viewer.render();viewer.rotate(25,{{x:0,y:1,z:0}});
</script></body></html>"""
    components.html(html, height=height + 10, scrolling=False)


def plddt_color(value: float) -> str:
    if value >= 90: return "#0053D6"
    if value >= 70: return "#65CBF3"
    if value >= 50: return "#FFDB13"
    return "#FF7D45"


def show_fold_results(
    result: dict, protein_name: str, sequence: str,
    interpretation: str,
    segments: list[dict] | None = None,
    linker_sequences: list[str] | None = None,
):
    st.success("✅ Structure predicted!")
    st.divider()

    # 3D viewer
    st.markdown("### 🎨 Interactive 3D Structure")
    st.caption("Coloured by pLDDT confidence · Cartoon / Stick / Surface / Sphere")
    render_3d_structure(result["pdb_string"], height=540)

    st.download_button(
        "⬇️ Download .pdb file",
        data=result["pdb_string"],
        file_name=f"{protein_name.replace(' ','_')[:40]}_esmfold.pdb",
        mime="chemical/x-pdb",
        use_container_width=True,
    )

    st.divider()

    # Confidence
    st.markdown("### 📊 Confidence Scores")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Mean pLDDT", f"{result['mean_plddt']:.1f} / 100")
    with c2:
        ptm = result.get("ptm")
        st.metric("pTM", f"{ptm:.3f}" if ptm else "N/A")
    with c3:
        st.metric("Confidence", esm.plddt_label(result["mean_plddt"]).split("—")[0].strip())
    st.caption(esm.plddt_label(result["mean_plddt"]))

    # pLDDT plot
    per_res = result.get("per_residue_plddt", [])
    if per_res:
        st.markdown("#### Per-residue pLDDT profile")
        has_domain_map = bool(segments and linker_sequences is not None)
        fig, axes = plt.subplots(
            2 if has_domain_map else 1, 1,
            figsize=(11, 3.8 if has_domain_map else 2.5),
            gridspec_kw={"height_ratios": [3, 1]} if has_domain_map else None,
        )
        ax = axes[0] if has_domain_map else axes
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")

        x = np.arange(1, len(per_res) + 1)
        ax.bar(x, per_res, color=[plddt_color(v) for v in per_res], width=1.0, edgecolor="none")
        for t, c in [(90,"#0053D6"),(70,"#65CBF3"),(50,"#FFDB13")]:
            ax.axhline(t, color=c, linestyle="--", lw=0.7, alpha=0.5)
        ax.set_xlim(1, len(per_res)); ax.set_ylim(0, 100)
        ax.set_ylabel("pLDDT", color="white", fontsize=9)
        ax.tick_params(colors="white", labelsize=8)
        for s in ax.spines.values(): s.set_edgecolor("#333")
        ax.legend(handles=[
            mpatches.Patch(color=c, label=l)
            for c, l in [("#0053D6","≥90"),("#65CBF3","70–90"),("#FFDB13","50–70"),("#FF7D45","<50")]
        ], loc="lower right", fontsize=7, facecolor="#1a1a2e", labelcolor="white", edgecolor="#555")

        if has_domain_map:
            ax2 = axes[1]
            ax2.set_facecolor("#0d1117")
            palette = ["#e63946","#457b9d","#2a9d8f","#e9c46a","#f4a261","#a8dadc","#c77dff"]
            for i, seg in enumerate(segments):
                s = (seg.get("actual_start") or 1) - 1
                e = seg.get("actual_end") or len(per_res)
                ax2.barh(0, e-s, left=s, color=palette[i%len(palette)], height=0.7)
                ax2.text(s+(e-s)/2, 0, seg.get("label",f"S{i+1}"),
                         ha="center", va="center", fontsize=7, color="white", fontweight="bold")
            pos = 0
            for i, seg in enumerate(segments):
                pos += len(seg.get("sub_sequence",""))
                if linker_sequences and i < len(linker_sequences) and linker_sequences[i]:
                    lk = len(linker_sequences[i])
                    ax2.barh(0, lk, left=pos, color="white", height=0.7, alpha=0.25)
                    ax2.text(pos+lk/2, 0, "lnk", ha="center", va="center", fontsize=6, color="white")
                    pos += lk
            ax2.set_xlim(0, len(per_res)); ax2.set_yticks([])
            ax2.set_xlabel("Residue", color="white", fontsize=9)
            ax2.tick_params(colors="white", labelsize=8)
            for s in ax2.spines.values(): s.set_edgecolor("#333")

        plt.tight_layout(pad=0.4)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    st.divider()

    # Interpretation
    st.markdown("### 🤖 AI Structural Interpretation")
    st.markdown(interpretation)
