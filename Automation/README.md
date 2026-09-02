# ducksteps release automation

The scripts that build and publish ducksteps. Kept here so the pipeline that produced a
release is readable alongside the release itself. Synced automatically on every publish,
so what is in this directory is what built the newest release.

| | |
|---|---|
| `watcher.py` | Polls Mozilla's product-details for a new ESR tag and decides whether there is anything to build. Runs twice daily and never touches the source tree. |
| `orchestrator.py` | The build pipeline. 23 phases, resumable from the last completed one. |
| `advisory.py` | Resolves the MFSA and CVE list from Mozilla's published advisory data. Never guesses: if the sources disagree or cannot be reached, it halts. |
| `render.py` | Drafts the release notes and changelog entry. A first draft: the notes are expected to be edited before they ship. |
| `publish.py` | Syncs this repo, creates the GitHub release, reads the edited draft back, and applies the house formatting rules. |
| `vt.py` | VirusTotal submission, verdict classification, and the repackaging ladder used when something is flagged. |
| `notify.py` | Push notifications and the approval gates. |
| `common.py` | Config, state, locking, and shared text rules. |
| `setup_scheduler.ps1` | Registers the two Windows Task Scheduler tasks. |
| `SCHEDULER.md` | Read this before the first build. Explains why the session must stay unlocked. |

## How a release happens

1. `watcher.py` sees a new ESR tag upstream and sends a notification.
2. Approving it starts `orchestrator.py`, which rebases the patch stack, builds both
   variants with PGO and full LTO, smoke-tests each one, packages them, and submits all
   four artifacts to VirusTotal.
3. It resolves the CVE list, drafts the release notes, and creates a draft release.
4. The draft gets edited by hand, on GitHub, in whatever way it needs.
5. Approving that publishes the release, updates this repo, and opens a discussion.

Two approvals, both answerable from a phone. Everything between them is unattended.

Step 4 is a normal part of the process rather than an escape hatch. Generated notes are a
starting point, and the ones that end up published are usually not the ones that were
generated. So the draft, not the generated text, is what the pipeline treats as real: on
approval it re-reads the release from GitHub and derives the `Docs/Changelog.md` entry from
whatever the body says at that moment. The release page, the changelog and the release
commit therefore cannot drift apart, however heavily the draft was rewritten. The approval
notification carries a "still editing" button for the same reason - the build finishes when
it finishes, which is not necessarily when anyone is awake to proofread it.

## What is not here

`.env` and `state.json` are deliberately excluded. `.env` holds the notification topics,
which are in practice the password for the approval buttons, and `state.json` holds local
build state. Anyone running these scripts needs to supply their own `.env` and adjust the
paths at the top of `config.toml`.
