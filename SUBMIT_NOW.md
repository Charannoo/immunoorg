# Submit in the next ~5 hours — do this in order

**Fastest calm path:** read **[`WIN_30MIN.md`](./WIN_30MIN.md)** first.

You do **not** need a finished local GRPO CPU run to submit. Judges need a **runnable Space**, **clear story**, **training path**, and **evidence**.

**Immediate:** `python scripts/make_hackathon_training_figure.py` → commits-ready **`evidence_grpo_training.png`** (real env rollout + where to get GRPO loss in Colab).

## 0. Hard prerequisites (30–45 min)

1. **Hugging Face Space** — push latest `master` so Docker rebuilds (`openenv-core` in `requirements.txt`, War Room, landing links).
2. **Smoke-test the Space** (incognito): `/` → **Launch demo** → expand **Live LLM War Room** (set **`GROQ_API_KEY`** etc. in **Secrets** for live LLM debate).
3. **Public writeup URL** — publish a short **HF Post** (copy from [`BLOG_POST.md`](./BLOG_POST.md)) **or** upload **&lt;2 min** YouTube using [`VIDEO_SCRIPT.md`](./VIDEO_SCRIPT.md). Paste the **public URL** into [`README.md`](./README.md) (replace `HF_MINI_BLOG_URL` / `YOUTUBE_DEMO_URL`).

## 1. GRPO training plot (45–60 min if you have Colab GPU)

1. Open [`ImmunoOrg_Training_Colab.ipynb`](./ImmunoOrg_Training_Colab.ipynb) in **Google Colab** → **Runtime → GPU (T4)**.
2. **Runtime → Run all**. Wait through install + GRPO.
3. When **Step 4b** runs, it writes **`evidence_grpo_training.png`** under `/content/immunoorg/`.
4. **Download** that PNG → drop it at the **repo root** → `git add evidence_grpo_training.png` → commit → push.

If Colab fails (OOM): in the notebook, set `MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"` and reduce `num_train_epochs` to `1`, then re-run from the model cell onward.

**If you truly have zero GPU time:** keep the existing committed `evidence_*.png` files, and in README add one line under the evidence section: *“GRPO loss/reward curves: see executed Colab notebook (link in table).”* — weaker, but better than missing links.

## 2. Last checks (5 min)

```bash
python scripts/verify_hackathon_submission.py
```

Fix any **FAIL** lines. **WARN** on missing `evidence_grpo_training.png` is OK only if you added the Colab notebook link + honest note.

## 3. Submit the form

Paste:

- **Space URL:** https://huggingface.co/spaces/hirann/immunoorg-v3  
- **Direct app:** https://hirann-immunoorg-v3.hf.space  
- **GitHub:** https://github.com/Charannoo/immunoorg  
- **Blog/video:** the URL you put in README  

## 4. Do **not** burn time on

- Waiting for **local CPU GRPO** (first step can take 30+ minutes and looks frozen).
- Perfect polish — **runnable Space + story + Colab path + plots** beats everything else.

Good luck.
