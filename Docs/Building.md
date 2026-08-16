# ducksteps Build & Release Runbook

> **This is now the manual fallback.** Since 153.0 the whole process runs from the scripts in
> [`Automation/`](../Automation/): `watcher.py` spots a new ESR tag, `orchestrator.py` does
> everything from Step 5 to Step 15, and the only manual steps are two approval taps on a
> phone. See [`Automation/README.md`](../Automation/README.md).
>
> Keep this runbook current anyway. It is what you fall back on when the pipeline halts, and
> the orchestrator's phases map onto these steps one for one, so it doubles as the
> explanation of what the automation is actually doing.

**Environment:**
| | |
|---|---|
| MozillaBuild shell | `D:\ducksteps\mozilla-build\start-shell.bat` |
| Source | `D:\ducksteps\mozilla-source\ducksteps` |
| Zen5 objdir | `D:\ducksteps\ducksteps-obj\esr1XX` |
| Legacy objdir | `D:\ducksteps\ducksteps-obj\esr1XX-Legacy` |
| package.sh | `D:\ducksteps\mozilla-source\ducksteps\package.sh` |
| background.js | `D:\ducksteps\mozilla-source\ducksteps\build\pgo\pgo_training_extension\background.js` |
| Docs/Patches repo | `D:\ducksteps\ducksteps-docs` |
| Automation | `D:\ducksteps\automation` (published as [`Automation/`](../Automation/)) |

---

## 🖥️ Step 1: Open the build shell

Run `start-shell.bat` from `D:\mozilla-build`.

---

## 📂 Step 2: Navigate to source

```bash
cd /d/ducksteps/mozilla-source/ducksteps
```

---

## 🔄 Step 3: Fetch latest tags from upstream

```bash
git fetch --tags origin
```

---

## 🏷️ Step 4: Find the new release tag

```bash
git tag -l "FIREFOX_1XX*esr*RELEASE"
```

You're looking for `FIREFOX_1XX_X_XeXXX_RELEASE`. If it's not listed, upstream hasn't tagged yet: don't proceed.

---

## 🌿 Step 5: Switch to your local branch

```bash
git checkout esr1XX
```

Expected output includes `Your branch and 'origin/esr1XX' have diverged`: that's normal. Do **not** run `git pull`.

---

## 🔀 Step 6: Rebase onto the new release tag

```bash
git stash                                        # only if you have unstaged changes
git rebase FIREFOX_1XX_X_Xesr_RELEASE
git stash pop                                    # if you stashed
```

**Your patch stack** (these replay automatically; no manual re-patching needed):
- `ducksteps: branding + patchset`
- `Custom PGO training: replace Mozilla default workload with realistic browsing corpus`
- `ducksteps: WebExtension PGO training + profileserver patches`
- `ducksteps: remove UPX from SFX stub (VT false positive fix)`

> ⚠️ **Version file conflict:** If git pauses on `browser/config/version.txt`, `version_display.txt`, or `config/milestone.txt`: upstream owns those files. Run:
> ```bash
> git rebase --skip
> ```
> Do **not** manually resolve. Upstream's version is correct by definition.

---

## ✅ Step 7: Verify the version

```bash
cat browser/config/version.txt
cat browser/config/version_display.txt
```

Expected: `1XX.X.X` and `1XX.X.Xesr`. If either shows the old version, the rebase didn't land correctly: stop.

---

## 🧹 Step 8: Clobber

```bash
./mach clobber
```

---

## 🔨 Step 9: Build

```bash
./mach build
```

The PGO flow runs automatically:
1. Instrumented build compiles
2. Firefox launches and runs the 88-site training corpus (133.6 min measured); do not interrupt
3. Optimized build compiles using profile data

`profile-run-1.log` stopping after site 1 of 88 is expected: that's Mozilla's stock
profile-initialization pass, not a hang or a failure. The real training run is
`profile-run-2.log`, which covers all 88 sites.

Done when you see `your build finally finished successfully!`

Verify it launches:
```bash
./mach run
```

> **Never distribute from `instrumented/`**: that's the PGO training binary.

---

## 📦 Step 10: Package

```bash
./package.sh /d/ducksteps/ducksteps-obj/esr1XX
```

The objdir argument is required; `package.sh` exits immediately if it's missing or doesn't
exist, rather than silently falling back to a default tree. The installer icon comes from the
ducksteps-branded `setup.ico` that NSIS compiles into the stub at build time via the branding
patch; no separate icon-stamping step is needed.

**Sanity check:** Installer should be ~85 MB on ESR 153 (it was ~72 MB on ESR 140).

| Output | Path |
|---|---|
| Installer EXE | `D:/ducksteps/ducksteps-obj/esr1XX/dist/firefox-1XX.X.X.en-US.win64.installer.exe` |
| Standalone ZIP | `D:/ducksteps/ducksteps-obj/esr1XX/dist/firefox-1XX.X.X.en-US.win64.zip` |

> **The installer moved in ESR 153.** It used to land in `dist/install/sea/`. Upstream changed
> `INSTALLER_PACKAGE` in `toolkit/mozapps/installer/upload-files.mk` from `$(PKG_INST_PATH)` to
> `$(PKG_PATH)`, which is empty for en-US builds, so it is now written directly to `dist/`.
> If you are building an older line, look in `dist/install/sea/` instead.

---

## 7️⃣ Step 11: Repack standalone as 7z

Convert the ZIP to 7z with these exact settings:
- **Format:** 7z
- **Compression level:** 9 (Ultra)
- **Method:** LZMA2
- **Dictionary size:** 384 MB
- **Word size:** 273
- **Solid block:** yes
- **Threads:** 3

Output filename: `ducksteps.1XX.X.X.AVX512.Standalone.7z`

The installer is renamed to match: `ducksteps.1XX.X.X.AVX512.Setup.exe`.

> **Naming changed in 153.0.** The Zen5 artifacts used to have no infix at all
> (`ducksteps.1XX.X.X.Setup.exe`). GitHub sorts the Assets box on a release **alphabetically
> by filename**, with no way to reorder it: there is no position field on the API, and upload
> order is ignored. With no infix, `...Legacy.Setup.exe` sorted above `...Setup.exe` and the
> AVX2 build sat on top of the AVX-512 one. `AVX512` sorts before `Legacy`, so the primary
> build now leads. Do not drop the infix, and do not rename either build to anything that
> sorts after `Legacy`.

---

## #️⃣ Step 12: Checksum and virus scan all release files

Right click each file, highlight 7-Zip, highlight CRC SHA, click SHA-512, double click SHA512 result, double click SHA512 text, right click and copy/paste it to Release Notes.

Submit all files to [VirusTotal](https://www.virustotal.com). Save the result URLs: they go in the release notes.

Expected: zero flags. If you see flags on any files, investigate.

---

## 💻 Step 13: Build and Package Legacy Variant

Switch to the Legacy mozconfig and rebuild from scratch:

```bash
export MOZCONFIG=/d/ducksteps/mozilla-source/ducksteps/.mozconfig-Legacy
./mach clobber
./mach build
./mach run
./package.sh /d/ducksteps/ducksteps-obj/esr1XX-Legacy
```


| Output | Path |
|---|---|
| Installer EXE | `D:/ducksteps/ducksteps-obj/esr1XX-Legacy/dist/firefox-1XX.X.X.en-US.win64.installer.exe` |
| Standalone ZIP | `D:/ducksteps/ducksteps-obj/esr1XX-Legacy/dist/firefox-1XX.X.X.en-US.win64.zip` |

Repeat steps 11 and 12 using `ducksteps.1XX.X.X.Legacy.Setup.exe` and `ducksteps.1XX.X.X.Legacy.Standalone.7z`.

> **Check you packaged the right objdir.** `mach package` takes its objdir from `MOZCONFIG`,
> not from the argument you pass `package.sh` (that argument is only used to find the finished
> installer). If you forget the `export MOZCONFIG=...` line above, it repackages the Zen5 tree
> and you ship Zen5 binaries labelled Legacy. Nothing downstream catches it: the two differ
> only in `-march`, so size, smoke test, VirusTotal and the hashes all look perfectly normal.
> Confirm the `Created package:` line in the output names the `-Legacy` objdir.

To switch back to Zen5:
```bash
export MOZCONFIG=/d/ducksteps/mozilla-source/ducksteps/.mozconfig
```

---

## 🚀 Step 14: Publish on GitHub

1. Repo → **Releases** → **Draft a new release**
2. **Choose a tag** → type the new version (e.g. `140.10.2`) → **Create new tag on publish**
3. Title follows release name style (e.g. `⛐ It's the "..." release:`)
4. Attach all files
5. Include SHA512 hashes and VirusTotal links in release notes, AVX512 build first
6. Publish, and start a discussion in **Announcements** while doing so
7. Update `Changelog.md` in `/docs/`

Notes on this step:

- **Do not repeat the release title inside the body.** GitHub already renders the release name
  above it, so it appears twice.
- **The Assets box order is fixed by filename, not by upload order.** See Step 11.
- **The discussion can only be started as the draft is published.** A draft cannot own one.
  On the API that is `--discussion-category "Announcements"` on the publish call, and it fails
  silently if the category name does not match exactly.
- **Update the changelog last,** once the notes are final. Writing it before the notes are
  agreed leaves it quoting text you then edit.

---

## 📤 Step 15: Update the patch stack

Export your commits as patches and push them. There is no separate docs repo: `D:/ducksteps/ducksteps-docs` is just a local clone of the same `github.com/SyntaxError-PEBKAC/ducksteps` project, checked out at a convenient path, and this is where the published patch stack (and your off-machine backup) lives:

```bash
cd D:/ducksteps/ducksteps-docs
git pull
rm Patches/000*.patch Patches/001*.patch
git -C D:/ducksteps/mozilla-source/ducksteps format-patch --binary -o Patches FIREFOX_1XX_X_Xesr_RELEASE..HEAD
git add Patches/
git commit -m "Update patch stack for 1XX.X.X"
git push
```

`Patches/000*.patch Patches/001*.patch` covers patches 0001 through 0019; add a third pattern if
the stack ever grows past that. `FIREFOX_1XX_X_Xesr_RELEASE` is the same tag you rebased onto in
Step 6: since your patch stack sits directly on top of it after every rebase, it's always the
correct range start. No need to track a base commit hash by hand.

---

## ☑️ Release Checklist

- [ ] Build completed without fatal errors
- [ ] `./mach run` launches with correct ducksteps branding (no Nightly purple)
- [ ] `package.sh` completed and installer is ~85 MB
- [ ] Legacy packaged from the `-Legacy` objdir, not the Zen5 one (check `Created package:`)
- [ ] Artifacts named `.AVX512.` and `.Legacy.`, AVX512 listed first everywhere
- [ ] `Changelog.md` updated, and the entry sits below the `# Changelog` header
- [ ] Patch stack updated and pushed to `ducksteps-docs`
- [ ] `Automation/` synced if any script changed

---

## 📝 Notes

- **`git pull` is banned:** your branch diverges from upstream intentionally. Always rebase.
- **Detached HEAD warnings** are harmless. The rebase workflow keeps you on `esr1XX`.
- **NSIS warnings 6010, 6012, 9000** are pre-existing upstream noise. Ignore them.
- **`instrumented/`** in the objdir is the PGO training binary. Never distribute from it.
- **UPX is intentionally disabled** on the SFX stub (`exe_7z_archive.py` patch). UPX 5.x triggered Malwarebytes AI false positives at every compression level tested. The stub is ~230KB; the size savings weren't worth the VirusTotal noise. This patch is committed to the branch and survives rebases automatically.
- **`bash` is not MozillaBuild's bash** when a Windows program launches it by bare name. Windows searches `System32` before `PATH`, and `C:\Windows\System32\bash.exe` is the WSL launcher, which mounts drives at `/mnt/d` and cannot see `D:\...` at all. Call `D:\ducksteps\mozilla-build\msys2\usr\bin\bash.exe` by full path from any script. `shutil.which("bash")` reports the right one and is therefore no help in spotting this.
- **`-vendor-short-name` means Mozilla, not the maintainer.** Firefox uses it for whoever receives telemetry and vets extensions, and ducksteps changes neither. It was briefly set to `SyntaxError-PEBKAC`, which made the browser tell users on first run that it was sending their data to a named individual. The About dialog credits the maintainer with a literal string instead.
- **PGO log location:** `D:/ducksteps/ducksteps-obj/esr1XX/instrumented/pgo_logs/profile-run-2.log`
- **LLVM Profile Errors** in the PGO log about "temporal profiles do not support merging at runtime" are expected. Not data loss; ignore them.
