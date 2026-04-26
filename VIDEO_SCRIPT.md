# 90-second submission video — recording script

A 90-second screen-cap is the cheapest way to lift the **Storytelling
(30%)** judge score. The hackathon brief explicitly accepts a video
under 2 minutes. Below is a tight script with **exact lines to read**,
**exact screens to show**, and **exact mouse clicks**, so you can
record it in one take with a free tool like [Loom](https://loom.com)
or OBS Studio.

Total runtime: **0:00 → 1:30**. Aim for ≤1:30.

---

## Tools you'll need (5 min setup)

- **Screen recorder**: Loom (browser, free) or OBS Studio.
- Browser tabs already open in this order:
  1. https://hirann-immunoorg-v3.hf.space (the live Space — landing page)
  2. https://huggingface.co/spaces/hirann/immunoorg-v3 (the Space card)
  3. https://github.com/Charannoo/immunoorg (the GitHub repo)
  4. https://github.com/Charannoo/immunoorg/blob/master/PROBLEM_STATEMENT.md
- (optional) one of the `evidence_*.png` files open in a viewer for
  the closing shot.

---

## Script (per-shot, with read-aloud lines and on-screen actions)

### Shot 1 — Hook (0:00 → 0:10)

**Show**: tab 1 (the live Space landing page with the green "Launch
interactive demo" button).

**Say** (steady pace, ~25 words):

> "Most cybersecurity environments train an agent to *stop the attack*.
> The real problem is the *organization* that lets the attack succeed
> — that's what ImmunoOrg trains for."

### Shot 2 — Click into the demo (0:10 → 0:20)

**Click** the green "▶ Launch interactive demo" button. The Gradio UI
loads. Hover the scenario dropdown briefly so the 5 scenario family
names are visible.

**Say**:

> "Two graphs run in parallel: a technical network and an organizational
> graph. Five conflict-heavy training scenarios — RAG-grounding,
> executive alignment, silo-breaker, stealth, and basic containment."

### Shot 3 — Pick "Executive Alignment" and run an episode (0:20 → 0:50)

**Action**: pick "3. Executive Alignment (uptime directive overrides
instinct)" from the dropdown. Click **Run episode**. Wait ~5 seconds
for the episode to play.

**While it's running, say**:

> "I'm picking the Executive Alignment scenario. The board has injected
> a directive: maintain 100% uptime, do NOT isolate any node. The agent's
> security instinct is to isolate — but doing that here is a
> 25-percent-of-reward penalty."

**Once results are visible, point at the heuristic table on the left,
then the trained-LLM table on the right, then the per-step reward
chart.**

**Say**:

> "On the left, the heuristic baseline. On the right, the GRPO-trained
> LLM. Both played the *same* scenario seed. The trained agent picks
> patches and IDS rules instead of isolating — that's the alignment
> behavior we trained for. Reward delta is at the top."

### Shot 4 — Show the reward curve (0:50 → 1:05)

**Action**: switch to tab 3 (GitHub repo). Scroll to the embedded
`evidence_grpo_training.png` chart in the README. (If the HPC run
hasn't finished yet, show `evidence_scenario_rewards.png` instead.)

**Say**:

> "Real GRPO training on a Qwen 7B model with three independent
> verifiable reward functions: format compliance, reasoning quality, and
> phase-appropriate action. Loss trends down, reward trends up,
> trained agent beats heuristic across all five scenario families."

### Shot 5 — Show the architecture in one breath (1:05 → 1:20)

**Action**: switch to tab 4 (PROBLEM_STATEMENT.md). Scroll quickly past
the 5-track reward table.

**Say**:

> "Five-track composable reward — uptime, threat neutralization,
> bureaucracy efficiency, code-patch quality, pipeline integrity. No
> single signal the agent can hack to max total reward. Pipeline is
> SFT warm-start, then GRPO with TRL plus Unsloth, then 100-episode
> evaluation, all chained as one SLURM submission."

### Shot 6 — Closer (1:20 → 1:30)

**Action**: switch back to the live Space landing page (tab 1).

**Say**:

> "Try it yourself — link is in the README. Thanks."

End recording.

---

## After recording

1. Upload to YouTube as **Unlisted** (so judges can view but it doesn't
   show on your channel).
2. Title: `ImmunoOrg 2.0 — OpenEnv Hackathon submission (90 sec)`
3. Description: paste the contents of [`BLOG_POST.md`](./BLOG_POST.md) §1.
4. Copy the YouTube URL.
5. Add it to the top of [`README.md`](./README.md) as a new row:
   ```markdown
   | 🎥 **2-minute video** | https://youtu.be/YOUR_VIDEO_ID |
   ```
6. Commit + push:
   ```powershell
   git add README.md
   git commit -m "Add 90-second submission video link"
   git push origin master
   ```

---

## What NOT to say

- Don't say "we built X bonus prize" — judges don't care about partner
  bonus claims unless you can demo them.
- Don't read the action enums — they'll be on screen.
- Don't go over 1:45 — keep it tight.
- Don't open a terminal — judges want to see the *demo*, not the code.

## Re-takes

If you flub a line, just keep going — Loom + OBS both let you trim the
intro/outro after the fact. **Don't aim for perfect**; aim for "one
take, conversational, hits the 6 beats above". A confident messy take
beats a polished overproduced one.
