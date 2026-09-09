"""Sanity checks for the SOPS+age encrypted-secrets setup.

Not a test of encryption correctness (that's sops's job) - just makes a
broken local/CI setup fail visibly: the tracked ciphertext must exist, and
the plaintext .env must never be trackable by git.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_env_enc_exists():
    assert (REPO_ROOT / ".env.enc").is_file(), (
        ".env.enc is missing - it's the tracked, encrypted secrets file "
        "(see 'Secrets management (SOPS + age)' in CLAUDE.md)"
    )


def test_env_is_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".env"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    assert result.returncode == 0, (
        ".env is not gitignored - a plaintext secrets file could be "
        "committed by accident (see .gitignore)"
    )
