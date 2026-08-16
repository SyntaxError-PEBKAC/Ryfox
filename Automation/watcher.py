from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import requests

import common
import notify

FIREFOX_VERSIONS_URL = "https://product-details.mozilla.org/1.0/firefox_versions.json"

# pending_release.status values that mean "Tim hasn't weighed in yet, keep asking."
# Anything else (approved / rejected / building / shipped) is a decided, terminal state.
OPEN_STATUSES = {"awaiting_tag", "awaiting_approval"}


def read_current_version(source_dir: Path) -> str:
    return (source_dir / "browser" / "config" / "version.txt").read_text(encoding="utf-8").strip()


def select_tracked_line(data, esr_major, logger=None):
    """Find whichever upstream field currently carries the tracked ESR major.

    During an ESR transition upstream ships two ESR lines in parallel for about twelve
    weeks, and product-details splits them across two keys: FIREFOX_ESR stays on the OLD
    line (it is what firefox.com still hands out by default) while FIREFOX_ESR_NEXT
    carries the new one. The new line only moves into FIREFOX_ESR once the transition
    closes and FIREFOX_ESR_NEXT empties out again.

    So the field to read depends on where the tracked major currently sits, and that
    changes underneath us mid-line. Reading FIREFOX_ESR alone was survivable for the
    whole of the 140 line - there was no transition in progress to misread - but the
    moment esr_major is bumped to the new line it means seeing nothing at all for the
    entire overlap: FIREFOX_ESR reports the old major, the major check fails, and the
    point-release check is skipped every run while new releases actually ship.

    Returns (field_name, version_string, (major, minor, patch)) or None if the tracked
    major is in neither field.
    """
    for field in ("FIREFOX_ESR", "FIREFOX_ESR_NEXT"):
        value = (data.get(field) or "").strip()
        if not value:
            continue
        try:
            parsed = common.parse_esr_version(value)
        except ValueError:
            if logger:
                logger.warning("could not parse %s=%r, ignoring that field", field, value)
            continue
        if parsed[0] == esr_major:
            return field, value, parsed
    return None


def newest_upstream_major(data, logger=None):
    """Highest ESR major visible in either field, used only to decide whether a NEWER line
    than the tracked one has been cut. Deliberately not "is FIREFOX_ESR_NEXT non-empty":
    once esr_major is bumped onto the new line, ESR_NEXT stays populated with that very
    same line for the rest of the overlap, and keying off its mere presence would re-fire
    the migration alert for weeks after the migration was already done."""
    majors = []
    for field in ("FIREFOX_ESR", "FIREFOX_ESR_NEXT"):
        value = (data.get(field) or "").strip()
        if not value:
            continue
        try:
            majors.append(common.parse_esr_version(value)[0])
        except ValueError:
            if logger:
                logger.warning("could not parse %s=%r for major comparison", field, value)
    return max(majors) if majors else None


def send_migration_alert(config, logger, dry_run, newest_major, newest_version, esr_major):
    reason = (
        f"Upstream has cut ESR {newest_major} ({newest_version}); tracked major is still {esr_major}. "
        f"Both lines ship in parallel for roughly twelve weeks, and the new one lives in "
        f"FIREFOX_ESR_NEXT until that window closes."
    )
    title = f"ducksteps: ESR {newest_major} migration window open"
    body = f"{reason} This is a supervised manual procedure. No build was triggered."

    logger.warning("MIGRATION alert: %s", reason)
    if dry_run:
        logger.info("[dry-run] would notify: %s | %s", title, body)
        return
    notify.publish(config, title, body, priority="high", tags=["warning"])


def send_gate1(config, logger, dry_run, version):
    logger.info("Gate 1: %s ready to build, notifying", version)
    if dry_run:
        logger.info("[dry-run] would send Gate 1 notification for %s", version)
        return
    notify.send_gate1(config, version)


def check_point_release(config, logger, dry_run, state, source_dir, major, minor, patch) -> bool:
    """Returns True on success (even 'nothing new'), False if this cycle hit an error."""
    try:
        current_version = read_current_version(source_dir)
    except OSError as exc:
        logger.error("could not read local version.txt: %s", exc)
        return False

    candidate_version = common.version_number(major, minor, patch)
    pending = state.get("pending_release")

    already_decided = (
        pending
        and pending.get("version") == candidate_version
        and pending.get("status") not in OPEN_STATUSES
    )

    if candidate_version == current_version:
        logger.info("no new release: upstream (%s) matches local tree", candidate_version)
        return True

    if already_decided:
        logger.info("release %s already %s, not re-notifying", candidate_version, pending["status"])
        return True

    tag = common.release_tag(major, minor, patch)
    try:
        available = common.tag_exists(source_dir, tag)
    except RuntimeError as exc:
        logger.error("tag check failed: %s", exc)
        return False

    first_detected_at = (
        pending["first_detected_at"]
        if pending and pending.get("version") == candidate_version
        else datetime.now(timezone.utc).isoformat()
    )

    if available:
        send_gate1(config, logger, dry_run, candidate_version)
        state["pending_release"] = {
            "version": candidate_version,
            "tag": tag,
            "status": "awaiting_approval",
            "first_detected_at": first_detected_at,
            "last_notified_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        logger.info("release %s detected, tag %s not yet pushed, will retry", candidate_version, tag)
        state["pending_release"] = {
            "version": candidate_version,
            "tag": tag,
            "status": "awaiting_tag",
            "first_detected_at": first_detected_at,
            "last_notified_at": pending.get("last_notified_at") if pending else None,
        }
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="ducksteps release watcher")
    parser.add_argument("--dry-run", action="store_true", help="log actions without sending notifications or saving state")
    args = parser.parse_args()

    config = common.load_config()
    logger = common.setup_logging("watcher")
    state = common.load_state()

    esr_major = config["project"]["esr_major"]
    source_dir = Path(config["project"]["source_dir"])
    had_error = False

    try:
        response = requests.get(FIREFOX_VERSIONS_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.error("failed to fetch firefox_versions.json: %s", exc)
        return 1

    firefox_esr = data.get("FIREFOX_ESR", "")
    firefox_esr_next = data.get("FIREFOX_ESR_NEXT", "")
    logger.info("FIREFOX_ESR=%s FIREFOX_ESR_NEXT=%s", firefox_esr, firefox_esr_next)

    newest_major = newest_upstream_major(data, logger=logger)
    if newest_major is not None and newest_major > esr_major:
        newest = select_tracked_line(data, newest_major, logger=logger)
        newest_version = newest[1] if newest else str(newest_major)
        migration_key = f"esr{newest_major}:{newest_version}"
        if state.get("migration_alert_sent_for") != migration_key:
            send_migration_alert(config, logger, args.dry_run, newest_major, newest_version, esr_major)
            state["migration_alert_sent_for"] = migration_key
        else:
            logger.info("migration already alerted for %s, not re-notifying", migration_key)

    tracked = select_tracked_line(data, esr_major, logger=logger)
    if tracked is None:
        # Not "nothing new" - the tracked line has vanished from upstream's own metadata,
        # which means either esr_major is wrong or the line is end-of-life. Either way it
        # would otherwise look identical to a quiet week, forever.
        logger.error(
            "tracked major %s is in neither FIREFOX_ESR (%s) nor FIREFOX_ESR_NEXT (%s)",
            esr_major, firefox_esr or "<empty>", firefox_esr_next or "<empty>",
        )
        had_error = True
    else:
        field, value, (major, minor, patch) = tracked
        logger.info("tracked ESR %s is upstream's %s = %s", esr_major, field, value)
        ok = check_point_release(config, logger, args.dry_run, state, source_dir, major, minor, patch)
        had_error = had_error or not ok

    state["firefox_esr"] = firefox_esr
    state["firefox_esr_next"] = firefox_esr_next
    state["last_checked_at"] = datetime.now(timezone.utc).isoformat()

    if args.dry_run:
        logger.info("[dry-run] not persisting state.json")
    else:
        common.save_state(state)

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
