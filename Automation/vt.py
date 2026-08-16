from __future__ import annotations

import os
import re
import subprocess
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import requests

VT_BASE = "https://www.virustotal.com/api/v3"
LARGE_FILE_THRESHOLD_BYTES = 32 * 1024 * 1024

POLL_INTERVAL_SECONDS = 30
POLL_MAX_MINUTES = 40
TERMINAL_STATUSES = {"completed", "partial"}

# "a detection names a real malware family" (Phase 5 spec): a result string that does NOT
# match one of these counts as a real family name, not noise, and skips the ladder entirely.
GENERIC_RESULT_PATTERN = re.compile(r"Generic|Heuristic|ML|AI|Trojan\.Gen|Unsafe|Suspicious", re.IGNORECASE)
IMMEDIATE_HALT_ENGINE_COUNT = 3


class VTError(Exception):
    pass


class VTTimeoutError(VTError):
    pass


class TokenBucket:
    """4 requests/minute throttle for VT's free tier - without it you eat 429s mid-ladder."""

    def __init__(self, max_calls=4, per_seconds=60):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._calls = deque()

    def acquire(self) -> None:
        while True:
            now = time.monotonic()
            while self._calls and now - self._calls[0] >= self.per_seconds:
                self._calls.popleft()
            if len(self._calls) < self.max_calls:
                self._calls.append(now)
                return
            time.sleep(self._calls[0] + self.per_seconds - now)


def _api_key() -> str:
    key = os.environ.get("VT_API_KEY")
    if not key:
        raise VTError("VT_API_KEY is not set in the environment")
    return key


def _headers() -> dict:
    return {"x-apikey": _api_key()}


@dataclass
class Verdict:
    stats: dict
    results: dict  # engine_name -> {"category": ..., "result": ..., ...}
    # Crowdsourced Sigma matches. Purely informational and deliberately kept out of
    # classify(): these are community rules matched against VT's SANDBOX telemetry, not
    # engine verdicts, and VT itself excludes them from the detection score. Our installers
    # have always matched four of them (three medium, one low) purely for being an unsigned
    # self-extracting archive that writes a hundred PE files. Recording them means a CHANGE
    # is visible release over release, which is the part actually worth knowing.
    sigma_summary: dict = field(default_factory=dict)  # ruleset -> {critical, high, medium, low}
    sigma_rules: list = field(default_factory=list)    # [{"level", "title", "source"}]


def _sigma_from_file_attrs(attrs) -> tuple[dict, list]:
    summary = attrs.get("sigma_analysis_summary") or {}
    rules = [
        {
            "level": entry.get("rule_level", ""),
            "title": entry.get("rule_title", ""),
            "source": entry.get("rule_source", ""),
        }
        for entry in (attrs.get("sigma_analysis_results") or [])
    ]
    rules.sort(key=lambda r: (r["level"], r["title"]))
    return summary, rules


def _verdict_from_file_attrs(attrs) -> Verdict:
    sigma_summary, sigma_rules = _sigma_from_file_attrs(attrs)
    return Verdict(
        stats=attrs.get("last_analysis_stats", {}),
        results=attrs.get("last_analysis_results", {}),
        sigma_summary=sigma_summary,
        sigma_rules=sigma_rules,
    )


def _verdict_from_analysis_attrs(attrs) -> Verdict:
    # No Sigma here on purpose: the /analyses object never carries it. It only lands on the
    # /files object once the sandbox run is processed, which submit_file fetches separately.
    return Verdict(stats=attrs.get("stats", {}), results=attrs.get("results", {}))


def get_existing_report(sha256, bucket, timeout=30) -> Verdict | None:
    bucket.acquire()
    r = requests.get(f"{VT_BASE}/files/{sha256}", headers=_headers(), timeout=timeout)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return _verdict_from_file_attrs(r.json()["data"]["attributes"])


def _get_upload_url(bucket, timeout=30) -> str:
    bucket.acquire()
    r = requests.get(f"{VT_BASE}/files/upload_url", headers=_headers(), timeout=timeout)
    r.raise_for_status()
    return r.json()["data"]


def _upload(url, file_path, bucket, timeout=600) -> str:
    file_path = Path(file_path)
    bucket.acquire()
    with open(file_path, "rb") as f:
        r = requests.post(url, headers=_headers(), files={"file": (file_path.name, f)}, timeout=timeout)
    r.raise_for_status()
    return r.json()["data"]["id"]


def _poll_analysis(analysis_id, bucket, logger=None, interval=POLL_INTERVAL_SECONDS, max_minutes=POLL_MAX_MINUTES) -> Verdict:
    deadline = time.monotonic() + max_minutes * 60
    while True:
        bucket.acquire()
        r = requests.get(f"{VT_BASE}/analyses/{analysis_id}", headers=_headers(), timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        status = data["attributes"]["status"]
        if status in TERMINAL_STATUSES:
            return _verdict_from_analysis_attrs(data["attributes"])
        if time.monotonic() >= deadline:
            raise VTTimeoutError(
                f"analysis {analysis_id} did not reach a terminal status within {max_minutes}m (last: {status})"
            )
        if logger:
            logger.info("VT analysis %s status=%s, polling again in %ds", analysis_id, status, interval)
        time.sleep(interval)


def submit_file(file_path, sha256, bucket, logger=None) -> Verdict:
    """Submits file_path for scanning, or reuses an existing report for the same hash (free
    dedup, avoids re-uploading identical artifacts). Handles the >32MB two-step upload flow
    transparently - files that size cannot use POST /files directly.
    """
    file_path = Path(file_path)
    existing = get_existing_report(sha256, bucket)
    if existing is not None:
        if logger:
            logger.info("hash %s already known to VT, reusing existing report", sha256[:16])
        return existing

    size = file_path.stat().st_size
    upload_url = _get_upload_url(bucket) if size > LARGE_FILE_THRESHOLD_BYTES else f"{VT_BASE}/files"

    if logger:
        logger.info("submitting %s (%.1fMB) to VT", file_path.name, size / (1024 * 1024))
    analysis_id = _upload(upload_url, file_path, bucket)
    verdict = _poll_analysis(analysis_id, bucket, logger=logger)

    # One extra read to pick up Sigma, which the analysis object does not carry. Sandbox
    # processing lags the AV scan and may not have finished, so an empty result here is
    # normal rather than an error. Strictly best effort: Sigma is informational, and a
    # release must never be held up or failed over it.
    try:
        refreshed = get_existing_report(sha256, bucket)
        if refreshed is not None:
            verdict.sigma_summary = refreshed.sigma_summary
            verdict.sigma_rules = refreshed.sigma_rules
        if logger and not verdict.sigma_rules:
            logger.info("no Sigma results yet for %s (sandbox run still pending)", file_path.name)
    except requests.RequestException as exc:
        if logger:
            logger.warning("could not fetch Sigma results for %s: %s", file_path.name, exc)

    return verdict


@dataclass
class Classification:
    status: str  # "PASS" | "KNOWN_NOISE" | "NEW_DETECTIONS" | "IMMEDIATE_HALT"
    detections: dict  # engine -> result info, malicious/suspicious entries only
    reason: str


def classify(verdict: Verdict, previous_engines: set | None = None) -> Classification:
    detections = {
        engine: info for engine, info in verdict.results.items()
        if info.get("category") in ("malicious", "suspicious")
    }

    if not detections:
        return Classification("PASS", {}, "zero detections")

    for engine, info in detections.items():
        result = info.get("result") or ""
        if result and not GENERIC_RESULT_PATTERN.search(result):
            return Classification(
                "IMMEDIATE_HALT", detections, f"{engine} names a real malware family ({result!r}), ladder skipped"
            )

    if len(detections) >= IMMEDIATE_HALT_ENGINE_COUNT:
        return Classification(
            "IMMEDIATE_HALT", detections,
            f"{len(detections)} engines agree (>= {IMMEDIATE_HALT_ENGINE_COUNT} threshold), ladder skipped",
        )

    if previous_engines and set(detections.keys()) == previous_engines:
        return Classification("KNOWN_NOISE", detections, "identical flagging engines to the previous shipped release")

    return Classification("NEW_DETECTIONS", detections, f"{len(detections)} new detection(s)")


def draft_fp_submissions(detections, artifact_name, logger=None) -> str | None:
    """Judgment site 2: asks claude -p to draft vendor false-positive submissions once the
    remediation ladder is exhausted. Never invents CVE-style claims - just describes the build."""
    engines = ", ".join(sorted(detections.keys()))
    prompt = (
        f"VirusTotal flagged the ducksteps (custom Firefox ESR build for AMD Zen5) artifact "
        f"{artifact_name!r} on these engines: {engines}. Repackaging with different 7z/installer "
        f"parameters did not clear it, which points to a false positive rather than real malware. "
        f"Draft a short, factual false-positive submission blurb per engine, suitable for pasting "
        f"into each vendor's FP-submission form: what the software is, why it might trip a "
        f"heuristic (PGO-optimized clang-cl build, custom NSIS packaging), and a request for "
        f"reclassification. Keep it factual, no marketing language."
    )
    try:
        result = subprocess.run(
            ["claude", "-p", prompt], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )
        if result.returncode != 0:
            if logger:
                logger.warning("claude -p FP-draft failed: %s", result.stderr.strip())
            return None
        return result.stdout.strip()
    except (subprocess.SubprocessError, OSError) as exc:
        if logger:
            logger.warning("could not invoke claude -p for FP drafting: %s", exc)
        return None
