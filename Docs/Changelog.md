# Changelog

All releases of ducksteps. Newest first.

---

## [140.13.0] — 21/July/2026

⛐ It's the "exploit code's already out there" release!

🔄 Updated to Firefox ESR 140.13.0. Pure upstream sync — no ducksteps-side changes this round.

🛡️ Addressed 32 CVEs from Mozilla Foundation Security Advisory 2026-70 (July 21, 2026). Two critical this cycle — a WebAssembly invalid pointer and a DOM Navigation site isolation bypass — both with public exploit code, though Mozilla reports no confirmed in-the-wild attacks yet. Also 16 high-severity patches (three sandbox escapes, two JIT miscompilations, four WebAssembly-related bugs), 13 moderate, 1 low. Heaviest cycle since 140.12.0's 29.

Critical severity:

- [CVE-2026-15718](https://www.cve.org/CVERecord?id=CVE-2026-15718) — invalid pointer in the JavaScript: WebAssembly component (public exploit code exists)
- [CVE-2026-15719](https://www.cve.org/CVERecord?id=CVE-2026-15719) — site isolation issue in the DOM: Navigation component (public exploit code exists)

High severity:

- [CVE-2026-16349](https://www.cve.org/CVERecord?id=CVE-2026-16349) — same-origin policy bypass in the DOM: Navigation component
- [CVE-2026-16350](https://www.cve.org/CVERecord?id=CVE-2026-16350) — incorrect boundary conditions in the Audio/Video: cubeb component
- [CVE-2026-16351](https://www.cve.org/CVERecord?id=CVE-2026-16351) — sandbox escape via use-after-free in the DOM: Navigation component
- [CVE-2026-16352](https://www.cve.org/CVERecord?id=CVE-2026-16352) — sandbox escape via use-after-free in the Disability Access APIs component
- [CVE-2026-16353](https://www.cve.org/CVERecord?id=CVE-2026-16353) — invalid pointer in the DOM: Bindings (WebIDL) component
- [CVE-2026-16354](https://www.cve.org/CVERecord?id=CVE-2026-16354) — information disclosure in the Graphics: ImageLib component
- [CVE-2026-16355](https://www.cve.org/CVERecord?id=CVE-2026-16355) — JIT miscompilation in the JavaScript Engine: JIT component
- [CVE-2026-16356](https://www.cve.org/CVERecord?id=CVE-2026-16356) — sandbox escape via use-after-free in the Disability Access APIs component (second instance)
- [CVE-2026-16357](https://www.cve.org/CVERecord?id=CVE-2026-16357) — incorrect boundary conditions in the Graphics component
- [CVE-2026-16360](https://www.cve.org/CVERecord?id=CVE-2026-16360) — memory safety bugs shared across ESR 115.38, ESR 140.13, and Firefox 153
- [CVE-2026-16361](https://www.cve.org/CVERecord?id=CVE-2026-16361) — memory safety bugs shared across ESR 115.38 and ESR 140.13
- [CVE-2026-16362](https://www.cve.org/CVERecord?id=CVE-2026-16362) — use-after-free in the WebRTC: Audio/Video component
- [CVE-2026-16363](https://www.cve.org/CVERecord?id=CVE-2026-16363) — JIT miscompilation in the JavaScript: WebAssembly component
- [CVE-2026-16368](https://www.cve.org/CVERecord?id=CVE-2026-16368) — incorrect boundary conditions in the JavaScript: WebAssembly component
- [CVE-2026-16369](https://www.cve.org/CVERecord?id=CVE-2026-16369) — integer overflow in the JavaScript: WebAssembly component
- [CVE-2026-16412](https://www.cve.org/CVERecord?id=CVE-2026-16412) — memory safety bugs shared across ESR 140.13 and Firefox 153

Moderate severity:

- [CVE-2026-16358](https://www.cve.org/CVERecord?id=CVE-2026-16358) — site isolation issue in the Graphics: WebRender component
- [CVE-2026-16359](https://www.cve.org/CVERecord?id=CVE-2026-16359) — incorrect boundary conditions in the Audio/Video: GMP component
- [CVE-2026-16371](https://www.cve.org/CVERecord?id=CVE-2026-16371) — privilege escalation in the DOM: Navigation component
- [CVE-2026-16374](https://www.cve.org/CVERecord?id=CVE-2026-16374) — information disclosure in the DevTools: Framework component
- [CVE-2026-16375](https://www.cve.org/CVERecord?id=CVE-2026-16375) — site isolation issue in the Networking: HTTP component
- [CVE-2026-16377](https://www.cve.org/CVERecord?id=CVE-2026-16377) — mitigation bypass in the PDF Viewer component
- [CVE-2026-16379](https://www.cve.org/CVERecord?id=CVE-2026-16379) — privilege escalation in the DOM: Content Processes component
- [CVE-2026-16381](https://www.cve.org/CVERecord?id=CVE-2026-16381) — same-origin policy bypass in the Networking: DNS component
- [CVE-2026-16383](https://www.cve.org/CVERecord?id=CVE-2026-16383) — mitigation bypass in the DOM: Networking component
- [CVE-2026-16387](https://www.cve.org/CVERecord?id=CVE-2026-16387) — site isolation issue in the Networking component
- [CVE-2026-16390](https://www.cve.org/CVERecord?id=CVE-2026-16390) — mitigation bypass in the Enterprise Policies component
- [CVE-2026-16391](https://www.cve.org/CVERecord?id=CVE-2026-16391) — information disclosure in the Storage: IndexedDB component
- [CVE-2026-16396](https://www.cve.org/CVERecord?id=CVE-2026-16396) — privilege escalation in WebExtensions

Low severity:

- [CVE-2026-16405](https://www.cve.org/CVERecord?id=CVE-2026-16405) — information disclosure in the Networking: WebSockets component

---

## [140.12.0] — 17/June/2026

⛐ It's the "twenty-nine CVEs but who's counting" release!

🔄  Updated to Firefox ESR 140.12.0.

🛡️  Addressed 29 CVEs from Mozilla Foundation Security Advisory 2026-58 (June 16, 2026). No critical severity, no active exploitation reported — though this is the heaviest patch cycle in the 140.x series so far: 12 high-severity patches including four separate sandbox escapes and a JIT miscompilation, 15 moderate, 2 low.

**High severity:**

- [CVE-2026-12289](https://www.cve.org/CVERecord?id=CVE-2026-12289) — privilege escalation in the Graphics: WebRender component
- [CVE-2026-12290](https://www.cve.org/CVERecord?id=CVE-2026-12290) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12291](https://www.cve.org/CVERecord?id=CVE-2026-12291) — use-after-free in the Networking: HTTP component
- [CVE-2026-12292](https://www.cve.org/CVERecord?id=CVE-2026-12292) — incorrect boundary conditions in the Web Audio component
- [CVE-2026-12294](https://www.cve.org/CVERecord?id=CVE-2026-12294) — sandbox escape in the DOM: Workers component
- [CVE-2026-12295](https://www.cve.org/CVERecord?id=CVE-2026-12295) — sandbox escape in the DOM: Navigation component
- [CVE-2026-12296](https://www.cve.org/CVERecord?id=CVE-2026-12296) — sandbox escape in the Security: Process Sandboxing component
- [CVE-2026-12297](https://www.cve.org/CVERecord?id=CVE-2026-12297) — sandbox escape via incorrect boundary conditions in the Networking component
- [CVE-2026-12298](https://www.cve.org/CVERecord?id=CVE-2026-12298) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12299](https://www.cve.org/CVERecord?id=CVE-2026-12299) — JIT miscompilation in the DOM: Core & HTML component
- [CVE-2026-12328](https://www.cve.org/CVERecord?id=CVE-2026-12328) — memory safety bugs shared across ESR 115.37, ESR 140.12, and Firefox 152 (evidence of memory corruption, plausible RCE potential)
- [CVE-2026-12329](https://www.cve.org/CVERecord?id=CVE-2026-12329) — memory safety bug in Firefox ESR 140.12

**Moderate severity:**

- [CVE-2026-12302](https://www.cve.org/CVERecord?id=CVE-2026-12302) — mitigation bypass in the DOM: Security component
- [CVE-2026-12304](https://www.cve.org/CVERecord?id=CVE-2026-12304) — same-origin policy bypass in the Networking: Cookies component
- [CVE-2026-12305](https://www.cve.org/CVERecord?id=CVE-2026-12305) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12306](https://www.cve.org/CVERecord?id=CVE-2026-12306) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12307](https://www.cve.org/CVERecord?id=CVE-2026-12307) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12308](https://www.cve.org/CVERecord?id=CVE-2026-12308) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12309](https://www.cve.org/CVERecord?id=CVE-2026-12309) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12310](https://www.cve.org/CVERecord?id=CVE-2026-12310) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12311](https://www.cve.org/CVERecord?id=CVE-2026-12311) — information disclosure + sandbox escape in the Security: Process Sandboxing component
- [CVE-2026-12312](https://www.cve.org/CVERecord?id=CVE-2026-12312) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12313](https://www.cve.org/CVERecord?id=CVE-2026-12313) — information disclosure + sandbox escape in the Security: Process Sandboxing component
- [CVE-2026-12314](https://www.cve.org/CVERecord?id=CVE-2026-12314) — memory safety bug in Firefox ESR 140.12
- [CVE-2026-12315](https://www.cve.org/CVERecord?id=CVE-2026-12315) — mitigation bypass in the DOM: Security component
- [CVE-2026-12327](https://www.cve.org/CVERecord?id=CVE-2026-12327) — memory safety bugs shared across ESR 140.12 and Firefox 152 (evidence of memory corruption, plausible RCE potential)
- [CVE-2026-12330](https://www.cve.org/CVERecord?id=CVE-2026-12330) — incorrect boundary conditions in the Internationalization component

**Low severity:**

- [CVE-2026-12324](https://www.cve.org/CVERecord?id=CVE-2026-12324) — incorrect boundary conditions in the Graphics: CanvasWebGL component
- [CVE-2026-12325](https://www.cve.org/CVERecord?id=CVE-2026-12325) — denial-of-service in the Graphics: ImageLib component

---

## [140.11.0] — 19/May/2026

⛐ It's the "stay in the sandbox" release! 

🔄 Updated to Firefox ESR 140.11.0.

🛡️ Addressed 15 CVEs from Mozilla Foundation Security Advisory 2026-48 (May 19, 2026). No critical issues, no active exploitation reported.

High severity:

- [CVE-2026-8401](https://www.cve.org/CVERecord?id=CVE-2026-8401) — sandbox escape via the Profile Backup component
- [CVE-2026-8947](https://www.cve.org/CVERecord?id=CVE-2026-8947) — use-after-free in WebIDL bindings
- [CVE-2026-8388](https://www.cve.org/CVERecord?id=CVE-2026-8388) — out-of-bounds read in the JIT compiler
- [CVE-2026-8391](https://www.cve.org/CVERecord?id=CVE-2026-8391) — issue in the JavaScript engine
- [CVE-2026-8946](https://www.cve.org/CVERecord?id=CVE-2026-8946) — out-of-bounds read in Web Codecs

Moderate severity:

- [CVE-2026-8953](https://www.cve.org/CVERecord?id=CVE-2026-8953) — sandbox escape via use-after-free in Accessibility APIs
- [CVE-2026-8958](https://www.cve.org/CVERecord?id=CVE-2026-8958) — info disclosure + sandbox escape in process sandboxing
- [CVE-2026-8959](https://www.cve.org/CVERecord?id=CVE-2026-8959) — sandbox escape via out-of-bounds read in Win32 widgets
- [CVE-2026-8950](https://www.cve.org/CVERecord?id=CVE-2026-8950) — same-origin policy bypass in HTTP networking
- [CVE-2026-8949](https://www.cve.org/CVERecord?id=CVE-2026-8949) — integer overflow in Win32 widgets
- [CVE-2026-8956](https://www.cve.org/CVERecord?id=CVE-2026-8956) — integer overflow in JAR networking
- [CVE-2026-8955](https://www.cve.org/CVERecord?id=CVE-2026-8955) — privilege escalation in DOM Workers
- [CVE-2026-8957](https://www.cve.org/CVERecord?id=CVE-2026-8957) — privilege escalation in Enterprise Policies
- [CVE-2026-8954](https://www.cve.org/CVERecord?id=CVE-2026-8954) — out-of-bounds read in audio/video processing

Low severity:

- [CVE-2026-8961](https://www.cve.org/CVERecord?id=CVE-2026-8961) — spoofing issue in Form Autofill

---

## [140.10.2] — 10/May/2026

⛐ It's the "patch Tuesday came early" release!

🔄 Updated to Firefox ESR 140.10.2.

🛡️ Addressed three high-severity CVEs from Mozilla Foundation Security Advisory 2026-41 (May 7, 2026): CVE-2026-8090 (use-after-free in the DOM/networking component), CVE-2026-8094 (issue in the WebRTC component), and CVE-2026-8092 (memory safety bugs with plausible RCE potential, shared across ESR 115.35.2, 140.10.2, and Firefox 150.0.2). Nothing critical this cycle — no sandbox escapes, no active exploitation reported — but the memory safety batch alone is reason enough to ship.

🧠 This is the 8th PGO training refinement. Three iterations this release focused on automating the corpus run end-to-end. Turns out auto-fullscreen on video sites is genuinely cursed... ad timing is inconsistent enough across YouTube, Twitch, and DailyMotion that any reliable automation would need per-site ad-skip logic and timing jitter I don't want to maintain. Fullscreen clicks are manual for now, which is fine; the duck doesn't care who clicked the button, only that the video codec paths got exercised.

---

## [140.10.1] — 29/April/2026

⛐ It's the "memory corruption and really long build days" release:

🔄 Updated to Firefox ESR 140.10.1.

🛡️ Addressed CVE-2026-7321 (WebRTC sandbox escape, CVSS 9.6 — the one that actually prompted the point release), CVE-2026-7322 (memory safety bugs with plausible RCE potential across ESR 115/140 and Firefox 150), and CVE-2026-7323 (additional memory safety bugs in ESR 140.10.0 and Firefox 150). Mozilla Foundation Security Advisory 2026-36. The WebRTC one had "critical" written all over it — good patch cycle to stay current on.

🧠 This is the 5th build using the custom PGO training infrastructure. The extension now drives 87 sites through realistic scroll patterns, video playback, SPA hydration, map interactions, and speed tests before handing off to a clean shutdown. Each training run clocks in around 121 minutes. Each full build is around 190 minutes. The duck is very well trained at this point.

🗜️ Retired UPX compression on the installer stub entirely. UPX 5.x triggered Malwarebytes AI false positives at every compression level tested — including -1. Not worth the 66KB. Zero VirusTotal flags on both files this release.

🔧 Committed the custom PGO and UPX patches to the branch so they survive rebases automatically. Future releases won't require the manual patch dance that this one did.

---

## [140.10.0] — 21/April/2026

⛐ It's the "the duck went to the gym" release:

🔄 Updated to Firefox ESR 140.10.0. Picked up today's upstream security patch.

🛡️ Patched 13 high-severity CVEs from MFSA 2026-32 (April 21, 2026). Highlights: use-after-free in the DOM (CVE-2026-6746), use-after-free in WebRTC (CVE-2026-6747), uninitialized memory in Web Codecs (CVE-2026-6748/6751), privilege escalation in WebRender (CVE-2026-6750), use-after-free in the JS engine (CVE-2026-6754), and a broad set of memory safety bugs with plausible RCE potential (CVE-2026-6785/6786). Full advisory: https://www.mozilla.org/en-US/security/advisories/mfsa2026-32/

🧠 Rebuilt the PGO training infrastructure from scratch as a proper WebExtension. The extension drives all 87 sites autonomously through scroll behaviors, video playback, SPA hydration, map panning, and speed tests, then navigates to a localhost-served shutdown page that calls Quitter.quit() for a clean profraw flush. This is the 5th refinement build using custom training, with improved tunings after each run.

🦾 Added RUSTFLAGS="-C target-cpu=znver5 -C opt-level=3" (Zen 5) and "-C target-cpu=haswell -C opt-level=3" (Legacy). The Rust side of the build was previously compiling to a generic target — it's now CPU-tuned to match the C/C++ flags.

🖳 Switched the Legacy build to -march=x86-64-v3 -mtune=generic. Covers Intel Haswell (2013) and later, and most AMD chips from Excavator (2015) onward. The generic tune keeps it fast across both vendors.

🔧 Patched profileserver.py with a 3-hour watchdog thread (safety net if a training site hangs), a @response_file workaround for Windows' 32K command-line limit when llvm-profdata merge chokes on hundreds of profraw filenames, and a Speedometer 3 HTTP server on port 8000 alongside the existing port 8888 server.

🚫 Disabled the updater, maintenance service, default-browser-agent, and crashreporter at compile time. None of them are used, and they were just sitting there consuming memory and storage for no reason.

🧪 Tested --enable-optimize="-O3" and --enable-optimize="-O3 /Gy". Both caused lld-link duplicate symbol errors in mozglue during the PGO instrumented phase — -O3 as a bare flag replaces Mozilla's default flag expansion in a way that breaks jemalloc operator handling. Reverted to bare --enable-optimize. Documented here so I remember not to try this again.

🗜️ Upgraded UPX from 3.95w (2018) to 5.1.1 (2026). No meaningful size change, but years of fixes baked in. Turns out 5.x's defaults (--best --lzma --ultra-brute) are spicy enough to turn two VirusTotal flags into six, so I patched exe_7z_archive.py to dial it back to -6 with no algorithm flags. That added 1-2MB more total filesize, but there are no more false positives from VirusTotal.

⏱️ Fun facts: each PGO run alone takes ~112 minutes, and a complete build now clocks in at ~190 minutes. (pls send RAM & caffeine)

🤖 Fun fact # 2 (3?): I spent a painful number of Claude Opus 4.6 credits on this release, and Anthropic waited until I was basically done to drop Opus 4.7 — which uses over a third fewer tokens per task. I'm not saying the timing was personal. I'm just saying the timing was personal.

---

## [140.9.1] — 09/April/2026

⛐ It's the "security patch, everyone's welcome!" release:

🔄  Updated to Firefox ESR 140.9.1. Just Mozilla patching things that needed patching.

🍾 First Skylake and newer release! Download the Legacy version if you don't have a AMD Zen 5 CPU. This build is compiled with:
-march=skylake -mtune=skylake
It requires a CPU with AVX2, BMI1, BMI2, FMA, LZCNT, MOVBE, and POPCNT support.
In practice that covers most Intel chips from Broadwell (2014) onward and most AMD chips from Excavator (2015) onward.

🛡️  Addressed three high-severity CVEs from Mozilla Foundation Security Advisory 2026-27 (April 7, 2026): CVE-2026-5732 (integer overflow in text rendering), CVE-2026-5731 (memory safety bugs shared across ESR 115.34.0/140.9.0/Firefox 149.0.1), and CVE-2026-5734 (memory safety bugs in ESR 140.9.0/Firefox 149.0.1). Two of the three showed evidence of memory corruption with plausible RCE potential.

🚨  VirusTotal: two flags (Arctic Wolf, Jiangmin) on Setup.exe — same compression heuristic suspects as always. Standalone clean.

---

## [140.9.0] — 25/March/2026

⛐ It's the "homework turned in on time" release:

🔄  Updated to Firefox ESR 140.9.0 release build (stable over latest-available).

🎂  Synchronized release date with Mozilla's ESR cadence — now shipping same-day as upstream ESR.

🛡️  AV false positive heads-up: compression flags (higher compression + file breakup) trigger suspicious-file detections on some scanners. Passed local Windows AV. VirusTotal: one flag (Jiangmin).

👩🏼‍🏫  Noted: custom PGO training scripts are coming. The duck will waddle faster. (coming soon™️)

---

## [140.8.0_PGO] — 14/February/2026

⛐ It's the "my bad, PGO was off!" release:

🔄  Updated to latest upstream ESR 140.x files.

🧠  Rebuilt with PGO correctly enabled — previous build had the flag silently missing.

🧹  Removed ccache — conflicts with PGO builds; user performance wins over compile time.

🗜️  Compressed Setup.exe further with additional UPX flags (`--best`, `--lzma`, `--ultra-brute`).

🛡️  AV heads-up: aggressive compression triggers scanner heuristics. Passed local Bitdefender. VirusTotal: two flags (Arctic Wolf, Jiangmin).

---

## [140.8.0] — 31/January/2026

⛐ It's the "I DID A THING!" release:

🌐  Renamed Nightly to Ryfox.

😐  Renamed Ryfox to ducksteps in accordance with Mozilla naming recommendations.

🏞️  Created an icon set via ChatGPT and implemented it in installer and browser. Not an artist — just wanted something welcoming and scalable. Proper iconography is a future problem.

💾  Moved working directories to ReFS storage for faster builds from source.

🚄  Configured ccache for faster compiling.

🐞  Patched numerous minor compilation bugs.

🪨  Swapped codebase from Nightly to ESR (major updates every 6–12 months, monthly security/bugfix cadence). More stable, easier to keep on a normal release schedule.

🗜️  Compressed standalone 7z as much as possible. (Level 9 Ultra, LZMA2, 3840 MB dict, 273 word size, solid block, 3 threads)

🤷🏽‍♂️  Unable to compress Setup.exe further — the two files ended up within 2.65 MB of each other.

💯  Version numbering now matches compiled Firefox version going forward.

---

## [v1.0.0] — 09/December/2025

Initial alpha release. Shipped as "Ryfox 1.0.0."

🦊  Built on Firefox Nightly 142.0a1 (2025-12-08).

🧰  Toolchain: VS 2022 Build Tools 17.14.36717.8, Rustup 1.28.2, Python 3.14.2, Chocolatey 2.6.0, ccache 4.12.2.

Benchmarks (9950X3D / RTX 4080 Super / 48GB DDR5 / 1080p 60Hz):

- Speedometer 3.1: 35.5

- JetStream 2.2: 336.123

- MotionMark 1.3.1: 2136.29

- Speedometer 2.1: 624
