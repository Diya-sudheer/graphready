"""Deploy the Gradio demo to Hugging Face Spaces.

One-time setup:
    1. Create a free account: https://huggingface.co/join
    2. Create a write token:  https://huggingface.co/settings/tokens
    3. pip install huggingface_hub
    4. python scripts/deploy_space.py --user YOUR_HF_USERNAME --token hf_...

The script creates (or updates) the Space and uploads demo/ plus the
graphready package source. First build takes ~10 minutes on the free CPU tier.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main(user: str, token: str, space_name: str = "graphready") -> None:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    repo_id = f"{user}/{space_name}"
    api.create_repo(repo_id, repo_type="space", space_sdk="gradio", exist_ok=True)

    # Assemble the Space contents: demo/ at root + package source + samples
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td)
        for f in (REPO / "demo").iterdir():
            shutil.copy2(f, stage / f.name)
        shutil.copytree(REPO / "src", stage / "src")
        samples = REPO / "data" / "samples"
        if samples.exists():
            shutil.copytree(samples, stage / "data" / "samples")

        api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=str(stage))

    print(f"Deployed: https://huggingface.co/spaces/{repo_id}")
    print("First build takes ~10 min (model weights download once, then cached).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True, help="Hugging Face username")
    ap.add_argument("--token", required=True, help="HF write token (hf_...)")
    ap.add_argument("--space", default="graphready")
    args = ap.parse_args()
    main(args.user, args.token, args.space)
