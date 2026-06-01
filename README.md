# 🧬 ProtFoldLab v3

**Agentic Protein Folding & Chimeric Design Lab**

Fully automated — no API key input from users. Deploy once on Streamlit Cloud, share the URL.

---

## ✨ Features

| | Natural Protein Mode | Chimeric Protein Mode |
|---|---|---|
| Input | UniProt search / accession | Plain language description |
| Parsing | — | Gemini AI |
| Sequences | UniProt REST | UniProt REST (per domain) |
| Design | — | ESM3 linker infilling |
| Folding | ESMFold | ESMFold |
| Output | 3D viewer + PDB + pLDDT + interpretation | All of left + domain map + FASTA |

---

## 🔑 APIs Used

| API | Auth | Cost | Purpose |
|---|---|---|---|
| ESMFold (api.esmatlas.com) | ❌ None needed | ✅ Free | Structure prediction |
| UniProt REST | ❌ None needed | ✅ Free | Sequence fetching |
| Gemini Flash (Google AI) | ✅ Key (server-side) | ✅ Free tier | Parsing + interpretation |
| ESM3 Forge (EvolutionaryScale) | ✅ Key (server-side) | ✅ Free tier | Linker design |

**Users never see or enter any API key.**

---

## 🚀 Deploying on Streamlit Cloud (recommended)

1. Fork or push this repo to your GitHub
2. Go to **[share.streamlit.io](https://share.streamlit.io)**
3. Click **New app** → select your repo → set main file to `app.py`
4. Go to **Advanced settings → Secrets** and paste:

```toml
GEMINI_API_KEY = "your-gemini-key-here"
ESM_FORGE_KEY  = "your-esm-forge-key-here"
```

5. Click **Deploy** — done. Share the URL with anyone.

### Getting the keys (both free)

**Gemini API key** (free, no credit card):
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key** → **Create API key**
3. Copy the key

**ESM3 Forge key** (free research tier):
1. Go to [forge.evolutionaryscale.ai](https://forge.evolutionaryscale.ai)
2. Sign up → generate an API token

---

## 💻 Running Locally

```bash
git clone https://github.com/AleenaI20/ProtFoldLab.git
cd ProtFoldLab

pip install -r requirements.txt

# Create local secrets file
mkdir -p .streamlit
cat > .streamlit/secrets.toml << EOF
GEMINI_API_KEY = "your-gemini-key"
ESM_FORGE_KEY  = "your-esm-forge-key"
EOF

streamlit run app.py
```

---

## 🏗️ Project Structure

```
ProtFoldLab/
├── app.py                      # Entry point — loads secrets, routing
├── pages/
│   ├── natural_protein.py      # Natural protein workflow
│   └── chimeric_protein.py     # Chimeric design workflow
├── utils/
│   ├── uniprot.py              # UniProt REST (stdlib only, no key)
│   ├── esmfold.py              # ESMFold via api.esmatlas.com (no key)
│   ├── esm3_design.py          # ESM3 linker design (Forge key, server-side)
│   ├── agent.py                # Gemini AI parsing & interpretation
│   └── viewer.py               # 3D viewer + Streamlit display helpers
├── .streamlit/
│   └── secrets.toml            # Local secrets (never pushed to GitHub)
├── requirements.txt
└── README.md
```

---

## 🧪 Example

**Chimeric prompt:**
> Human alpha7 nAChR ECD + TM1-TM4 + SAP domain + C. elegans unc-29 latch

**Pipeline:**
1. Gemini identifies: CHRNA7 (P36544) ECD (1–236), TM1–TM4 (237–480), UNC-29 (P12364) latch (~170–210)
2. UniProt fetches both sequences
3. ESM3 designs 5 aa linkers at each junction
4. ESMFold folds the full 500+ aa chimera (auto-chunked if needed)
5. Gemini analyses domain confidence and junction quality

---

## 📚 References

- Hayes et al. (2025). ESM3. *Science*.
- Lin et al. (2023). ESMFold. *Science*, 379, 1123–1130.
- UniProt Consortium (2023). *Nucleic Acids Research*, 51(D1), D523–D531.

---

## 📄 License

MIT
