# ducksteps Build & Release Runbook

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

**Sanity check:** Installer should be ~72 MB.

| Output | Path |
|---|---|
| Installer EXE | `D:/ducksteps/ducksteps-obj/esr1XX/dist/install/sea/firefox-1XX.X.X.en-US.win64.installer.exe` |
| Standalone ZIP | `D:/ducksteps/ducksteps-obj/esr1XX/dist/firefox-1XX.X.X.en-US.win64.zip` |

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

Output filename: `ducksteps.1XX.X.X.Standalone.7z`

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
| Installer EXE | `D:/ducksteps/ducksteps-obj/esr1XX-Legacy/dist/install/sea/firefox-1XX.X.X.en-US.win64.installer.exe` |
| Standalone ZIP | `D:/ducksteps/ducksteps-obj/esr1XX-Legacy/dist/firefox-1XX.X.X.en-US.win64.zip` |

Repeat steps 11 and 12 using `ducksteps.1XX.X.X.Legacy.Setup.exe` and `ducksteps.1XX.X.X.Legacy.Standalone.7z`.

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
5. Include SHA512 hashes and VirusTotal links in release notes
6. Publish
7. Update `Changelog.md` in `/docs/`

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
- [ ] `package.sh` completed and installer is ~72 MB
- [ ] `Changelog.md` updated
- [ ] Patch stack updated and pushed to `ducksteps-docs`

---

## 📝 Notes

- **`git pull` is banned:** your branch diverges from upstream intentionally. Always rebase.
- **Detached HEAD warnings** are harmless. The rebase workflow keeps you on `esr1XX`.
- **NSIS warnings 6010, 6012, 9000** are pre-existing upstream noise. Ignore them.
- **`instrumented/`** in the objdir is the PGO training binary. Never distribute from it.
- **UPX is intentionally disabled** on the SFX stub (`exe_7z_archive.py` patch). UPX 5.x triggered Malwarebytes AI false positives at every compression level tested. The stub is ~230KB; the size savings weren't worth the VirusTotal noise. This patch is committed to the branch and survives rebases automatically.
- **PGO log location:** `D:/ducksteps/ducksteps-obj/esr1XX/instrumented/pgo_logs/profile-run-2.log`
- **LLVM Profile Errors** in the PGO log about "temporal profiles do not support merging at runtime" are expected. Not data loss; ignore them.
