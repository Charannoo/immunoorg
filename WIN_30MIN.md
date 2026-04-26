# Win mode — 30 minutes (breathe, then do)

You are **not** blocked. Do these in order. **Do not** start long CPU GRPO.

## 1. Generate one more evidence PNG (2 minutes)

From repo root:

```bash
python scripts/make_hackathon_training_figure.py
```

This creates **`evidence_grpo_training.png`** (real env curve + pointer to Colab for loss). Commit it.

## 2. Colab for the “full” training plot (15 min if GPU free)

1. README → **Open in Colab** on the training notebook.  
2. **Runtime → GPU → Run all.**  
3. Download **`evidence_grpo_training.png`** from Colab if Step 4b looks better — **replace** the file from step 1, commit.

## 3. Hugging Face post (8 min)

1. New **Post** on HF.  
2. Copy **`BLOG_POST.md`** (trim if long).  
3. Add links: Space, GitHub, Colab.  
4. Paste the post URL into **`README.md`** (replace `HF_MINI_BLOG_URL`).

## 4. Push Space + GitHub (5 min)

```bash
git add evidence_grpo_training.png README.md
git commit -m "Add hackathon training evidence figure + HF blog URL"
git push origin master
```

If your **Space is connected to this GitHub repo** in HF settings, it will **rebuild on its own** after `git push origin`.

Otherwise push the Space git remote (needs HF token), e.g.:

```bash
git push hf-new master
```

## 5. Click test (2 min)

Open Space → `/demo` → **Live LLM War Room** opens at top of page (set **GROQ_API_KEY** in Space secrets if needed).

---

**If you only have 10 minutes total:** do steps **1, 3, 4** and mention Colab in the HF post (“full GRPO curves in linked notebook”).

You’ve got this.
