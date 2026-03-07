from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "ops" / "scripts" / "send-telegram-summary.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_send_telegram_summary_uses_decrypted_secrets_and_posts_message(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    calls_path = tmp_path / "curl-call.txt"
    summary_path = tmp_path / "summary.txt"
    summary_path.write_text("Updated AGENTS.md and installed Telegram delivery workflow.\n", encoding="utf-8")

    _write_executable(
        fake_bin / "sops",
        """#!/usr/bin/env bash
set -euo pipefail
cat <<'EOF'
telegram:
  bot_token: "bot-token-123"
  chat_id: "5471749508"
EOF
""",
    )
    _write_executable(
        fake_bin / "curl",
        f"""#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" > "{calls_path}"
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["TELEGRAM_SECRETS_FILE"] = str(tmp_path / "telegram.sops.yaml")
    (tmp_path / "telegram.sops.yaml").write_text("encrypted-placeholder", encoding="utf-8")

    completed = subprocess.run(
        [
            str(SCRIPT_PATH),
            "--title",
            "Codex finished work",
            "--summary-file",
            str(summary_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )

    assert completed.returncode == 0, completed.stderr
    call_args = calls_path.read_text(encoding="utf-8")
    assert "https://api.telegram.org/botbot-token-123/sendMessage" in call_args
    assert "chat_id=5471749508" in call_args
    assert "Codex finished work" in call_args
    assert "Updated AGENTS.md and installed Telegram delivery workflow." in call_args
