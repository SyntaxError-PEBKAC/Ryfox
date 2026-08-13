# ducksteps patch stack

These are the commits that turn a stock Firefox ESR checkout into ducksteps — exported with `git format-patch` from the `esr140` branch, applied on top of upstream Mozilla commit `6defe063302b` (see [`../Docs/Building.md`](../Docs/Building.md) for the full build workflow).

To use them: clone [mozilla-firefox/firefox](https://github.com/mozilla-firefox/firefox), check out the matching ESR branch/tag, then apply in order:

```bash
git am Patches/0001-*.patch Patches/0002-*.patch ... Patches/0009-*.patch
```

or all at once:

```bash
git am Patches/*.patch
```

Numbered in the order they were originally committed:

1. `branding + patchset` — ducksteps branding (icons, brand strings, `application.ini`, etc.)
2. `Custom PGO training` — replaces Mozilla's default PGO workload with a realistic browsing corpus
3. `WebExtension PGO training + profileserver patches`
4. `remove UPX from SFX stub` — VirusTotal false-positive fix
5. `Remove stale Marionette PGO script`
6. `PGO corpus updates` — duck.ai behavior, speedtest fixes, dwell bumps
7. `PGO fullscreen video, airbnb popup fix, librespeed retry, speedometer dwell bump, duck.ai submit fix`
8. `PGO remove video fullscreen, Speedometer dwell -15s, corpus tweaks`
9. `About dialog credits + What's new link` — credits Mozilla and SyntaxError-PEBKAC, points release notes at `Docs/Changelog.md`
