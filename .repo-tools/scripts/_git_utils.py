"""Robust git operations for launchd-triggered publishers.

After laptop sleep/wake cycles, the network/SSH context is sometimes stale,
which causes `git pull` to fail or time out on the first attempt — the launchd
job wakes the laptop briefly but the network interface and SSH state need a
moment to fully re-establish. This module wraps `git pull` with a DNS pre-warm
and retry-with-backoff so the publishers stop aborting on those transients
without changing their structure or their cross-machine dedup guarantees.
"""

from __future__ import annotations

import logging
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple


def wake_network(host: str = "github.com", port: int = 443, max_attempts: int = 3) -> bool:
    """Force OS to re-establish network/DNS by resolving a host.

    Returns True if the host resolves within max_attempts. After laptop wake
    the resolver and interface sometimes need a beat before they answer.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            socket.setdefaulttimeout(10)
            socket.getaddrinfo(host, port)
            return True
        except (socket.gaierror, socket.timeout, OSError):
            if attempt < max_attempts:
                time.sleep(2)
    return False


def robust_git_pull(
    repo_root: Path,
    logger: Optional[logging.Logger] = None,
    max_attempts: int = 3,
    base_timeout: int = 60,
) -> Tuple[bool, str]:
    """Run `git pull --rebase --autostash` with network pre-warm + retries.

    Each attempt: DNS-warm `github.com` first, then run pull with a growing
    timeout (base_timeout * attempt → 60s, 120s, 180s by default). On failure,
    waits 5s, 10s, ... before the next attempt. Designed for launchd-after-wake.

    Returns (ok, message). On ok=False, message is the last error/stderr so the
    caller can log it and decide on its own abort/skip policy.
    """
    log = logger or logging.getLogger(__name__)
    cmd = ["git", "-C", str(repo_root), "pull", "--rebase", "--autostash"]

    last_err = "no attempt made"
    for attempt in range(1, max_attempts + 1):
        if not wake_network():
            last_err = "network unreachable (DNS resolve failed)"
            log.warning(f"[git-pull] attempt {attempt}/{max_attempts}: {last_err}")
        else:
            timeout = base_timeout * attempt
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    if attempt > 1:
                        log.info(f"[git-pull] succeeded on attempt {attempt}/{max_attempts}")
                    return True, "ok"
                last_err = (result.stderr.strip() or "non-zero exit")[:300]
                log.warning(
                    f"[git-pull] attempt {attempt}/{max_attempts} failed "
                    f"(rc={result.returncode}): {last_err}"
                )
            except subprocess.TimeoutExpired:
                last_err = f"timed out after {timeout}s"
                log.warning(f"[git-pull] attempt {attempt}/{max_attempts} {last_err}")
            except Exception as exc:
                last_err = f"crashed: {exc}"
                log.warning(f"[git-pull] attempt {attempt}/{max_attempts} {last_err}")

        if attempt < max_attempts:
            backoff = 5 * attempt
            log.info(f"[git-pull] retrying after {backoff}s...")
            time.sleep(backoff)

    return False, last_err
