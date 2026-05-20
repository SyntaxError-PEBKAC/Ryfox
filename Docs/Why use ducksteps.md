## 🚀 Why ducksteps is faster than stock Firefox

Mozilla ships a build of Firefox that runs on basically every x86-64 PC made in the last 15 years. That's great for compatibility. It's not great for performance. ducksteps is compiled specifically to go faster on the hardware it targets, using every tool available.

Here's what changed and why it matters:

---

- ⚙️ **Optimized build (`--enable-optimize`)**  
  Compiler optimizations turned all the way up. Faster code execution, snappier UI, smoother scrolling on heavy pages.

- 🗜️ **Full LTO (Link-Time Optimization) (`--enable-lto=full`)**  
  Normally the compiler optimizes each file in isolation. Full LTO lets it see the entire browser at once and eliminate wasted work across the whole codebase. Tighter hot paths, better cache behavior, fewer micro-pauses. This is one of the bigger contributors to the rendering gains — the 2D canvas rasterizer and compositor run in tight inner loops that span multiple files, and LTO can inline and optimize across those boundaries in ways a normal build can't.

- 🧪 **PGO (Profile-Guided Optimization) (`MOZ_PGO=1`)**  
  Before the final build compiles, Firefox runs a training session. It browses real websites and records which code runs most often. The compiler uses that data to make *those specific paths* as fast as possible. The result is measurably faster rendering and real-world JavaScript performance. One honest tradeoff: short synthetic benchmarks like Speedometer score slightly lower (~2%), because their cold-start JIT and rapid GC patterns don't show up much in a real browsing session. That's a deliberate call — the browser is tuned for how people actually use it, not benchmark loops.

- 🏋️ **Custom PGO training corpus (80+ sites, ~135 minutes)**  
  Stock Firefox trains PGO on a generic Mozilla workload. ducksteps trains on 80+ real websites — including YouTube, Reddit, news sites, maps, e-commerce, and speed tests — with realistic scroll behavior, video playback, and SPA navigation simulated automatically. Better training data means the optimization is tuned to how browsers actually get used. The rendering pipeline in particular benefits heavily from this: sustained scrolling and compositing paths are exactly what the training session exercises most.

- 🛠️ **Clang toolchain + LLD linker (`clang-cl`, `lld-link`)**  
  The full LLVM toolchain throughout — no MSVC codegen. Pairs tightly with LTO and PGO for stronger whole-program results and more consistent output.

- 🎯 **CPU-specific tuning — C/C++ and Rust**  
  Stock Firefox targets a generic x86-64 baseline that runs everywhere. ducksteps targets your CPU specifically:
  - **Zen 5 build:** `-march=znver5 -mtune=znver5` + `RUSTFLAGS="-C target-cpu=znver5"` — every instruction optimized for Ryzen 9000 / Ryzen AI 300 silicon, including the Rust components (WebRender, the style engine, parts of the networking stack)
  - **Legacy build:** `-march=x86-64-v3 -mtune=generic` + `RUSTFLAGS="-C target-cpu=haswell"` — targets the full AVX2 feature set without locking to one microarchitecture, so it runs fast on both Intel (Haswell 2013+) and AMD (Excavator 2015+) hardware
  
  CPU-specific codegen lets the compiler use instruction sets the generic build leaves on the table — on Zen 5 that includes AVX-512, which the rendering pipeline can vectorize against directly.

- 🚀 **Release mode (`--enable-release`)**  
  Production build settings, not developer build settings. Avoids overhead that's only useful when you're debugging Firefox itself.

- 🪓 **Debug mode stripped (`--disable-debug`)**  
  Developer logging and runtime checks removed. Less background work, fewer micro-pauses on heavy pages.

- 🔇 **Unused services removed at compile time**  
  The updater, maintenance service, default-browser agent, and crash reporter are all compiled out entirely — not just disabled in settings. ducksteps manages its own update cadence, doesn't phone home, and doesn't need Mozilla's background services running. Smaller binary (~5–9 MB), lower RAM floor (~4–9 MB less resident memory), no periodic background wake-ups, and less security risk.

---

## 📊 How it benchmarks

Tested on AMD Ryzen 9950X3D / 48GB DDR5 / RTX 4080 Super / Windows 11 25H2, five runs each, against a clean install of stock Firefox ESR on the same machine:

| Benchmark | What it measures | Result |
|---|---|---|
| MotionMark 1.3.1 | Rendering, animation, compositing | **+9.91%** |
| JetStream 3.0 | Real-world JavaScript and WebAssembly | **+1.95%** |
| Speedometer 3.1 | Short interactive microbenchmarks | **−2.05%** |

The Speedometer result is the tradeoff explained above — PGO trained for real browsing, not benchmark loops. The MotionMark and JetStream gains reflect what the build config was actually designed to do.

Full methodology, per-workload breakdowns, variance analysis, and a detailed explanation of what's driving each result: [PerformanceBenchmark.md](PerformanceBenchmark).

---

## 🧰 Build consistency

- 🧱 **Unified build (`--enable-unified-build`)**  
  Faster compile times — I can iterate and ship security updates faster.

- 📦 **Everything built locally (`--disable-artifact-builds`)**  
  No mixing prebuilt Mozilla pieces with locally-optimized ones. One coherent build, start to finish.
