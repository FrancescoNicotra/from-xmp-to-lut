# XMP-to-LUT Compiler

Convert Adobe Camera Raw XMP sidecar files (Lightroom/ACR presets) into Affinity-compatible `.cube` 3D LUT files.

## Architecture

- **Rust core** — color math, identity LUT generation, `.cube` file writer
- **Python layer** — XMP parsing (defusedxml), CLI (click), orchestration
- **PyO3 + maturin** — bridges Rust ↔ Python

## Setup

Prerequisiti:
- Python >= 3.10
- Rust toolchain (rustc + cargo)

Installazione Rust (una delle due):

```bash
# Consigliato: rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Oppure con Homebrew
# brew install rust
```

## Avvio rapido (dev)

```bash
# Crea e attiva un virtualenv (maturin develop richiede un venv attivo)
python3 -m venv .venv
source .venv/bin/activate

# Installa maturin e compila l'estensione Rust in modalita develop
python3 -m pip install -U pip maturin
python3 -m maturin develop --extras dev

# Converti un preset
xmp-to-lut convert preset.xmp -o output.cube

# Ispeziona le impostazioni parsate
xmp-to-lut inspect preset.xmp

# Esegui i test
python3 -m pytest
```

## Project Structure

```
src/            Rust core (PyO3 lib)
python/         Python package (parser, CLI, mappings)
tests/          Test suite + XMP fixtures
```
