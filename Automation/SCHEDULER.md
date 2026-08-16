# Task Scheduler setup

## Read this before the first real build

**The console session must stay unlocked for the entire build.** Sleep and hibernate
must be disabled for the duration; screen-off (monitor sleep) is fine, that doesn't
affect this.

**Why:** Session 0 and locked sessions drop hardware compositing. PGO training drives a
real Firefox window through 88 sites for ~134 minutes to record which code paths
actually run under WebRender and the GPU compositor. Without real compositing, that
window either doesn't render normally or renders through a software fallback path, so
the profile gets recorded, the build finishes, everything *looks* fine, and the
resulting binary is measurably worse in exactly the paths PGO was supposed to optimize.
There's no error, no warning, nothing in the log: the only symptom is a binary that's
quietly worse than it should be. This is exactly why Invariant 2 (never Session 0) and
the orchestrator task's "run only when logged on" setting exist.

In practice: don't lock your session, don't let Windows sleep, and don't RDP into this
machine to run a build (RDP sessions used to force the same GPU-less compositing path
as Session 0; if you ever need remote access during a build, confirm your Windows
build's RDP client actually gives you hardware acceleration before trusting the result).

---

## What gets registered

Running `setup_scheduler.ps1` creates two Task Scheduler tasks:

| Task | Trigger | Runs whether logged on or not? |
|---|---|---|
| `ducksteps watcher` | Daily, 9:00 AM and 5:00 PM | Yes |
| `ducksteps orchestrator` | None (manual start only) | No, requires an interactive logon |

**`ducksteps watcher`** polls Mozilla, decides if there's something new to build, and
sends the Gate 1 notification if so. It runs in a few seconds and never touches the
source tree beyond a read-only `git ls-remote`. Safe to run unattended, which is why it
can run whether you're logged on or not.

**`ducksteps orchestrator`** runs the actual 10-hour build pipeline. It has **no
automatic trigger on purpose** - start it yourself once you've approved a release from
your phone:

- Task Scheduler UI: right-click "ducksteps orchestrator" -> Run
- Or from an elevated or regular prompt: `schtasks /run /tn "ducksteps orchestrator"`

If a build gets interrupted (reboot, crash, you closed it), don't re-run the task as-is:
open `start-shell.bat` yourself and run `python orchestrator.py --resume` directly. The
registered task always does a fresh start, which correctly refuses to clobber an
in-progress build and will just tell you to use `--resume` instead - resuming from a
random restart isn't a case worth a second scheduled task for.

## Running the setup script

```powershell
D:\ducksteps\automation\setup_scheduler.ps1
```

**Run this from an elevated (Run as Administrator) PowerShell prompt.** The watcher
task's logon type (S4U: runs whether logged on or not, without storing your Windows
password anywhere) requires elevation to register. Without it, registration fails
partway through with "Access is denied" - confirmed directly, not assumed, while
building this.

Safe to re-run any time (e.g. after moving the automation directory, or changing your
Python install path at the top of the script): it re-registers both tasks in place
rather than erroring on "task already exists."

## Checking on things

```powershell
Get-ScheduledTask -TaskName "ducksteps*"
Get-ScheduledTaskInfo -TaskName "ducksteps watcher"
Get-ScheduledTaskInfo -TaskName "ducksteps orchestrator"
```

`logs/` in the automation directory has the real record of what each run actually did;
Task Scheduler's own "Last Run Result" only tells you the process exit code.

## Removing everything

```powershell
Unregister-ScheduledTask -TaskName "ducksteps watcher" -Confirm:$false
Unregister-ScheduledTask -TaskName "ducksteps orchestrator" -Confirm:$false
```
