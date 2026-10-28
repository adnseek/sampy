# Splice Sample Organizer (`sampy`) 🎧

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies](https://img.shields.io/badge/dependencies-zero%20(stdlib%20only)-success.svg)]()

> **Turn your messy, deeply-nested Splice folder chaos into a clean, producer-ready sample library for your DAW (Ableton Live, Logic Pro, FL Studio, Bitwig, MPC).**

---

## ❓ The Problem with Splice

When you download samples from Splice, they are scattered across hundreds of cryptic, deeply nested subdirectories:

```text
❌ Default Splice Chaos:
~/Splice/sounds/packs/
└── MEMPHIS TYPE BEATS - VOL 2/
    └── Origin_Sound_-_MEMPHIS_TYPE_BEATS_-_VOL_2/
        └── one_shots/
            └── drum_hits/
                └── hihats/
                    └── OS_MEM2_hihat_again.wav
```

Browsing this inside your DAW's file browser is a nightmare. Finding a simple clap or comparing pads takes forever because everything is locked away in its own pack silo.

---

## ✨ The Solution

**`sampy`** recursively scans your Splice library, uses token-based natural language pattern matching to accurately categorize every sample, extracts musical keys and BPMs, and organizes everything into a clean, intuitive tree:

```text
✅ Clean, Producer-Friendly Tree:
Splice_Organized/
├── 📁 Pads/
│   ├── Pad Loops/                   (Warm Pads, Synth Pads)
│   ├── Pad One-Shots/
│   └── Atmospheres & Drones/
├── 📁 Melodies/
│   ├── Songstarters/                (Full multi-instrument song concepts)
│   ├── Stacks & Compositions/       (Resampled chops & melodic stacks)
│   ├── Melody Loops/                (Toplines, riffs, arps)
│   └── Chords & Progressions/
├── 📁 Vocals/
│   ├── Spoken Word/                 (Dialogues, speeches, movie quotes)
│   ├── Hooks & Phrases/             (Lead vocal lines, chorus, verses)
│   ├── Adlibs & Shouts/             (Chants, shouts, vocal hits)
│   ├── Choir/                       (Choirs, hymns, vocal stacks)
│   ├── Vocal Textures & Atmos/
│   └── Vocal Loops / One-Shots/
├── 📁 Drums/
│   ├── Kicks/
│   ├── Snares/
│   ├── Claps & Snaps/
│   ├── Hi-Hats/
│   │   ├── Closed/
│   │   └── Open/
│   ├── Hi-Hat Loops/
│   ├── Full Drum Loops/
│   ├── Percussion / Percussion Loops/
│   ├── Cymbals & Rides/
│   ├── Toms/ & Rims/
│   └── Breakbeats & Fills/
├── 📁 Bass/
│   ├── 808/                         (Tuned 808s, Sub 808s, Distorted 808s)
│   ├── Synth Bass/                  (Reese, Acid, Neuro, Moog)
│   ├── Electric & Acoustic Bass/
│   └── Bass Loops / One-Shots/
├── 📁 Keys & Piano/ (Acoustic Piano, Rhodes, Wurlitzer, Organ)
├── 📁 Guitars/ (Acoustic Guitar, Electric Guitar)
├── 📁 Brass & Winds/ (Saxophone, Trumpet, Horns, Flutes)
├── 📁 Strings/ (Violins, Cellos, Orchestral Ensembles)
├── 📁 Synths/ (Leads, Plucks, Arps, Bells)
└── 📁 FX & Textures/ (Risers, Impacts, Foley, Sound Effects)
```

---

## 🚀 Key Highlights

- **Zero Dependencies**: Pure Python 3 standard library (`os`, `re`, `shutil`, `json`, `argparse`). No `pip install` required.
- **Accurate Classification**: Uses boundary-aware token splitting (splits camelCase, numbers, and audio tags) so `MADLIB_kick` is recognized as a Kick and not falsely classified as an `adlib`.
- **Key & BPM Detection**: Detects keys (e.g. `Am`, `C#m`, `Ebmaj`, `F#`) and tempos (e.g. `140_bpm`, `90BPM`).
- **Optional Key Subfolders (`--group-by-key`)**: Automatically organizes tonal folders (Melodies, Pads, Vocals, 808s) into key subfolders (e.g., `Melodies/Am/`, `Vocals/Cm/`).
- **Safe by Default**:
  - `copy` (default): Copies samples into the new directory, leaving your original Splice folder completely intact so the Splice Desktop app keeps working seamlessly.
  - `symlink`: Creates symbolic links in seconds, taking **0 MB extra disk space** while behaving like real audio files in your DAW.
- **Collision Proof**: If two packs contain a file with the same name (e.g. `Kick_01.wav`), the script automatically appends the pack name (`Kick_01 [Pack Name].wav`). Nothing is ever overwritten.
- **Search Index**: Automatically writes a `library_index.json` containing metadata for fast programmatic search.

---

## 🛠️ Quickstart

### 1. Preview without touching any files (Dry-Run)
```bash
python3 organize_samples.py --dry-run
```

### 2. Copy samples into a clean library (Safe & Standalone)
```bash
python3 organize_samples.py -s ~/Splice/sounds/packs -t ~/Music/Splice_Organized
```

### 3. Instant Symlink Mode (0 MB Extra Space)
```bash
python3 organize_samples.py --mode symlink
```

### 4. Group Tonal Folders by Musical Key
```bash
python3 organize_samples.py --group-by-key
```

---

## 📖 CLI Arguments Reference

| Option | Shorthand | Default | Description |
|---|---|---|---|
| `--source` | `-s` | `~/Splice/sounds/packs` | Source directory containing Splice packs |
| `--target` | `-t` | `~/Music/Splice_Organized` | Target directory for the new organized tree |
| `--mode` | `-m` | `copy` | `copy` (safe physical copy), `symlink` (instant, 0 MB disk space), or `move` |
| `--group-by-key` | `-k` | `False` | Subdivide tonal folders (Melodies, Pads, 808s, etc.) by key (e.g. `Am/`, `Cm/`) |
| `--dry-run` | `-n` | `False` | Simulate the entire process without modifying or writing any files |
| `--write-index` | `-i` | `False` | Save an optional `library_index.json` metadata search index |
| `--verbose` | `-v` | `False` | Print detailed source and destination paths for every sample |

---

## 💬 Ready-to-use Reddit Post Template

If you are sharing this on Reddit (e.g. r/edmproduction, r/trapproduction, r/FL_Studio, r/Ableton), feel free to use this template:

```markdown
**Title:** I built an open-source Python tool to organize the messy Splice sample folder into a clean, DAW-ready tree (Keys, BPM, Pads, Vocals, 808s, etc.)

Hey everyone,

Like many producers, I got tired of Splice's default folder hierarchy. When you download hundreds of samples, Splice dumps them into deeply nested pack folders (`Origin_Sound_.../one_shots/drum_hits/hihats/...`), making it super frustrating to browse through your DAW's sidebar.

I wrote **`sampy`** — a zero-dependency Python script that scans your Splice library and organizes everything into a clean, intuitive tree:

- **Pads** (Loops, One-Shots, Atmospheres)
- **Melodies** (Songstarters, Stacks, Loops, Chords)
- **Vocals** (Spoken Word, Hooks, Adlibs, Choirs)
- **Drums** (Kicks, Snares, Claps, Closed/Open Hats, Drum Loops)
- **Bass** (808s, Synth Bass, Electric Bass)
- **Keys, Guitars, Strings, Brass, Synths & FX**

### Key Features:
- **Zero dependencies** (pure Python 3 standard library, no pip install needed)
- **Key & BPM extraction** (can even group melodic folders into Key subfolders with `--group-by-key`)
- **Safe & Space-Saving**: Has `--mode symlink` so it takes 0 MB extra disk space and takes 2 seconds to link your whole library, without breaking the Splice desktop app.
- **Collision Protection**: Never overwrites files with generic names like `Kick_01.wav`.
- **Dry-run mode**: Preview everything before touching a single file.

GitHub link: [Your Repository Link Here]

Hope this helps speed up your workflow! Let me know if you have ideas or suggestions.
```

---

## 📄 License

MIT License. Free to use, modify, and distribute.
# sampy
# sampy
