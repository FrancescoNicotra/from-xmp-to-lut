# XMP-to-LUT Compiler

Converte preset XMP di Adobe Camera Raw (Lightroom/ACR) in file `.cube` 3D LUT compatibili con Affinity.
Converts Adobe Camera Raw XMP presets (Lightroom/ACR) into Affinity-compatible `.cube` 3D LUT files.

## Italiano

### Architettura

- **Rust core** — color math, identity LUT generation, `.cube` file writer
- **Python layer** — XMP parsing (defusedxml), CLI (click), orchestration
- **PyO3 + maturin** — bridge Rust ↔ Python

### Comandi CLI

#### `convert`

- Scopo: converte un preset XMP in una LUT `.cube`.
- Input: file `.xmp`.
- Output: file `.cube` (default: stesso nome nella stessa cartella).
- Opzioni chiave: `-o/--output`, `--size`, `--title`.

Esempio:

```bash
xmp-to-lut convert preset.xmp -o output.cube --size 64 --title "Preset"
```

#### `inspect`

- Scopo: mostra le impostazioni estratte dal preset XMP.
- Output: riepilogo per sezioni, campi modificati/invariati, curve non lineari.
- Warning: segnala proprieta `crs:` non supportate (se presenti).

Esempio:

```bash
xmp-to-lut inspect preset.xmp
```

#### `calibrate`

- Scopo: confronta una `.cube` simulata con una HALD processata da ACR.
- Output: report di errore; con `-o` scrive una `.cube` corretta.
- Input: `simulated.cube` e `processed_hald.png`.
- Opzioni chiave: `--level`, `-o/--output`, `--title`.
- Dipendenze: richiede `numpy` e `Pillow` per leggere la HALD.

Esempi:

```bash
# Solo report
xmp-to-lut calibrate simulated.cube processed_hald.png --level 8

# Report + output
python3 -m pip install 'xmp-to-lut[calibration]'
xmp-to-lut calibrate simulated.cube processed_hald.png --level 8 \
	-o corrected.cube --title "Preset (calibrated)"
```

#### `batch`

- Scopo: converte tutti i `.xmp` in una directory.
- Output: stato per file + riepilogo finale con categorie di errore.
- Opzioni chiave: `-o/--output-dir`, `--size`, `--verbose`.
- `--verbose`: mostra warning e dettagli errori per file.

Esempio:

```bash
xmp-to-lut batch ./presets -o ./luts --size 64 --verbose
```

### Setup

Prerequisiti:
- Python >= 3.10
- Rust toolchain (rustc + cargo)

#### Guida macOS

```bash
# (Opzionale) Installa Rust via Homebrew
brew install rust

# In alternativa: rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Crea e attiva un virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Installa maturin e compila l'estensione Rust in modalita develop
python3 -m pip install -U pip maturin
python3 -m maturin develop --extras dev
```

#### Guida Windows (PowerShell)

```powershell
# Installa Rust (winget)
winget install --id Rustlang.Rustup -e

# Crea e attiva un virtualenv
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installa maturin e compila l'estensione Rust in modalita develop
python -m pip install -U pip maturin
python -m maturin develop --extras dev
```

Se l'attivazione del venv fallisce, abilita gli script:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Project Structure

```
src/            Rust core (PyO3 lib)
python/         Python package (parser, CLI, mappings)
tests/          Test suite + XMP fixtures
```

## English

### Architecture

- **Rust core** — color math, identity LUT generation, `.cube` file writer
- **Python layer** — XMP parsing (defusedxml), CLI (click), orchestration
- **PyO3 + maturin** — Rust ↔ Python bridge

### CLI commands

#### `convert`

- Purpose: converts an XMP preset into a `.cube` LUT.
- Input: `.xmp` file.
- Output: `.cube` file (default: same name in the same folder).
- Key options: `-o/--output`, `--size`, `--title`.

Example:

```bash
xmp-to-lut convert preset.xmp -o output.cube --size 64 --title "Preset"
```

#### `inspect`

- Purpose: prints the parsed settings from an XMP preset.
- Output: grouped summary, modified/unchanged fields, non-linear curves.
- Warnings: flags unsupported `crs:` properties when present.

Example:

```bash
xmp-to-lut inspect preset.xmp
```

#### `calibrate`

- Purpose: compares a simulated `.cube` with a HALD image processed by ACR.
- Output: error report; with `-o` writes a corrected `.cube`.
- Input: `simulated.cube` and `processed_hald.png`.
- Key options: `--level`, `-o/--output`, `--title`.
- Dependencies: requires `numpy` and `Pillow` to read the HALD image.

Examples:

```bash
# Report only
xmp-to-lut calibrate simulated.cube processed_hald.png --level 8

# Report + output
python3 -m pip install 'xmp-to-lut[calibration]'
xmp-to-lut calibrate simulated.cube processed_hald.png --level 8 \
	-o corrected.cube --title "Preset (calibrated)"
```

#### `batch`

- Purpose: converts all `.xmp` files in a directory.
- Output: per-file status + final summary with failure categories.
- Key options: `-o/--output-dir`, `--size`, `--verbose`.
- `--verbose`: shows warnings and detailed errors per file.

Example:

```bash
xmp-to-lut batch ./presets -o ./luts --size 64 --verbose
```

### Setup

Requirements:
- Python >= 3.10
- Rust toolchain (rustc + cargo)

#### macOS guide

```bash
# (Optional) Install Rust via Homebrew
brew install rust

# Or use rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Create and activate a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install maturin and build the Rust extension in develop mode
python3 -m pip install -U pip maturin
python3 -m maturin develop --extras dev
```

#### Windows guide (PowerShell)

```powershell
# Install Rust (winget)
winget install --id Rustlang.Rustup -e

# Create and activate a virtualenv
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install maturin and build the Rust extension in develop mode
python -m pip install -U pip maturin
python -m maturin develop --extras dev
```

If venv activation fails, allow scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Project Structure

```
src/            Rust core (PyO3 lib)
python/         Python package (parser, CLI, mappings)
tests/          Test suite + XMP fixtures
```
