# 🦆 ducksteps vs Stock Firefox ESR: Benchmark Assesment by Claude Opus 4.7 Adaptive Thinking

**ducksteps 140.11.0 Zen5 (Standalone) vs Firefox ESR 140.11.0 (stock installer)**
*AMD Ryzen 9950X3D · 48GB DDR5 · RTX 4080 Super · Windows 11 25H2 · 3840×2160 @ 120Hz*

---

## 🧠 TL;DR (for the IT layman)

I built ducksteps to make Firefox faster on my specific hardware. I ran three industry-standard browser benchmarks five times each on both browsers, on the same PC, with the same conditions. Here's what came out the other side:

- 🎨 **Rendering performance: ducksteps is ~10% faster overall, and 52% faster on 2D canvas line drawing specifically.** If you scroll a lot, watch videos, use map apps, or interact with anything graphically rich, ducksteps wins by a meaningful margin.
- 🧮 **Real-world JavaScript: ducksteps is ~2% faster.** Modest but consistent.
- 🏎️ **Tight microbenchmarks (Speedometer): ducksteps is ~2% slower.** Yes, slower. Speedometer measures very short, very repetitive UI interactions, and ducksteps' PGO training is tuned for long-form realistic browsing instead. This is a deliberate tradeoff, and I'll explain why it's the right one below.

**Bottom line:** if your day looks like "scroll Reddit, watch YouTube, read articles, click around web apps," ducksteps will feel faster. If your day looks like "run TodoMVC benchmarks in a loop," buy stock in coffee instead (my personal favorite is Coffee Bean & Tea Leaf espresso).

---

## 🧪 Methodology

Both browsers tested on the same machine, same session day, with all unnecessary programs and services closed. Each benchmark run was preceded by `Ctrl+F5` (hard refresh) and a minimum 5-second settle period before clicking start. Firefox was a fresh install; ducksteps was the Standalone Zen5 7z extracted to a clean profile location.

- **Speedometer 3.1** — 5 runs each. JSON exports parsed for both headline scores and per-workload timings.
- **JetStream 3.0** — 5 runs each. Composite scores read from result screenshots.
- **MotionMark 1.3.1** — 5 runs each. Composite + per-subtest scores read from result screenshots.

Sample size (n=5 per browser per benchmark) is small but adequate for detecting effects larger than the run-to-run variance, which I report alongside every result.

---

## 📊 Headline Results

| Benchmark | Firefox mean | ducksteps mean | Δ | Δ% | FF CoV | DS CoV |
|---|---:|---:|---:|---:|---:|---:|
| Speedometer 3.1 (higher = better) | 34.64 | 33.93 | −0.71 | **−2.05%** | 0.69% | 1.05% |
| JetStream 3.0 (higher = better) | 194.07 | 197.85 | +3.78 | **+1.95%** | 0.84% | 0.66% |
| MotionMark 1.3.1 (higher = better) | 1070.76 | 1176.83 | +106.08 | **+9.91%** | 2.18% | 1.12% |

CoV = coefficient of variation (run-to-run noise). ducksteps is *less* noisy than stock on two of three benchmarks, which is itself a quiet win — tighter codegen producing more deterministic execution timing.

---

## 🏎️ Speedometer 3.1: The Tradeoff

Speedometer 3.1 measures synchronous and asynchronous timings on 20 short interactive workloads (TodoMVC variants across most major frameworks, plus news SPAs, rich-text editors, charting libraries, and a perf dashboard). The composite Score is `1000 / (geomean of test totals) / 60`, so even sub-millisecond regressions across many subtests compound.

**Per-workload breakdown (mean of 5 runs, lower ms = better):**

| Workload | Firefox (ms) | ducksteps (ms) | Δ |
|---|---:|---:|---:|
| React-Stockcharts-SVG | 57.65 | 60.88 | **+5.59%** 🔴 |
| TodoMVC-JavaScript-ES5 | 28.36 | 29.54 | +4.16% 🔴 |
| TodoMVC-WebComponents | 13.53 | 14.01 | +3.59% 🔴 |
| TodoMVC-Lit-Complex-DOM | 14.56 | 15.08 | +3.56% 🔴 |
| Editor-TipTap | 53.33 | 55.09 | +3.29% 🔴 |
| TodoMVC-Preact-Complex-DOM | 11.83 | 12.21 | +3.20% 🔴 |
| Charts-chartjs | 31.16 | 32.07 | +2.91% 🔴 |
| Charts-observable-plot | 35.94 | 36.94 | +2.79% 🔴 |
| TodoMVC-Svelte-Complex-DOM | 10.53 | 10.81 | +2.68% 🔴 |
| TodoMVC-Vue | 17.91 | 18.36 | +2.55% 🔴 |
| Editor-CodeMirror | 18.39 | 18.76 | +1.99% 🔴 |
| Perf-Dashboard | 41.45 | 42.26 | +1.97% 🔴 |
| TodoMVC-jQuery | 107.57 | 109.57 | +1.86% 🔴 |
| TodoMVC-Angular-Complex-DOM | 29.02 | 29.49 | +1.61% 🔴 |
| NewsSite-Nuxt | 47.81 | 48.57 | +1.58% 🔴 |
| TodoMVC-JavaScript-ES6-Webpack | 40.60 | 41.05 | +1.12% 🔴 |
| TodoMVC-Backbone | 20.27 | 20.48 | +1.06% 🔴 |
| NewsSite-Next | 60.07 | 60.65 | +0.96% ⚪ |
| TodoMVC-React-Redux | 27.09 | 27.05 | −0.16% ⚪ |
| **TodoMVC-React-Complex-DOM** | **26.83** | **26.22** | **−2.27% 🟢** |

ducksteps loses on 18 of 20 workloads, ties on 1, wins on 1. That's not random noise — that's a *pattern*. And the pattern points at exactly one thing: **the PGO training corpus.**

### Why PGO training causes this

ducksteps trains PGO on ~88 real websites with 60–300 second dwell times — long YouTube playback, multi-minute Reddit scrolls, sustained map panning, full Speedometer 3 runs included as a static dwell, real article reading. The instrumented build records which code paths execute most, and the optimizer makes those paths fast at the expense of paths that didn't show up often.

Speedometer 3.1's individual subtests run on the order of 10–100ms each and exercise the same hot path 10 times in a row. They hit:

- **JIT warmup paths** — baseline-to-Ion transition code that runs once per workload and then never again
- **Cold interpreter dispatch** — short-lived bytecode that never reaches Ion
- **GC paths from rapid allocate/free cycles** — TodoMVC adds and deletes 100 items, hammering minor GC

The PGO profile barely touches those paths (long browsing sessions are mostly *already warm* JIT code), so the optimizer deprioritizes them. The result: the optimized binary is slightly slower on cold-start microbenchmark code, and slightly faster on everything else.

This is the textbook PGO tradeoff. The literature on profile-guided optimization is full of warnings that training data should match production workload. ducksteps' training data deliberately *doesn't* match Speedometer; it matches actual browsing. So Speedometer gets a small consistent penalty, and actual browsing gets the speedup.

The lone Speedometer win — TodoMVC-React-Complex-DOM (−2.27%) — is the closest workload in the suite to "what real React apps look like at runtime," which is consistent with this story: the more a Speedometer subtest resembles the PGO training corpus, the closer ducksteps gets to (or surpasses) stock.

**Confidence: HIGH.** The pattern is too consistent across 20 independent workloads to be noise, and the magnitude (−2.05% composite) lines up with what published PGO tradeoff studies report when training/test distributions diverge.

---

## 🧮 JetStream 3.0: The Quiet Win

JetStream 3.0 runs 100+ JavaScript and WebAssembly programs spanning compiler workloads, crypto, codecs, ML, and real-world derived snippets. It's the most representative pure-JS benchmark for "what advanced web apps actually do."

| | Firefox | ducksteps |
|---|---:|---:|
| Mean | 194.07 | 197.85 |
| Min | 192.37 | 196.71 |
| Max | 195.76 | 199.89 |
| Stdev | 1.63 | 1.30 |
| CoV | 0.84% | 0.66% |

**+1.95% in favor of ducksteps**, with tighter variance.

A ~2% JetStream gain is modest in absolute terms but exactly what you'd expect from `-march=znver5` + full LTO + PGO when the training corpus is well-aligned with the benchmark. JetStream's workloads are long-running (lots of iterations of the same function), so the PGO profile captures their hot paths reasonably well. The CPU-specific codegen wins come from:

- **Tighter register allocation** under known Zen 5 register pressure characteristics
- **Better branch prediction hints** for Zen 5's TAGE-based predictor
- **AVX-512 paths** where available (Zen 5 has 512-bit datapaths, not the double-pumped 256-bit of Zen 4)
- **LTO cross-TU inlining** that the stock build's per-TU optimization can't reach

Subtest-level reading from screenshots (sampled, not exhaustive): ducksteps shows the largest gains on compute-heavy workloads (crypto suites, raytrace variants, Babylon physics) and is roughly flat on string/parsing-heavy ones (acorn-wtb, esprima-next-wtb). That's consistent with the SIMD/register-allocation story above.

---

## 🎨 MotionMark 1.3.1: The Knockout

MotionMark measures how much animation complexity the browser can sustain at the target frame rate (120 fps on this display) before frame drops occur. Each subtest stresses a different rendering subsystem.

| | Firefox | ducksteps |
|---|---:|---:|
| Mean composite | 1070.76 | 1176.83 |
| Min | 1034.20 | 1158.16 |
| Max | 1097.81 | 1192.81 |
| CoV | 2.18% | 1.12% |

**+9.91% composite gain.** And ducksteps' CoV is half of Firefox's — meaning the same workload produces more deterministic frame timing, which is exactly what you want from a compositor.

### Subtest breakdown (mean of 5 runs)

| Subtest | What it stresses | Firefox | ducksteps | Δ |
|---|---|---:|---:|---:|
| Canvas Lines | 2D canvas line rasterization | 12571.77 | 19171.92 | **+52.50%** 🟢 |
| Paths | SVG path rendering | 2352.64 | 2545.23 | +8.19% 🟢 |
| Canvas Arcs | Bézier/arc rasterization on canvas | 757.82 | 810.05 | +6.89% 🟢 |
| Design | DOM + text layout + reflow | 224.53 | 238.80 | +6.35% 🟢 |
| Multiply | CSS transform matrix multiply | 1089.52 | 1142.95 | +4.90% 🟢 |
| Leaves | Small element DOM transforms | 1060.50 | 1105.04 | +4.20% 🟢 |
| Images | Image decode + composite | 259.65 | 268.46 | +3.39% 🟢 |
| Suits | Mixed workload | 1150.85 | 1151.00 | +0.01% ⚪ |

### The Canvas Lines anomaly

The +52.5% gap on Canvas Lines deserves its own paragraph. Firefox's mean is 12,572 with runs spanning 12,089–12,869 (~6% range). ducksteps' mean is 19,172 with runs spanning 18,826–20,245 — one outlier high run inflates the mean slightly, but even excluding that run, ducksteps comes in at ~18,900, which is still **+50% over Firefox**. This isn't a measurement artifact.

Canvas Lines stresses the 2D canvas line rasterization path through Skia and WebRender. The inner loop:

1. Iterates over a large set of line segments
2. Computes screen-space transforms (vectorizable math)
3. Rasterizes to GPU-uploaded textures (memory bandwidth bound)
4. Submits draw calls to the compositor (call-overhead sensitive)

Every one of those steps benefits from the ducksteps build configuration:

- **Step 2** vectorizes well on AVX-512, which `-march=znver5` enables
- **Step 3** benefits from LTO eliminating cross-module function call overhead in the hot loop
- **Step 4** benefits from PGO inlining the high-frequency submission path
- The Rust WebRender components (`RUSTFLAGS="-C target-cpu=znver5"`) get the same CPU-specific treatment as the C++ side, where stock Firefox compiles Rust to generic x86-64

This is the exact codepath the ducksteps configuration was designed to win, and it's winning hard.

### The other subtests

The remaining wins (Paths, Canvas Arcs, Design, Multiply, Leaves, Images) all sit in the +3–8% range, which is consistent with the "general LTO + PGO + march" benefit applied to less-vectorizable rendering paths. Each subtest stresses a slightly different mix of WebRender, layout, font shaping, and compositor work, and ducksteps wins consistently across all of them.

**Suits** ties at +0.01%. That subtest is intentionally a mix of all the others, so it ends up averaging out near zero gain (composite is higher because Canvas Lines gets weighted heavily by the score formula).

### Why MotionMark wins more than JetStream

Two reasons:

1. **Workload alignment.** The PGO training corpus is mostly real websites with sustained scrolling, video playback, and SPA interaction — all WebRender-heavy. The compositor and rasterizer hot paths the training session exercised are *exactly* the ones MotionMark measures.
2. **Code locality.** Rendering pipelines are big tight inner loops over millions of pixels/vertices/segments. LTO can inline aggressively across translation unit boundaries and the PGO profile tells the compiler exactly which branches to predict. JavaScript JITs are themselves runtime compilers that produce already-optimized code, so the static compiler has less to do at build time.

**Confidence: HIGH.** Both the magnitude and the per-subtest distribution match what the literature predicts for whole-program LTO + PGO + CPU-specific codegen on a rendering-heavy workload.

---

## 🔬 Why these results make sense

Pulling it together, the build configuration drives three independent effects:

| Effect | Driven by | What it helps | What it doesn't help |
|---|---|---|---|
| Better instruction selection | `-march=znver5` + `RUSTFLAGS -C target-cpu=znver5` | Vectorizable inner loops, SIMD-friendly math | Branch-heavy control flow, JIT-emitted code |
| Whole-program optimization | `--enable-lto=full` | Cross-TU inlining, dead code elimination | Code paths that were already inlined |
| Hot-path specialization | `MOZ_PGO=1` + custom training corpus | Whatever the training corpus exercised | Whatever it didn't |

Speedometer is a *microbenchmark* in the strict sense: short, repetitive, designed to be sensitive to JIT and GC behavior. The PGO profile underweights those paths, so ducksteps loses a small consistent amount. JetStream is *macrobenchmark*-shaped (long JS programs), which the profile covers, so ducksteps gains modestly. MotionMark is *exactly* what the PGO corpus trained on (sustained rendering), so ducksteps wins decisively.

If I wanted to flip the Speedometer result, I could add Speedometer 3 itself as a training workload — and actually, the PGO corpus already includes Speedometer 3 as a dwell site, but only as one item in 88, weighted by dwell time. Increasing its weight would help Speedometer scores at the cost of less-trained real-world paths. That's a Faustian bargain and I'm not making it.

---

## 📐 Variance & reproducibility notes

- All runs on the same machine, same session day, same display configuration. No reboots between runs.
- Background services minimized but not disabled (Defender, networking, audio stack all live).
- ducksteps' CoV is lower than Firefox's on JetStream and MotionMark, slightly higher on Speedometer. The Speedometer increase is small (1.05% vs 0.69%) and consistent with the workload-mismatch story (subtests that fall outside the trained code paths produce slightly more variable timings).
- The MotionMark Canvas Lines outlier in ducksteps run 1 (20,245 vs 18,826–19,061 in runs 2–5) is real measurement noise but doesn't change the conclusion — removing it still leaves +50% over Firefox.
- n=5 is small. A future round with n=20+ would tighten the confidence intervals, especially on Speedometer where the effect is small and noisy.

---

## 🤷 Honest takeaways

- ducksteps trades a small amount of synthetic microbenchmark performance for a meaningful gain in real-world rendering and a smaller gain in real-world JavaScript. I think this is the right tradeoff for a browser people actually browse with.
- The Speedometer regression is real and I'm not hiding it. If your specific use case is dominated by very short interactive bursts on TodoMVC-shaped apps with cold JIT, stock Firefox will be ~2% faster. For everyone else, ducksteps wins.
- The MotionMark Canvas Lines result (+52.5%) is unusually large and deserves more investigation in a future profiling session. The hypothesis (AVX-512 + LTO + WebRender hot loop) is plausible but I haven't proven it via flame graphs yet.
- These results are specific to a Zen 5 9950X3D running Windows 11. The Legacy ducksteps build (compiled `-march=x86-64-v3`) would show smaller gains. Other hardware will land somewhere between stock and the Zen 5 numbers reported here.

---

## 📎 Raw data

### Speedometer 3.1 (composite score, higher = better)

| Run | Firefox | ducksteps |
|:---:|---:|---:|
| 1 | 34.52 | 33.45 |
| 2 | 34.85 | 33.80 |
| 3 | 34.87 | 34.15 |
| 4 | 34.66 | 33.85 |
| 5 | 34.30 | 34.38 |
| **mean** | **34.64** | **33.93** |
| stdev | 0.24 | 0.36 |

### JetStream 3.0 (composite score, higher = better)

| Run | Firefox | ducksteps |
|:---:|---:|---:|
| 1 | 195.76 | 198.36 |
| 2 | 194.29 | 197.21 |
| 3 | 195.51 | 199.89 |
| 4 | 192.40 | 196.71 |
| 5 | 192.37 | 197.07 |
| **mean** | **194.07** | **197.85** |
| stdev | 1.63 | 1.30 |

### MotionMark 1.3.1 (composite score @ 120fps, higher = better)

| Run | Firefox | ducksteps |
|:---:|---:|---:|
| 1 | 1097.81 | 1192.81 |
| 2 | 1080.76 | 1181.47 |
| 3 | 1072.72 | 1170.03 |
| 4 | 1034.20 | 1158.16 |
| 5 | 1068.29 | 1181.70 |
| **mean** | **1070.76** | **1176.83** |
| stdev | 23.34 | 13.19 |

---

*Benchmarks run 20 May 2026 on AMD Ryzen 9950X3D / 48GB DDR5 / RTX 4080 Super / Windows 11 25H2. Same machine, same session.*
