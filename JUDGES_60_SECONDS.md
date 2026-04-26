# Judges — 60 seconds on ImmunoOrg 2.0

1. **Open the Space (direct host):** https://hirann-immunoorg-v3.hf.space  
2. Click **▶ Launch interactive demo** → **`/demo`**.  
3. **Episode demo:** pick a scenario → **Run episode** → compare heuristic vs trained columns + charts.  
4. **Theme #1 (multi-agent):** scroll to **“Live LLM War Room”** (accordion is open by default) → fill threat fields → **Run War Room debate** (needs **`GROQ_API_KEY`** or other LLM secret on the Space).  
5. **Training:** [Open Colab](https://colab.research.google.com/github/Charannoo/immunoorg/blob/master/ImmunoOrg_Training_Colab.ipynb) → GPU → Run all → Step 4b = GRPO plots.  
6. **Writeup:** [`BLOG_POST.md`](./BLOG_POST.md) (paste into a Hugging Face post) — link should also be in [`README.md`](./README.md).

**API:** `POST /reset`, `POST /step`, `GET /state`, `GET /openenv.yaml`.
