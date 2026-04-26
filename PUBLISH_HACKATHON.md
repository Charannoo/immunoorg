# Hackathon submission — publish these URLs (5 minutes)

**If you are hours from the deadline, use [`SUBMIT_NOW.md`](./SUBMIT_NOW.md) as the master checklist** — this file is only the HF/YouTube paste instructions.

Non-negotiables ask for a **public mini-blog on Hugging Face** *or* a **&lt;2 minute YouTube** video, with everything linked from **README.md**.

Your in-repo writeups are already done: [`BLOG_POST.md`](./BLOG_POST.md), [`VIDEO_SCRIPT.md`](./VIDEO_SCRIPT.md).

## 1. Hugging Face “mini-blog” (recommended)

1. Open [Hugging Face](https://huggingface.co/) → your profile → **Posts** / **Articles** (or publish from your Space’s **Community** tab).
2. Title idea: **ImmunoOrg 2.0 — training an LLM to heal enterprises (OpenEnv India 2026)**.
3. Copy the body from [`BLOG_POST.md`](./BLOG_POST.md) (edit for length if needed).
4. Add these links at the bottom:
   - Space: https://huggingface.co/spaces/hirann/immunoorg-v3  
   - GitHub: https://github.com/Charannoo/immunoorg  
   - Colab: link to `ImmunoOrg_Training_Colab.ipynb` on GitHub (raw or Colab open link).
5. **Copy the public URL** of the post and paste it into **README.md** in the resources table (`HF_MINI_BLOG_URL`).

Do **not** upload large video files to the Space repo — link YouTube instead.

## 2. YouTube (&lt; 2 minutes) — optional if HF post is primary

1. Record using the beat sheet in [`VIDEO_SCRIPT.md`](./VIDEO_SCRIPT.md).
2. Upload as **Public** or **Unlisted**.
3. Put the URL in **README.md** (`YOUTUBE_DEMO_URL`).

## 3. Judges’ guide (reference)

Official “what judges look for” doc (link in hackathon brief):  
https://docs.google.com/document/d/1Odznuzwtb1ecDOm2t6ToZd4MuMXXfO6vWUGcxbC6mFs/edit?tab=t.0#bookmark=kix.2dz0x0nie3me  

## 4. After publishing

1. Edit **README.md** — fill in the two URL placeholders in the resources table.
2. Run **`python scripts/verify_hackathon_submission.py`** and fix anything it reports.
3. Push GitHub + Hugging Face Space remotes; wait for Space rebuild.

## 5. Local Python gotcha (OpenEnv)

If `import openenv.core` fails or imports the wrong code, run `pip uninstall openenv`
(the legacy namesake package) and `pip install openenv-core` so only the hackathon
framework is on your `PYTHONPATH`.
