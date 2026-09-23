# Aura / Pearl AI Miner (Windows)

Windows desktop UI for the **Aura / Pearl AI** mining stack. Includes the PyQt packaged app (`dist/Aura`), launcher scripts, SRBMiner Multi binaries under `bin/`, and helper utilities.

> **Windows only.** This project targets Windows (`.exe`, `.bat`, `.vbs`, PyInstaller `dist`).

## Quick start

1. Clone this repo.
2. Edit `config.json` and set your real wallet addresses (replace the placeholders):
   - `YOUR_BTC_WALLET`
   - `YOUR_BCH_WALLET`
   - `YOUR_PRL_WALLET`
3. Double-click **`START.bat`** (or run `AuraUI.exe` / `dist\Aura\Aura.exe`).
4. Optional: `START_HIDDEN.vbs` starts the UI without a console window.

## Pearl AI boost

Boost / intensity is configurable from **1–8** via:

- `pearl_ai_boost`
- `ai_intensity`
- `hs_boost`

in `config.json` (and the UI controls when available).

## Layout

| Path | Purpose |
|------|---------|
| `START.bat` / `START_HIDDEN.vbs` | Launchers |
| `AuraUI.exe` | Small UI launcher |
| `dist/Aura/` | Packaged Aura app + `_internal` runtime |
| `bin/` | SRBMiner-Multi miner binaries |
| `_app/` | App source / supporting Python modules |
| `config.json` | Wallets, pool, boost settings (**placeholders in this publish**) |
| `assets/` | Icons / UI assets |

## Pool defaults (example)

Default template points at Unmineable Pearl pool host `pearlpow.unmineable.com:4444`. Change host/port/coin/payout to match your setup.

## Safety notes

- Never commit real wallet addresses or private keys.
- Local overrides and logs are ignored via `.gitignore`.
- Large miner/UI binaries are included so the folder can run after clone.

## License / third-party

SRBMiner-Multi is third-party software; respect its license and terms. Aura UI packaging uses PyQt5 / Python runtime components under their respective licenses.

## Miner binaries (SRBMiner)

Windows Defender often quarantines `SRBMiner-MULTI.exe` / the official zip as PUA when copied for publishing.

This GitHub tree includes the Aura UI, `dist/`, scripts, and `bin/` helpers. If `bin/SRBMiner-MULTI.exe` is missing after clone:

1. Download **SRBMiner-Multi** (Win64) from the official SRBMiner release.
2. Place `SRBMiner-MULTI.exe` under `bin\` (and optionally under `bin\srb\SRBMiner-Multi-3-6-1\`).
3. Add a Defender exclusion for this folder if your AV removes the miner again.

Live mining installs on your PC are separate; do not delete them when cloning this repo.
