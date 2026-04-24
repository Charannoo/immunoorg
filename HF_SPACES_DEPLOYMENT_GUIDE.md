# 🚀 HuggingFace Spaces Deployment Guide

This guide explains how to deploy ImmunoOrg to HuggingFace Spaces for judges to access.

## Option 1: Deploy via Git Push (Recommended for Hackathon)

### Step 1: Create HF Space

```bash
# 1. Go to https://huggingface.co/spaces
# 2. Click "Create new Space"
# 3. Fill in:
#    - Owner: your-username
#    - Space name: immunoorg-environment
#    - License: openrail (or MIT)
#    - Space SDK: Docker
#    - Visibility: Public
# 4. Click "Create Space"
```

### Step 2: Clone the Space Repository

```bash
# Clone your new space
git clone https://huggingface.co/spaces/your-username/immunoorg-environment
cd immunoorg-environment
```

### Step 3: Copy ImmunoOrg Files

```bash
# Copy all ImmunoOrg files to the space repo
cp -r /path/to/immunoorg-project/* .

# Should contain:
# - Dockerfile
# - requirements.txt
# - immunoorg/
# - server/
# - openenv.yaml
# - README.md
```

### Step 4: Create app.py (Optional Interface)

Create `app.py` for a simple Gradio interface:

```python
"""
Optional: Gradio interface for ImmunoOrg on HF Spaces
This allows judges to interact with the environment without code.
"""

import gradio as gr
import json
import requests
from immunoorg.environment import ImmunoOrgEnvironment
from immunoorg.models import ImmunoAction, ActionType

def run_environment(difficulty: int, num_steps: int):
    """Run environment and return results."""
    try:
        env = ImmunoOrgEnvironment(difficulty=difficulty, seed=42)
        obs = env.reset()
        
        results = {
            "observation": obs.model_dump(),
            "difficulty": difficulty,
            "status": "✅ Environment initialized"
        }
        
        return json.dumps(results, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

# Create Gradio interface
interface = gr.Interface(
    fn=run_environment,
    inputs=[
        gr.Slider(1, 4, value=1, label="Difficulty Level"),
        gr.Slider(1, 50, value=10, label="Number of Steps"),
    ],
    outputs="text",
    title="ImmunoOrg: Interactive Environment",
    description="Test the ImmunoOrg environment on HuggingFace Spaces",
)

if __name__ == "__main__":
    interface.launch(server_name="0.0.0.0", server_port=7860)
```

### Step 5: Push to HF Spaces

```bash
# Add all files to git
git add .
git commit -m "Initial ImmunoOrg environment deployment"

# Push to HF Spaces (this will trigger Docker build)
git push

# Wait 5-10 minutes for Docker build and deployment
# Then access at: https://huggingface.co/spaces/your-username/immunoorg-environment
```

### Step 6: Verify Deployment

```bash
# Test the endpoint once it's live
curl https://huggingface.co/spaces/your-username/immunoorg-environment/health
```

## Option 2: Local Testing Before Deployment

Test locally to ensure Docker build works:

```bash
# Build Docker image
docker build -t immunoorg-env .

# Run container
docker run -p 7860:7860 immunoorg-env

# Test the server
curl http://localhost:7860/health
```

## Option 3: Push from GitHub

If you have the repo on GitHub:

```bash
# In HF Spaces, go to Settings → Repository
# Link your GitHub repo
# HF will auto-deploy on GitHub push
```

## Files Needed in Spaces

```
immunoorg-environment/
├── Dockerfile              # Docker config
├── requirements.txt        # Python dependencies
├── app.py                  # Optional Gradio UI
├── server/
│   └── main.py            # FastAPI app
├── immunoorg/
│   ├── environment.py
│   ├── models.py
│   ├── network_graph.py
│   ├── org_graph.py
│   ├── permission_flow.py
│   ├── attack_engine.py
│   ├── belief_map.py
│   ├── reward.py
│   ├── curriculum.py
│   ├── self_improvement.py
│   ├── agents/
│   │   ├── defender.py
│   │   └── department.py
│   └── __init__.py
├── openenv.yaml           # OpenEnv spec
├── README.md              # Documentation
└── .gitignore             # Ignore large files
```

## Troubleshooting

### Docker Build Fails
- Check Dockerfile syntax: `docker build -t test .`
- Ensure all imports are in requirements.txt
- Look at HF Spaces build logs

### Environment doesn't load
- Verify `openenv.yaml` is present and valid
- Check that `immunoorg/` package is importable
- Test locally: `python -c "from immunoorg.environment import ImmunoOrgEnvironment"`

### Slow performance
- Reduce default difficulty or number of steps
- Use async loading in Gradio
- Cache environment state if possible

## URL Template

Once deployed, your environment will be at:

```
https://huggingface.co/spaces/[USERNAME]/[SPACE-NAME]
```

Share this URL with judges!

## Next Steps

1. **Push to Spaces** (this file)
2. **Update README** with Spaces link
3. **Test interactively** on HF Spaces
4. **Share with judges** via email/submission form
