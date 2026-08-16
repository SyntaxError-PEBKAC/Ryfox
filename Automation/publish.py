from __future__ import annotations

import re
import subprocess
from pathlib import Path

import common

_PATCH_SUBJECT_LINE = re.compile(r"^Subject:\s*(.+)$", re.MULTILINE)
_FORMAT_PATCH_PREFIX = re.compile(r"^\[PATCH[^\]]*\]\s*")

_DOCS_SYNC_FILES = [
    # (relative to source_dir, relative to repo_dir, normalize_to_lf)
    (".mozconfig", "Docs/.mozconfig", False),
    (".mozconfig-Legacy", "Docs/.mozconfig-Legacy", True),
    ("build/pgo/pgo_training_extension/background.js", "Docs/PGO/background.js", False),
    ("build/pgo/pgo_training_extension/manifest.json", "Docs/PGO/manifest.json", False),
    ("build/pgo/pgo_done.html", "Docs/PGO/pgo_done.html", False),
    ("build/pgo/profileserver.py", "Docs/PGO/profileserver.py", False),
]


# The automation source itself is published alongside the release it produced, so the
# pipeline that built an artifact is auditable by whoever downloads it. Globs rather than a
# fixed list so a new module is picked up without anyone remembering to add it here.
_AUTOMATION_SYNC_GLOBS = ("*.py", "*.md", "*.ps1", "config.toml", ".gitignore")

# Never copied, whatever the globs match. This lands in a PUBLIC repo: .env holds the ntfy
# topics, which are in practice the password for the approve-gate buttons (anyone who knows
# the approve topic can approve a build), and state.json carries build state, draft URLs and
# VT history. Enforced by name below rather than left to the globs happening not to match.
_AUTOMATION_NEVER_SYNC = frozenset({".env", "state.json"})
_AUTOMATION_NEVER_SYNC_SUFFIXES = (".key", ".lock", ".log", ".png", ".pyc")


class PublishError(Exception):
    pass


def sync_automation(repo_dir, automation_dir, logger=None) -> list:
    """Copy the automation source into <repo>/Automation/ so the published pipeline matches
    the release it produced. Returns the files written.

    Kept separate from sync_docs_files because that one resolves paths relative to the
    Firefox source tree, and the automation lives outside it.
    """
    automation_dir, repo_dir = Path(automation_dir), Path(repo_dir)
    destination = repo_dir / "Automation"
    destination.mkdir(parents=True, exist_ok=True)

    candidates = sorted({p for glob in _AUTOMATION_SYNC_GLOBS for p in automation_dir.glob(glob)})
    synced = []
    for src in candidates:
        if not src.is_file():
            continue
        if src.name in _AUTOMATION_NEVER_SYNC or src.name.endswith(_AUTOMATION_NEVER_SYNC_SUFFIXES):
            if logger:
                logger.warning("refusing to publish %s (excluded from the public repo)", src.name)
            continue
        dst = destination / src.name
        dst.write_bytes(src.read_bytes())
        synced.append(dst)

    if logger:
        logger.info("synced %d automation file(s) to %s", len(synced), destination)
    return synced


def _run_git(args, cwd, logger=None, timeout=120):
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    if result.returncode != 0:
        message = f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}"
        if logger:
            logger.error(message)
        raise PublishError(message)
    return result.stdout


# --- 1. Export the patch stack ---

def sync_patch_stack(repo_dir, source_dir, upstream_tag, logger=None) -> list:
    repo_dir = Path(repo_dir)
    patches_dir = repo_dir / "Patches"

    _run_git(["pull"], repo_dir, logger=logger)

    for pattern in ("000*.patch", "001*.patch"):
        for f in patches_dir.glob(pattern):
            f.unlink()

    _run_git(
        ["-C", str(source_dir), "format-patch", "--binary", "-o", str(patches_dir), f"{upstream_tag}..HEAD"],
        cwd=None, logger=logger,
    )
    new_patches = sorted(patches_dir.glob("*.patch"))
    if logger:
        logger.info("exported %d patches to %s", len(new_patches), patches_dir)
    return new_patches


# --- 2. Regenerate Patches/README.md ---

def _patch_commit_subjects_ordered(source_dir, upstream_tag, logger=None) -> list:
    """--reverse: oldest first, matching "numbered in the order they were originally
    committed" - render.py's equivalent helper deliberately returns newest-first instead,
    which is right for release-notes display but wrong for this numbered list."""
    output = _run_git(["log", "--reverse", "--pretty=format:%s", f"{upstream_tag}..HEAD"], source_dir, logger=logger)
    return [line.strip() for line in output.splitlines() if line.strip()]


def _upstream_sha(source_dir, upstream_tag, logger=None) -> str:
    return _run_git(["rev-parse", "--short=12", upstream_tag], source_dir, logger=logger).strip()


def regenerate_patches_readme(repo_dir, source_dir, upstream_tag, branch, logger=None) -> Path:
    subjects = _patch_commit_subjects_ordered(source_dir, upstream_tag, logger=logger)
    sha = _upstream_sha(source_dir, upstream_tag, logger=logger)

    patches_dir = Path(repo_dir) / "Patches"
    patch_files = sorted(f.name for f in patches_dir.glob("*.patch"))
    if len(patch_files) <= 3:
        example_range = " ".join(f"Patches/{n}" for n in patch_files)
    else:
        example_range = f"Patches/{patch_files[0]} Patches/{patch_files[1]} ... Patches/{patch_files[-1]}"

    numbered = "\n".join(f"{i}. `{subject}`" for i, subject in enumerate(subjects, start=1))

    content = f"""# ducksteps patch stack

These are the commits that turn a stock Firefox ESR checkout into ducksteps: exported with `git format-patch` from the `{branch}` branch, applied on top of upstream Mozilla commit `{sha}` (see [`../Docs/Building.md`](../Docs/Building.md) for the full build workflow).

To use them: clone [mozilla-firefox/firefox](https://github.com/mozilla-firefox/firefox), check out the matching ESR branch/tag, then apply in order:

```bash
git am {example_range}
```

or all at once:

```bash
git am Patches/*.patch
```

Numbered in the order they were originally committed:

{numbered}
"""
    readme_path = patches_dir / "README.md"
    with open(readme_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    if logger:
        logger.info("regenerated %s: %d patches, base %s", readme_path, len(subjects), sha)
    return readme_path


# --- 3-4. Sync Docs/.mozconfig, .mozconfig-Legacy, Docs/PGO/* ---

def sync_docs_files(repo_dir, source_dir, logger=None) -> list:
    source_dir, repo_dir = Path(source_dir), Path(repo_dir)
    synced = []
    for src_rel, dst_rel, normalize_lf in _DOCS_SYNC_FILES:
        src, dst = source_dir / src_rel, repo_dir / dst_rel
        if not src.exists():
            if logger:
                logger.warning("sync source missing, skipping: %s", src)
            continue
        content = src.read_bytes()
        if normalize_lf:
            content = content.replace(b"\r\n", b"\n")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(content)
        synced.append(dst)
        if logger:
            logger.info("synced %s -> %s%s", src, dst, " (normalized to LF)" if normalize_lf else "")
    return synced


# --- 5. Prepend changelog entry ---

_CHANGELOG_SEPARATOR = "\n\n---\n\n"
_CHANGELOG_HEADING = re.compile(r"^## \[([^\]]+)\]")


def prepend_changelog(repo_dir, changelog_entry_text, logger=None) -> Path:
    """Put the entry at the top, REPLACING any existing entry for the same version.

    Idempotent by version, not blindly prepending. Two things make that necessary now:
    PUBLISH is resumable and may re-enter this after a partial run, and it executes after
    a Gate 2 round-trip during which the release notes may have been rewritten. A blind
    prepend in either case leaves one release with two entries, the stale one on top.
    """
    changelog_path = Path(repo_dir) / "Docs" / "Changelog.md"
    existing = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else ""

    entry = changelog_entry_text.rstrip("\n")
    new_version = _CHANGELOG_HEADING.match(entry)

    # Docs/Changelog.md's own convention (confirmed against the real file): entries
    # separated by a "---" divider.
    if existing.strip():
        head, separator, tail = existing.partition(_CHANGELOG_SEPARATOR)
        head_version = _CHANGELOG_HEADING.match(head.lstrip())
        replacing = (
            separator
            and new_version
            and head_version
            and head_version.group(1) == new_version.group(1)
        )
        if replacing:
            if logger:
                logger.info("changelog already has an entry for %s, replacing it in place",
                            new_version.group(1))
            new_content = entry + _CHANGELOG_SEPARATOR + tail
        else:
            new_content = f"{entry}{_CHANGELOG_SEPARATOR}{existing.lstrip()}"
    else:
        new_content = entry + "\n"
    changelog_path.write_text(new_content, encoding="utf-8")
    if logger:
        logger.info("prepended changelog entry to %s", changelog_path)
    return changelog_path


# --- 6-7. Commit, push, tag ---

def commit_push_tag(repo_dir, version, logger=None) -> None:
    repo_dir = Path(repo_dir)
    _run_git(["add", "-A"], repo_dir, logger=logger)

    status = _run_git(["status", "--porcelain"], repo_dir, logger=logger)
    if not status.strip():
        if logger:
            logger.warning("nothing to commit in %s for %s - proceeding to tag anyway", repo_dir, version)
    else:
        _run_git(["commit", "-m", f"Release {version}"], repo_dir, logger=logger)
        _run_git(["push"], repo_dir, logger=logger)

    # Idempotent tagging. A plain `git tag <v>` fails outright when the tag exists, which
    # a resumed PUBLISH would hit every time. Move the tag only when it actually points
    # somewhere else, so the common no-op case never force-pushes anything.
    head = _run_git(["rev-parse", "HEAD"], repo_dir, logger=logger).strip()
    tagged = subprocess.run(
        ["git", "rev-list", "-n", "1", version], cwd=repo_dir, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    existing = tagged.stdout.strip() if tagged.returncode == 0 else None

    if existing == head:
        if logger:
            logger.info("tag %s already points at %s, nothing to do", version, head[:12])
        return

    if existing:
        if logger:
            logger.warning("tag %s points at %s, moving it to %s", version, existing[:12], head[:12])
        _run_git(["tag", "-f", version], repo_dir, logger=logger)
        _run_git(["push", "-f", "origin", version], repo_dir, logger=logger)
    else:
        _run_git(["tag", version], repo_dir, logger=logger)
        _run_git(["push", "origin", version], repo_dir, logger=logger)
    if logger:
        logger.info("committed, pushed, and tagged %s in %s", version, repo_dir)


# --- 8, 10. GitHub release ---

def create_draft_release(repo_slug, version, title, notes_path, artifact_paths, logger=None) -> str:
    cmd = [
        "gh", "release", "create", version,
        "--repo", repo_slug,
        "--draft",
        "--title", title,
        "--notes-file", str(notes_path),
        *[str(p) for p in artifact_paths],
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if result.returncode != 0:
        raise PublishError(f"gh release create failed: {result.stderr.strip()}")
    draft_url = result.stdout.strip()
    if logger:
        logger.info("created draft release %s: %s", version, draft_url)
    return draft_url


def publish_release(repo_slug, version, discussion_category=None, logger=None) -> None:
    """Flip the draft public, and start its release discussion in the same call.

    --discussion-category only takes effect on the draft -> published transition, which is
    exactly this call, so the discussion has to be requested here rather than at
    create_draft_release time (a draft cannot own a discussion yet).
    """
    cmd = ["gh", "release", "edit", version, "--repo", repo_slug, "--draft=false"]
    if discussion_category:
        cmd += ["--discussion-category", discussion_category]

    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    if result.returncode != 0:
        raise PublishError(f"gh release edit --draft=false failed: {result.stderr.strip()}")
    if logger:
        logger.info("published release %s", version)

    if not discussion_category:
        return

    # Report the discussion URL rather than assuming it appeared. gh exits 0 whether or not
    # the discussion was actually created (a disabled Discussions tab or a renamed category
    # both fail quietly), and a silent miss here is the kind of thing nobody notices for
    # several releases. Never fatal: the release itself is already public by this point.
    probe = subprocess.run(
        ["gh", "api", f"repos/{repo_slug}/releases/tags/{version}", "--jq", ".discussion_url"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    url = probe.stdout.strip()
    if probe.returncode == 0 and url and url != "null":
        if logger:
            logger.info("release discussion: %s", url)
    elif logger:
        logger.warning(
            "no discussion was created for %s in category %r - check that Discussions are "
            "enabled and the category name matches exactly",
            version, discussion_category,
        )


def recent_release_titles(repo_slug, limit=2, logger=None) -> list:
    result = subprocess.run(
        ["gh", "release", "list", "--repo", repo_slug, "--limit", str(limit)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if result.returncode != 0:
        if logger:
            logger.warning("gh release list failed: %s", result.stderr.strip())
        return []
    titles = []
    for line in result.stdout.splitlines():
        match = re.search(r'"([^"]*)"', line.split("\t")[0])
        if match:
            titles.append(match.group(1))
    return titles


# --- One-time cleanup sweep: em dashes, CVE bullet format, emoji spacing ---
# Idempotent by construction: every pattern below only matches the OLD shape (unbolded ID,
# dash separator, double space after emoji, bold-in-changelog-context). An already-swept
# line doesn't match and passes through unchanged, so re-running this is always safe.

_EMOJI_DOUBLE_SPACE = re.compile(r"(🔄|🛡️|✅|🚨|🌐|🏞️|💾|🚄|🐞|🪨|🗜️|💯|⛐|🤷🏽‍♂️)[ \t]{2,}")
_CVE_BULLET = re.compile(r"^-\s*(?:\[(CVE-\d{4}-\d+)\]\(([^)]+)\)|(CVE-\d{4}-\d+))\s*[—–-]\s*(.+)$")
_CHANGELOG_HEADER = re.compile(r"^## \[([^\]]+)\]\s*[—–]\s*(.+)$", re.MULTILINE)
_BOLD_SEVERITY_HEADER = re.compile(r"^\*\*(Critical|High|Moderate|Low) severity:\*\*\s*$", re.MULTILINE)


def convert_cve_bullet_to_format_a(line: str) -> str:
    """Handles both shapes seen in real historical documents: the changelog's
    already-linked-but-unbolded bullets, and the release bodies' bare-CVE-ID (no link at
    all) bullets. Any trailing text after the separator (including Tim's own editorial
    asides like "(public exploit code exists)") is preserved, just moved after the bold ID
    instead of being dash-separated - Format A has no dedicated slot for such asides, and
    dropping Tim's own commentary silently felt like the wrong call to make unilaterally.
    """
    match = _CVE_BULLET.match(line.strip())
    if not match:
        return line
    linked_id, url, bare_id, rest = match.groups()
    cve_id = linked_id or bare_id
    url = url or f"https://www.cve.org/CVERecord?id={cve_id}"
    return f"- **[{cve_id}]({url})** {rest.strip()}"


def normalize_changelog_header(text: str) -> str:
    """## [X] — date -> ## [X] (date), matching the target format from render.py and
    getting rid of the header's own em dash in one move."""
    return _CHANGELOG_HEADER.sub(r"## [\1] (\2)", text)


def normalize_emoji_spacing(text: str) -> str:
    return _EMOJI_DOUBLE_SPACE.sub(r"\1 ", text)


def unbold_severity_headers(text: str) -> str:
    return _BOLD_SEVERITY_HEADER.sub(r"\1 severity:", text)


_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_BARE_CVE = re.compile(r"CVE-(\d{4})-(\d+)(?:/(\d+))?")


def link_bare_cve_mentions(text: str) -> str:
    """Some older release bodies (pre-140.11.0) mention CVEs inline in prose instead of as
    bullets - convert_cve_bullet_to_format_a never sees these, so they'd stay unlinked.
    Also handles the "CVE-2026-6748/6751" shorthand seen in 140.10.0 (two CVEs, same year,
    slash-separated) by linking both.

    Existing markdown links are masked out first rather than guarded against with lookaround
    assertions on the CVE pattern itself, since a CVE ID legitimately appears a second time
    inside its own URL (?id=CVE-...) - trying to distinguish "in a URL" from "bare in
    parenthetical prose" (e.g. "(CVE-2026-6746)") with lookaround alone is exactly the kind
    of thing that's easy to get subtly wrong. Masking first means the bare-CVE pass never
    sees an already-linked occurrence at all, so it can't double-touch it.
    """
    protected = []

    def _mask(match):
        protected.append(match.group(0))
        return f"\x00LINK{len(protected) - 1}\x00"

    masked = _MARKDOWN_LINK.sub(_mask, text)

    def _link(match):
        year, first_num, second_num = match.groups()
        first_id = f"CVE-{year}-{first_num}"
        result = f"[{first_id}](https://www.cve.org/CVERecord?id={first_id})"
        if second_num:
            second_id = f"CVE-{year}-{second_num}"
            result += f"/[{second_id}](https://www.cve.org/CVERecord?id={second_id})"
        return result

    masked = _BARE_CVE.sub(_link, masked)

    for i, original in enumerate(protected):
        masked = masked.replace(f"\x00LINK{i}\x00", original)
    return masked


def sweep_changelog_entry(text: str) -> str:
    """Changelog target: plain (non-bold) severity headers, per Phase 6's spec."""
    text = normalize_changelog_header(text)
    lines = [convert_cve_bullet_to_format_a(line) for line in text.splitlines()]
    text = "\n".join(lines)
    text = link_bare_cve_mentions(text)
    text = common.strip_em_dashes(text)
    text = normalize_emoji_spacing(text)
    text = unbold_severity_headers(text)
    return text if text.endswith("\n") else text + "\n"


def sweep_release_body(text: str) -> str:
    """Release body target: bold severity headers (already the case in every real body
    checked) - so this is identical to the changelog sweep minus the unbolding step."""
    lines = [convert_cve_bullet_to_format_a(line) for line in text.splitlines()]
    text = "\n".join(lines)
    text = link_bare_cve_mentions(text)
    text = common.strip_em_dashes(text)
    text = normalize_emoji_spacing(text)
    return text if text.endswith("\n") else text + "\n"
