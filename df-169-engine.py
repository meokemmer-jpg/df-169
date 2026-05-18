
# K16: Concurrent-Spawn-Mutex (fcntl-based, Trinity-CONSERVATIVE 2026-05-17)
def k16_lock_or_exit(df_name: str):
    """Acquire exclusive lock or exit(3). Prevents concurrent DF runs."""
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)


# K13: External-Anchor-Mock-RFC3161 (Trinity-CONSERVATIVE 2026-05-17)
def k13_anchor(payload_hash: str) -> dict:
    """Mock RFC3161-style timestamp anchor."""
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }


# K12: HMAC-SHA256-Provenance (Trinity-CONSERVATIVE 2026-05-17)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-conservative-v1") -> dict:
    """Returns payload_hash + HMAC-SHA256 signature."""
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

"""DF-169 engine for Buecher-Verlag-Comm communication cadence tracking."""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone

DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-169.lock")
DF_ID = "169"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-169"
    iso_timestamp: str = ""
    source: str = "mock"
    emails_sent: int = 0
    emails_received: int = 0
    response_time_avg_days: float = 0
    open_threads: int = 0
    escalations: list = field(default_factory=list)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    try:
        return (time.time() - p.stat().st_mtime) >= min_age_sec
    except OSError:
        return False


def acquire_lock_with_identity() -> bool:
    stale_after_sec = 6 * 60 * 60
    now = time.time()

    try:
        LOCK_DIR.mkdir(mode=0o700)
    except FileExistsError:
        try:
            age = now - LOCK_DIR.stat().st_mtime
        except OSError:
            return False

        if age < stale_after_sec:
            return False

        try:
            for child in LOCK_DIR.iterdir():
                if child.is_file() or child.is_symlink():
                    child.unlink()
            LOCK_DIR.rmdir()
            LOCK_DIR.mkdir(mode=0o700)
        except OSError:
            return False
    except OSError:
        return False

    identity = {
        "df_id": DF_ID,
        "pid": os.getpid(),
        "created_at": iso_now(),
        "cwd": os.getcwd(),
    }
    try:
        (LOCK_DIR / "identity.json").write_text(
            json.dumps(identity, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        release_lock()
        return False

    return True


def release_lock() -> None:
    try:
        if not LOCK_DIR.exists():
            return
        for child in LOCK_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
        LOCK_DIR.rmdir()
    except OSError:
        return


def k17_pre_action_verification(anchors) -> dict:
    missing = []
    for anchor in anchors or []:
        if isinstance(anchor, Path):
            exists = anchor.exists()
        else:
            value = str(anchor)
            candidate = Path(value)
            exists = bool(os.environ.get(value)) or candidate.exists()
            if not exists and not candidate.is_absolute():
                exists = (DF_DIR / value).exists()
        if not exists:
            missing.append(str(anchor))

    return {
        "ok": len(missing) == 0,
        "missing_anchors": missing,
        "env_tag": os.environ.get("DF_169_ENV_TAG", "local"),
    }


def _is_real_api_enabled() -> bool:
    return os.environ.get("DF_169_REAL_API_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    return sorted({match.group(0) for match in DECISION_KEYWORDS_REGEX.finditer(str(text))})


def assert_no_decision_keywords(output) -> None:
    text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    hits = scan_output_for_decision_keywords(text)
    if hits:
        raise ValueError(f"Q_0/K_0 decision keyword block triggered: {', '.join(hits)}")


def _env_int(name, default=0) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_float(name, default=0.0) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_list(name) -> list:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        return [item.strip() for item in raw.split(",") if item.strip()]


def collect_tracker_output() -> TrackerOutput:
    output = TrackerOutput(iso_timestamp=iso_now())

    if _is_real_api_enabled():
        output.source = "env"
        output.emails_sent = _env_int("DF_169_EMAILS_SENT")
        output.emails_received = _env_int("DF_169_EMAILS_RECEIVED")
        output.response_time_avg_days = _env_float("DF_169_RESPONSE_TIME_AVG_DAYS")
        output.open_threads = _env_int("DF_169_OPEN_THREADS")
        output.escalations = _env_list("DF_169_ESCALATIONS")

    return output


def main() -> int:
    if not acquire_lock_with_identity():
        return 3

    try:
        pav = k17_pre_action_verification([DF_DIR])
        if not pav.get("ok"):
            return 3

        tracker_output = collect_tracker_output()
        payload = asdict(tracker_output)
        payload["k17_pre_action_verification"] = pav

        assert_no_decision_keywords(payload)

        report_dir = DF_DIR / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        report_path = report_dir / f"df-169-{date_tag}.json"
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())