from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

_DEFAULT_LOGGER = logging.getLogger("notify")

# Notification matrix (Phase 3 spec): event -> priority.
PRIORITIES = {
    "gate1": "default",
    "build_started": "low",
    "retrying": "low",
    "smoke_ready": "high",
    "fatal_error": "urgent",
    "vt_flagged": "urgent",
    "draft_ready": "high",
    "published": "default",
}

SNOOZE_INTERVAL_SECONDS = 3 * 3600
MAX_SNOOZES = 3
# Per-connection idle timeout for poll_topic, not a reconnect cadence: requests'
# timeout= during streaming is a read/inactivity timeout that resets on every
# received chunk, and ntfy sends a keepalive well under 60s, so one connection
# normally holds for the whole snooze window. This only fires if the server
# actually goes quiet.
POLL_SECONDS = 60


def _encode_header(value: str) -> bytes:
    """ntfy titles/actions carry emoji; http.client refuses non-latin1 str headers, so send raw UTF-8 bytes."""
    return value.encode("utf-8")


def _headers(title, priority, *, actions=None, tags=None, click=None, message=None, filename=None) -> dict:
    headers = {"Title": _encode_header(title), "Priority": priority}
    if actions:
        headers["Actions"] = _encode_header("; ".join(actions))
    if tags:
        headers["Tags"] = ",".join(tags)
    if click:
        headers["Click"] = click
    if message is not None:
        headers["Message"] = _encode_header(message)
    if filename:
        headers["Filename"] = filename
    return headers


def _topic_url(config: dict, topic_key: str) -> str:
    ntfy = config["ntfy"]
    topic = ntfy[topic_key]
    if not topic:
        raise RuntimeError(f"ntfy {topic_key} is not configured (check .env)")
    return f"{ntfy['server'].rstrip('/')}/{topic}"


def publish(config, title, body, *, priority="default", actions=None, tags=None, click=None) -> None:
    url = _topic_url(config, "notify_topic")
    headers = _headers(title, priority, actions=actions, tags=tags, click=click)
    response = requests.post(url, data=body.encode("utf-8"), headers=headers, timeout=15)
    response.raise_for_status()


def publish_file(config, title, message, file_path, *, priority="default", actions=None, tags=None) -> None:
    url = _topic_url(config, "notify_topic")
    file_path = Path(file_path)
    headers = _headers(title, priority, actions=actions, tags=tags, message=message, filename=file_path.name)
    with open(file_path, "rb") as f:
        response = requests.put(url, data=f, headers=headers, timeout=60)
    response.raise_for_status()


def _approve_url(config: dict) -> str:
    return _topic_url(config, "approve_topic")


# --- Notification matrix: one function per event type ---

def send_gate1(config, version) -> None:
    approve_url = _approve_url(config)
    actions = [
        f"http, ✅ Approve, {approve_url}, method=POST, body=approve-{version}",
        f"http, ⏰ Wait 3h, {approve_url}, method=POST, body=snooze-{version}",
        f"http, \U0001f6d1 Reject, {approve_url}, method=POST, body=reject-{version}",
    ]
    publish(
        config,
        title=f"ducksteps {version} ready to build",
        body="Upstream tagged. Both variants, roughly 10 hours.",
        priority=PRIORITIES["gate1"],
        actions=actions,
    )


def send_build_started(config, version) -> None:
    publish(
        config,
        title=f"ducksteps {version} build started",
        body="PREFLIGHT passed, pipeline running. Expect roughly 10 hours.",
        priority=PRIORITIES["build_started"],
    )


def send_retrying(config, version, reason) -> None:
    publish(
        config,
        title=f"ducksteps {version} retrying",
        body=f"Known-recoverable failure, retrying once: {reason}",
        priority=PRIORITIES["retrying"],
    )


def send_smoke_test_ready(config, version, variant, screenshot_path) -> None:
    approve_url = _approve_url(config)
    actions = [
        f"http, ✅ Looks good, {approve_url}, method=POST, body=smoke-ok-{version}-{variant}",
        f"http, \U0001f6d1 Reject, {approve_url}, method=POST, body=smoke-reject-{version}-{variant}",
    ]
    publish_file(
        config,
        title=f"ducksteps {version} {variant} smoke test",
        message="Firefox launched, here's the window. Approve to continue packaging.",
        file_path=screenshot_path,
        priority=PRIORITIES["smoke_ready"],
        actions=actions,
    )


def send_fatal_error(config, version, summary, log_path) -> None:
    # No remote log-viewing mechanism exists in this project (web dashboards are
    # explicitly out of scope), so unlike the other gates this has no real target
    # for a button. The path goes in the body text instead of a dead "View log" action.
    publish(
        config,
        title=f"ducksteps {version} FATAL",
        body=f"{summary}\n\nLog: {log_path}",
        priority=PRIORITIES["fatal_error"],
    )


def send_vt_flagged(config, version, summary) -> None:
    approve_url = _approve_url(config)
    actions = [
        f"http, ✅ Approve, {approve_url}, method=POST, body=vt-approve-{version}",
        f"http, \U0001f6d1 Halt, {approve_url}, method=POST, body=vt-halt-{version}",
    ]
    publish(
        config,
        title=f"ducksteps {version} VirusTotal flagged",
        body=summary,
        priority=PRIORITIES["vt_flagged"],
        actions=actions,
    )


def send_draft_ready(config, version, draft_url) -> None:
    approve_url = _approve_url(config)
    actions = [
        f"http, ✅ Publish, {approve_url}, method=POST, body=publish-{version}",
        f"http, \U0001f6d1 Reject, {approve_url}, method=POST, body=reject-draft-{version}",
    ]
    publish(
        config,
        title=f"ducksteps {version} draft ready",
        body=f"Review before it goes public: {draft_url}",
        priority=PRIORITIES["draft_ready"],
        actions=actions,
        click=draft_url,
    )


def send_published(config, version, release_url) -> None:
    publish(
        config,
        title=f"ducksteps {version} published",
        body="It's live.",
        priority=PRIORITIES["published"],
        actions=[f"view, View release, {release_url}"],
        click=release_url,
    )


# --- Receiving: approve_topic long-poll ---

def poll_topic(config, topic_key, timeout_seconds=POLL_SECONDS) -> str | None:
    """One bounded long-poll against an ntfy topic. Returns the first message body seen, or None if the window
    closes with nothing new.

    Deliberately omits `since` (not `since=now`, which ntfy's API rejects with 400):
    an omitted `since` streams only messages published after the connection opens,
    with no cached-backlog replay, confirmed empirically against a topic with a
    pre-existing cached message.

    Timeouts and connection drops are treated as routine and swallowed - a
    read-timeout while streaming surfaces as requests.exceptions.ConnectionError
    (wrapping urllib3's ReadTimeoutError), not requests.exceptions.Timeout, so both
    are caught here. HTTPError (bad status codes) is deliberately NOT caught: that
    means a real misconfiguration, and staying silent there would be indistinguishable
    from "no message yet" for hours - which is exactly how an earlier since="now" bug
    here went undetected until tested directly: ntfy's 400 was swallowed by a
    too-broad except clause.
    """
    ntfy = config["ntfy"]
    topic = ntfy[topic_key]
    url = f"{ntfy['server'].rstrip('/')}/{topic}/json"
    try:
        with requests.get(url, stream=True, timeout=timeout_seconds) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event.get("event") == "message":
                    return event.get("message", "")
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return None
    return None


def send_tap_confirmation(config, action_body) -> None:
    """iOS ntfy issue #1728: clear=true never dismisses the source notification, so echo receipt back explicitly."""
    publish(config, title="ducksteps: got it", body=f"Received: {action_body}", priority="default")


def await_decision(config, timeout_seconds, valid_bodies, logger=None) -> str:
    """
    Long-polls the approve_topic until a message matching a key in `valid_bodies`
    arrives, or timeout_seconds elapses with nothing relevant. Sends the iOS
    tap-confirmation workaround on any match. `valid_bodies` maps an exact expected
    message body (e.g. "smoke-ok-140.14.0-zen5") to the outcome string to return
    for it (e.g. "approved"). Returns "no_response" on timeout.
    """
    log = logger or _DEFAULT_LOGGER
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        message = poll_topic(config, "approve_topic", timeout_seconds=min(POLL_SECONDS, remaining))
        if not message:
            continue
        if message in valid_bodies:
            send_tap_confirmation(config, message)
            return valid_bodies[message]
        log.info("ignoring unrelated approve-topic message: %s", message)
    return "no_response"


def await_gate1_decision(config, version, logger=None) -> str:
    """
    Waits for a response to an already-sent Gate 1 notification for `version`.
    Snooze policy: up to MAX_SNOOZES re-asks, SNOOZE_INTERVAL_SECONDS apart.
    Returns "approved", "rejected", or "no_response".
    """
    log = logger or _DEFAULT_LOGGER
    snoozes_used = 0
    valid_bodies = {
        f"approve-{version}": "approved",
        f"reject-{version}": "rejected",
        f"snooze-{version}": "snooze",
    }

    while True:
        log.info(
            "waiting up to %.0fm for a Gate 1 response on %s (snooze %d/%d used)",
            SNOOZE_INTERVAL_SECONDS / 60, version, snoozes_used, MAX_SNOOZES,
        )
        outcome = await_decision(config, SNOOZE_INTERVAL_SECONDS, valid_bodies, logger=log)

        if outcome != "snooze":
            return outcome  # "approved" / "rejected" / "no_response"

        snoozes_used += 1
        if snoozes_used > MAX_SNOOZES:
            log.info("snooze cap reached for %s, stopping until the next watcher run", version)
            return "no_response"
        log.info("snoozed (%d/%d), re-asking in %.0fh", snoozes_used, MAX_SNOOZES, SNOOZE_INTERVAL_SECONDS / 3600)
        send_gate1(config, version)
