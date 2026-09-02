from __future__ import annotations

import email
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.header import decode_header

_FORMAT_PATCH_PREFIX = re.compile(r"^\[PATCH[^\]]*\]\s*")

# Mozilla's own commit-workflow conventions (Bug NNNNN, No bug, r=/a= approval tags). Rebasing
# onto the release tag doesn't land HEAD exactly on Tim's first patch - confirmed against the
# real esr140 history, which has a couple of stray upstream lint-fix commits between the tag
# and the patch stack (matching Patches/README.md's own note that the real base is a specific
# commit SHA, not the tag). current_upstream_tag..HEAD narrows things down to nearly just the
# patch stack; this is a defensive second pass to drop what slips through.
_UPSTREAM_COMMIT_PATTERN = re.compile(r"^(Bug\s+\d+|No\s+[Bb]ug|Backed out|Merge)\b", re.IGNORECASE)
_UPSTREAM_APPROVAL_TAG = re.compile(r"\br=\w+|\ba=\w+")


def _looks_like_upstream_commit(subject: str) -> bool:
    return bool(_UPSTREAM_COMMIT_PATTERN.match(subject) or _UPSTREAM_APPROVAL_TAG.search(subject))


@dataclass
class ReleaseData:
    version: str
    esr_version: str
    mfsa_number: str | None
    mfsa_url: str | None
    announced_date: str | None
    cves: list = field(default_factory=list)          # [{id, title, impact, url}]
    ducksteps_changes: list = field(default_factory=list)  # [str]
    artifacts: list = field(default_factory=list)      # [{name, sha512, vt_url}]
    title: str = ""
    summary: str = ""
    release_date: str = ""  # "14/August/2026" - set once so both renderers agree
    # Optional prose sections rendered ABOVE the security content, as
    # [{"heading": str, "body": [str, ...]}]. Empty for ordinary point releases, which
    # carry no features by definition (an ESR line only ever receives security fixes).
    # Populated for an ESR migration, where the interesting part of the release is the
    # thirteen versions of upstream work the new line drags in, not the CVE list.
    # Deliberately caller-supplied: Mozilla publishes no machine-readable "what changed
    # between two ESR lines" feed, so this content is curated per migration rather than
    # invented by the script.
    extra_sections: list = field(default_factory=list)


def _run_git(args, cwd, logger=None, timeout=60):
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    if result.returncode != 0:
        if logger:
            logger.warning("git %s failed in %s: %s", " ".join(args), cwd, result.stderr.strip())
        return None
    return result.stdout


def _current_patch_subjects(source_dir, current_upstream_tag, logger=None) -> list:
    """Tim's patch stack for this release, in order. current_upstream_tag..HEAD gets rid of
    the bulk of upstream noise (everything between the old and new releases); the upstream
    commit-pattern filter is a defensive second pass for the couple of stray commits that
    can still land between the tag and Tim's first patch."""
    output = _run_git(["log", "--pretty=format:%s", f"{current_upstream_tag}..HEAD"], source_dir, logger=logger)
    if output is None:
        return []
    subjects = [line.strip() for line in output.splitlines() if line.strip()]
    return [s for s in subjects if not _looks_like_upstream_commit(s)]


def _extract_patch_subject(patch_file_content: str) -> str | None:
    """git format-patch folds a long Subject onto a continuation line (RFC 2822) and
    MIME-encodes it (RFC 2047) whenever it contains non-ASCII characters. A plain
    "Subject:\\s*(.+)$" regex only ever sees the first line, so a wrapped or encoded
    subject came back truncated/garbled and silently failed to match the un-truncated
    subject that `git log --pretty=%s` returns for the same commit - every such patch
    was then wrongly reported as "new" in get_ducksteps_changes, every release. Parsing
    the header block with `email` handles both correctly.
    """
    _, _, header_block = patch_file_content.partition("\n")  # drop the mbox "From <sha> ..." line
    raw_subject = email.message_from_string(header_block).get("Subject")
    if not raw_subject:
        return None
    raw_subject = re.sub(r"\r?\n", "", raw_subject)  # unfold: fold-point whitespace is already in the text
    subject = "".join(
        part.decode(encoding or "utf-8", errors="replace") if isinstance(part, bytes) else part
        for part, encoding in decode_header(raw_subject)
    )
    return _FORMAT_PATCH_PREFIX.sub("", subject.strip())


def _previous_patch_subjects(repo_dir, prev_version_tag, logger=None) -> set | None:
    """Subjects of Patches/*.patch as they existed at the docs-repo tag for the previous
    ducksteps release. Returns None (not an empty set) when that can't be determined - the
    caller must not confuse "unknown" with "nothing was different"."""
    # <tag>:Patches (colon syntax) addresses the subtree's contents directly. A bare
    # "ls-tree <tag> Patches" instead lists Patches as a single tree ENTRY at the root
    # ("040000 tree <sha> Patches"), not what's inside it - confirmed by testing this
    # against a real Patches/ directory, which silently looked identical to "not found".
    listing = _run_git(["ls-tree", "--name-only", f"{prev_version_tag}:Patches"], repo_dir, logger=logger)
    if not listing:
        return None

    subjects = set()
    for name in listing.splitlines():
        name = name.strip()
        if not name.endswith(".patch"):
            continue
        content = _run_git(["show", f"{prev_version_tag}:Patches/{name}"], repo_dir, logger=logger)
        if content is None:
            continue
        subject = _extract_patch_subject(content)
        if subject:
            subjects.add(subject)
    return subjects or None


def _find_previous_version_tag(repo_dir, current_version, logger=None) -> str | None:
    def _version_key(tag):
        try:
            return tuple(int(part) for part in tag.split("."))
        except ValueError:
            return None

    listing = _run_git(["tag", "-l"], repo_dir, logger=logger)
    if listing is None:
        return None

    current_key = _version_key(current_version)
    candidates = []
    for tag in listing.splitlines():
        key = _version_key(tag.strip())
        if key is not None and key < current_key:
            candidates.append((key, tag.strip()))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def get_ducksteps_changes(source_dir, repo_dir, current_upstream_tag, current_version, logger=None) -> list:
    """True delta since the previous shipped release: patch-stack commit subjects that are new
    relative to what shipped last time (compared against Patches/ at the docs repo's previous
    version tag). Falls back to the full current stack - clearly logged, never silent - when
    the previous release's data isn't available (e.g. the very first release this runs for).
    """
    current_subjects = _current_patch_subjects(source_dir, current_upstream_tag, logger=logger)

    prev_version_tag = _find_previous_version_tag(repo_dir, current_version, logger=logger)
    if prev_version_tag is None:
        if logger:
            logger.warning("no earlier version tag found in %s; showing the full current patch stack", repo_dir)
        return current_subjects

    previous_subjects = _previous_patch_subjects(repo_dir, prev_version_tag, logger=logger)
    if previous_subjects is None:
        if logger:
            logger.warning(
                "no Patches/ data at %s in %s; showing the full current patch stack",
                prev_version_tag, repo_dir,
            )
        return current_subjects

    new_subjects = [s for s in current_subjects if s not in previous_subjects]
    if logger:
        logger.info(
            "ducksteps_changes: %d new/changed of %d current patches (vs %s)",
            len(new_subjects), len(current_subjects), prev_version_tag,
        )
    return new_subjects


def _parse_title_summary(text):
    title = None
    summary_lines = []
    mode = None
    for line in text.splitlines():
        if line.startswith("TITLE:"):
            title = line[len("TITLE:"):].strip()
            mode = None
        elif line.startswith("SUMMARY:"):
            summary_lines.append(line[len("SUMMARY:"):].strip())
            mode = "summary"
        elif mode == "summary":
            summary_lines.append(line.strip())
    summary = " ".join(part for part in summary_lines if part) or None
    return title, summary


def _draft_title_and_summary(cves, ducksteps_changes, previous_titles, feature_headlines=None, logger=None):
    """Judgment site 3: claude -p writes ONLY the title and summary paragraph. Everything else
    in ReleaseData is derived from the YAML/artifacts - the model never sees or produces a CVE ID."""
    severity_counts = {}
    for cve in cves:
        impact = cve.get("impact", "unknown")
        severity_counts[impact] = severity_counts.get(impact, 0) + 1
    counts_text = ", ".join(f"{n} {level}" for level, n in severity_counts.items()) or "zero"

    previous_text = "\n".join(f'- "{t}"' for t in previous_titles) or "(no previous releases to reference)"
    changes_text = "; ".join(ducksteps_changes) if ducksteps_changes else "none - pure upstream sync"

    if feature_headlines:
        # Migration release: the CVE list is routine, the thirteen versions of upstream
        # features are not. Steer both title and summary at the features, and hand over the
        # exact headlines so the model has no reason to invent any.
        features_text = "; ".join(feature_headlines)
        title_instruction = (
            "A short witty phrase for the title, in the style of the previous titles above "
            "(they follow the pattern: It's the \"<phrase>\" release! - give me just the "
            "phrase). This release jumps a whole ESR line, so base the phrase on the NEW "
            "FEATURES below rather than on the CVE count. Only reference features from this "
            f"list, do not invent any:\n{features_text}"
        )
        summary_instruction = (
            "A one-paragraph summary in the voice above, led by what users actually get: this "
            "is the first build on the new ESR line, so it carries thirteen versions of "
            "upstream work at once. Draw only on the feature list above; do not invent "
            "features, and do not name or invent any CVE IDs or bug numbers. Mention the "
            "security fixes briefly at the end - the per-severity counts and total given "
            "above, and nothing more specific - since they are the routine part this time."
        )
    elif cves:
        title_instruction = (
            "A short witty phrase for the title, in the style of the previous titles above "
            "(they follow the pattern: It's the \"<phrase>\" release! - give me just the phrase)."
        )
        summary_instruction = (
            "A one-paragraph summary of the security fixes, in the voice above. State the "
            "severity breakdown explicitly (the per-severity counts given above, and the total) - "
            "this paragraph is the only place the reader gets it, since the release notes no "
            "longer list the CVEs individually. Beyond that, do not name or invent any CVE IDs, "
            "bug numbers, or specific vulnerability names - just characterize the release at a "
            "high level (whether anything stands out)."
        )
    else:
        title_instruction = (
            "A short witty phrase for the title, in the style of the previous titles above "
            "(they follow the pattern: It's the \"<phrase>\" release! - give me just the phrase)."
        )
        summary_instruction = (
            "A one-sentence note that this release has no security content this round - just an "
            "upstream sync (plus whatever ducksteps changes were listed above, if any)."
        )

    features_block = ""
    if feature_headlines:
        joined = "\n".join(f"- {f}" for f in feature_headlines)
        features_block = (
            "\nThis release is the first on a NEW ESR line, so it also brings thirteen "
            f"versions of upstream Firefox work at once. The notable additions are:\n{joined}\n"
        )

    prompt = (
        "You are writing the title and summary paragraph for a ducksteps release. ducksteps is "
        "a custom Firefox ESR build for AMD Zen5, maintained by one person as a side project.\n\n"
        "Voice: casual maker/devlog voice, playful, blunt, self-aware, minimal hype, occasional "
        "mild self-deprecation. Not corporate, not hypey, not apologetic.\n\n"
        f"This release: {counts_text} CVEs addressed. ducksteps-side changes this round: {changes_text}.\n"
        f"{features_block}\n"
        f"Previous release titles, for tone reference:\n{previous_text}\n\n"
        "Write:\n"
        f"1. {title_instruction}\n"
        f"2. {summary_instruction}\n\n"
        "Respond in exactly this format, nothing else:\n"
        "TITLE: <phrase>\n"
        "SUMMARY: <paragraph>"
    )

    try:
        result = subprocess.run(
            ["claude", "-p", prompt], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )
        if result.returncode != 0:
            if logger:
                logger.warning("claude -p title/summary draft failed: %s", result.stderr.strip())
            return None, None
        return _parse_title_summary(result.stdout)
    except (subprocess.SubprocessError, OSError) as exc:
        if logger:
            logger.warning("could not invoke claude -p for title/summary: %s", exc)
        return None, None


def build_release_data(*, version, esr_version, advisory, ducksteps_changes, artifacts, previous_titles,
                       extra_sections=None, feature_headlines=None, logger=None) -> ReleaseData:
    title, summary = _draft_title_and_summary(
        advisory.cves, ducksteps_changes, previous_titles,
        feature_headlines=feature_headlines, logger=logger,
    )
    now = datetime.now(timezone.utc)
    return ReleaseData(
        extra_sections=list(extra_sections or []),
        version=version,
        esr_version=esr_version,
        mfsa_number=advisory.mfsa_number,
        mfsa_url=advisory.mfsa_url,
        announced_date=advisory.announced_date,
        cves=advisory.cves,
        ducksteps_changes=ducksteps_changes,
        artifacts=artifacts,
        title=title or "untitled",
        summary=summary or "",
        release_date=f"{now.day}/{now.strftime('%B')}/{now.year}",
    )


def _upstream_sync_lines(data: ReleaseData) -> list:
    """One line per ducksteps-side change, each its own bullet rather than a semicolon-joined
    run-on sentence. Each entry in ducksteps_changes carries its own tailored leading emoji -
    that pairing is a judgment call (what a change IS, not just its raw commit subject), so it
    is made where the list is curated, not invented here from a fixed keyword table."""
    lines = [f"🔄 Updated to Firefox ESR {data.version}."]
    if data.ducksteps_changes:
        lines.append("")
        lines.extend(data.ducksteps_changes)
    else:
        lines.append("")
        lines.append("Pure upstream sync; no ducksteps-side changes this round.")
    return lines


def _extra_sections(data: ReleaseData) -> list:
    lines = []
    for section in data.extra_sections:
        lines.append(section["heading"])
        lines.append("")
        lines.extend(section["body"])
        lines.append("")
    return lines


def _security_paragraph(data: ReleaseData) -> list:
    """The whole of the security content: a count, a link to the advisory, and the drafted
    summary. Releases used to follow this with every CVE broken out by severity, one linked
    bullet each - at 50+ CVEs an advisory that buried everything else in the notes, and the
    advisory itself is a better place to read the full list than a copy of it here. The
    severity breakdown survives inside data.summary, which _draft_title_and_summary is told
    to spell out for exactly that reason."""
    if not data.cves:
        return []
    return [
        f"🛡️ Addressed {len(data.cves)} CVEs from "
        f"[Mozilla Foundation Security Advisory {data.mfsa_number}]({data.mfsa_url}) "
        f"({data.announced_date}). {data.summary}",
        "",
    ]


def render_release_notes(data: ReleaseData) -> str:
    # No title line here. GitHub already renders release.name above the body, so emitting
    # it again just repeats the same sentence twice on the release page. The changelog
    # renderer DOES keep it, because there each entry is only introduced by a "## [version]"
    # heading and would otherwise lose the phrase entirely.
    lines = _upstream_sync_lines(data) + [""]
    lines.extend(_extra_sections(data))  # features first: on a migration that is the story
    lines.extend(_security_paragraph(data))

    lines.append("---")
    lines.append("")
    lines.append("✅ SHA512:")
    lines.append("")
    for artifact in data.artifacts:
        lines.append(artifact["name"])
        lines.append(f"`{artifact['sha512']}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("🚨 VirusTotal Results:")
    lines.append("")
    for artifact in data.artifacts:
        # blank line between each entry - confirmed against Tim's real published 140.13.0
        # release body, which has one; the SHA512 section above already matched this.
        lines.append(f"[{artifact['name']}]({artifact['vt_url']})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_changelog_entry(data: ReleaseData) -> str:
    lines = [
        f"## [{data.version}] ({data.release_date})", "",
        f'⛐ It\'s the "{data.title}" release!', "",
    ]
    lines.extend(_upstream_sync_lines(data))
    lines.append("")
    lines.extend(_extra_sections(data))
    lines.extend(_security_paragraph(data))
    return "\n".join(lines).rstrip() + "\n"
