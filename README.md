# 🧬 ProtFoldLab

**Agentic Protein Folding & Chimeric Design Lab**

ProtFoldLab is a fully automated Streamlit web application for studying protein structure and designing chimeric proteins. No GPU required, no API key input from users — just open the URL and run.

---

## 🧬 What is this for?

This tool is built for studying **protein folding** — both naturally occurring proteins and chimeric (fusion) proteins assembled from domains of different species.

**Example use cases:**
- Predict the 3D structure of **human alpha7 nAChR** (P36544)
- Design and fold a chimera: **human alpha7 nAChR ECD + TM1-TM4 + SAP domain + C. elegans unc-29 latch**
- Study whether two domains from different species can fold together coherently
- Get AI-interpreted confidence scores (pLDDT, pTM) with biological context

---

## ⚙️ Pipeline Overview

### 🔬 Natural Protein Mode
```
UniProt search / accession
        ↓
UniProt REST API  →  fetch sequence
        ↓
ESMFold (api.esmatlas.com)  →  predict 3D structure   [free, no key]
        ↓
Gemini AI  →  interpret pLDDT, pTM, structural regions
```

### 🧪 Chimeric Protein Mode
```
Plain language description
  e.g. "Human alpha7 nAChR ECD + TM1-TM4 + SAP + C. elegans unc-29 latch"
        ↓
Gemini AI  →  parse domains, identify UniProt accessions
        ↓
UniProt REST API  →  fetch sequence for each domain
        ↓
ESM3 (EvolutionaryScale Forge)  →  design linker sequences at junctions  [DESIGN]
        ↓
Assemble:  domain1 + ESM3_linker + domain2 + ESM3_linker + domain3 ...
        ↓
ESMFold  →  predict 3D structure of full chimera   [PREDICT]
        ↓
Gemini AI  →  interpret domain confidence, linker quality, folding coherence
```

---

## 📤 Outputs

| Output | Description |
|---|---|
| 🎨 Interactive 3D viewer | Rotatable structure coloured by pLDDT confidence (cartoon / stick / surface / sphere) |
| ⬇️ PDB file download | Full predicted structure as `.pdb` file |
| 📊 Mean pLDDT | Per-model confidence score (0–100) |
| 📊 pTM score | Predicted TM-score, overall fold quality |
| 📈 Per-residue pLDDT plot | Bar chart with domain boundary overlay for chimeras |
| 🤖 AI interpretation | Gemini's expert analysis of structural regions, confidence, and biological implications |
| ⬇️ Chimera FASTA | Downloadable assembled chimeric sequence |

### pLDDT confidence scale
| Score | Meaning |
|---|---|
| ≥ 90 | Very high — confident within ~1 Å |
| 70–90 | High — reliable backbone |
| 50–70 | Medium — correct topology, uncertain side-chains |
| < 50 | Low — likely disordered or unreliable |

---

## 🔑 APIs Used

| API | Key required? | Cost | Purpose |
|---|---|---|---|
| ESMFold (`api.esmatlas.com`) | ❌ None | ✅ Free | Structure prediction |
| UniProt REST (`rest.uniprot.org`) | ❌ None | ✅ Free | Protein sequence database |
| Gemini Flash (Google AI Studio) | ✅ Server-side only | ✅ Free tier | Domain parsing & interpretation |
| ESM3 (EvolutionaryScale Forge) | ✅ Server-side only | ✅ Free research tier | Linker sequence design |

**Users never see or enter any API key.** Keys are stored as secrets by the developer.

---

## 🚀 Deployment (Hugging Face Spaces — recommended)

Hugging Face Spaces is the recommended deployment platform. It supports Streamlit natively, requires no full GitHub account access, and is purpose-built for ML/biology tools.

### Step 1 — Get free API keys (developer only, one-time)

**Gemini API key** (30 seconds, no credit card):
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key** → **Create API key**

**ESM3 Forge key** (free research/academic access):
1. Go to [forge.evolutionaryscale.ai](https://forge.evolutionaryscale.ai)
2. Sign up → generate an API token

### Step 2 — Deploy on Hugging Face Spaces
1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **Create new Space**
3. Name it `ProtFoldLab`, choose **Streamlit** as the SDK, set to **Public**
4. Upload all project files directly (no GitHub connection needed)
5. Go to **Settings → Variables and Secrets** and add:
   - `GEMINI_API_KEY` → your Gemini key
   - `ESM_FORGE_KEY` → your ESM3 Forge key
6. The Space builds automatically — share the URL with anyone

### Alternative — Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub repo → set main file to `app.py`
3. Go to **Advanced settings → Secrets** and paste:
```toml
GEMINI_API_KEY = "your-gemini-key-here"
ESM_FORGE_KEY  = "your-esm-forge-key-here"
```
4. Click **Deploy**

---

## 💻 Running Locally

```bash
git clone https://github.com/AleenaI20/ProtFoldLab.git
cd ProtFoldLab

pip install -r requirements.txt

# Set up local secrets
mkdir -p .streamlit
nano .streamlit/secrets.toml
# Paste:
# GEMINI_API_KEY = "your-key"
# ESM_FORGE_KEY  = "your-key"

streamlit run app.py
```

---

## 🏗️ Project Structure

```
ProtFoldLab/
├── app.py                      # Streamlit entry point, loads secrets server-side
├── pages/
│   ├── natural_protein.py      # Natural protein: search → fold → interpret
│   └── chimeric_protein.py     # Chimeric: parse → fetch → design → fold → interpret
├── utils/
│   ├── uniprot.py              # UniProt REST client (stdlib only, no key)
│   ├── esmfold.py              # ESMFold via api.esmatlas.com (no key, auto-chunking)
│   ├── esm3_design.py          # ESM3 linker design via Forge API
│   ├── agent.py                # Gemini AI: domain parsing & structural interpretation
│   └── viewer.py               # 3D viewer (py3Dmol) + Streamlit display helpers
├── .streamlit/
│   └── secrets.toml            # Local secrets — never pushed to GitHub
├── requirements.txt
└── README.md
```

---

## 📚 Scientific References

- Hayes et al. (2025). "Simulating 500 million years of evolution with a language model." *Science*. — **ESM3**
- Lin et al. (2023). "Evolutionary-scale prediction of atomic-level protein structure with a language model." *Science*, 379, 1123–1130. — **ESMFold**
- UniProt Consortium (2023). "UniProt: the Universal Protein Database." *Nucleic Acids Research*, 51(D1), D523–D531.

---

## 📄 License

MIT License — see `LICENSE`
