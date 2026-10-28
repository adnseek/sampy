#!/usr/bin/env python3
"""
Splice Sample Organizer (sampy)
===============================
Recursive audio sample classifier and organizer for Splice libraries (.wav, .mp3, .aif, .flac).
Turns the messy, deeply nested Splice pack folder structure into a clean, intuitive,
producer-friendly sample tree (Pads, Melodies, Vocals, Drums, Bass, Keys, Guitars, FX, etc.),
with subcategories (Spoken Word, Hooks, 808s, Kicks, Snares), key detection, and BPM.

Features:
- Pure Python 3 standard library (zero external dependencies).
- Multi-token NLP & heuristics for accurate classification of Splice naming patterns.
- Musical Key detection & normalization (e.g., Am, C#m, Fmaj, Bb).
- BPM extraction and automatic Loop vs. One-Shot detection.
- Special handling for Spoken Word, Choir, Adlibs, and Lead Vocal Hooks.
- Operation modes:
    * 'copy'    : Safe physical copy (default, keeps original Splice library untouched).
    * 'symlink' : Instant symbolic links (takes 0 MB disk space).
    * 'move'    : Moves original files.
- Dry-run mode (--dry-run) for zero-risk preview.
- Optional key grouping (--group-by-key) for melodic folders (e.g., Melodies/Am/).
- Collision-proof: Never overwrites files with identical names from different packs.
- Auto-generates a search index (library_index.json) in the target folder.
"""

import os
import sys
import re
import json
import shutil
import signal
import argparse
from pathlib import Path
from collections import defaultdict, Counter

# Handle Unix pipe closures (e.g. piping output to head or less) without stack traces
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except Exception:
    pass

SUPPORTED_EXTENSIONS = {'.wav', '.mp3', '.aif', '.aiff', '.flac'}

# Tokens that resemble musical keys but are common words, initials, or audio terms
INVALID_KEY_TOKENS = {
    'A', 'I', 'IN', 'IS', 'AM', 'PM', 'IT', 'TO', 'BY', 'X', 'NO', 'OFF', 'ON', 'UP', 'DO',
    'AT', 'SO', 'OR', 'IF', 'BE', 'MY', 'HE', 'WE', 'GO', 'AN', 'AS', 'ALL', 'THE', 'OF',
    'OS', 'DBM', 'VVD', 'FL', 'RKU', 'TSP', 'BOS', 'CPA', 'JJP', 'EX', 'EAF', 'BRS',
    'FSS', 'SM', 'WCK', 'BB3', 'LV', 'SFM', 'LDA', 'MEM2', 'TMZ', 'TR8', 'TD', 'MRNB2',
    'TRIV', 'PUKG', 'LHH2', 'FLINT2', 'SL', 'MT3', 'DPTE2', 'RW', 'TRKTRN', 'VPH',
    'MADLIB', 'KSHMR', 'BPM', 'WAV', 'MP3', 'AIFF', 'FLAC', 'AUDIO', 'HIT', 'SHOT', 'LOOP',
    'RAW', 'WET', 'DRY', 'ALT', 'VIP', 'EXT', 'FULL', 'LEAD', 'MAIN', 'CHORD', 'STACK'
}

STRONG_KEY_PATTERN = re.compile(r'^([A-Ga-g][#b]?(?:maj(?:or)?|min(?:or)?|m)?)$')


def tokenize(text):
    """
    Intelligently tokenize a string:
    - Splits camelCase (SciFiVoice -> Sci Fi Voice)
    - Separates numbers from letters (sax1 -> sax 1, 120bpm -> 120 bpm, while keeping C# / D# intact)
    - Normalizes to lowercase tokens
    """
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    s = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', s)
    s = re.sub(r'([0-9])([a-zA-Z])', r'\1 \2', s)
    return set(re.findall(r'[a-zA-Z0-9#]+', s.lower()))


class SampleClassifier:
    """Extracts category, subcategory, musical key, BPM, and loop/one-shot status."""

    @staticmethod
    def extract_bpm(filename, parent_path):
        """Extracts BPM from filename or directory path (range: 50-220)."""
        m = re.search(r'(?:^|[_\s\-])(?:bpm[_\s]*)?([5-9][0-9]|1[0-9]{2}|2[0-1][0-9])(?:[_\s\-]*(?:bpm))?(?=[_\s\.\-]|bmp|$)', filename, re.IGNORECASE)
        if m and 50 <= int(m.group(1)) <= 220:
            return int(m.group(1))
        m = re.search(r'(?:^|[_\s\-])(?:bpm[_\s]*)?([5-9][0-9]|1[0-9]{2}|2[0-1][0-9])(?:[_\s\-]*(?:bpm))?(?=[_\s\.\-]|$)', parent_path, re.IGNORECASE)
        if m and 50 <= int(m.group(1)) <= 220:
            return int(m.group(1))
        return None

    @staticmethod
    def extract_key(filename, parent_path):
        """Detects and normalizes musical key (e.g. Am, C#m, Fmaj, Bb)."""
        tokens = re.split(r'[_ \-\.\(\)\[\]]+', os.path.splitext(filename)[0])

        # Traverse tokens from right to left (keys are usually placed towards the end of filename)
        for t in reversed(tokens):
            if t.upper() in INVALID_KEY_TOKENS:
                continue
            m = STRONG_KEY_PATTERN.match(t)
            if m:
                raw = m.group(1)
                if len(raw) == 1:
                    if raw in 'ABCDEFG':
                        # Avoid false positives for the English word 'A' unless at the very end
                        if raw == 'A' and t != tokens[-1]:
                            continue
                        return raw
                else:
                    root = raw[0].upper()
                    acc = '#' if '#' in raw else ('b' if 'b' in raw.lower() else '')
                    rest = raw[len(root) + len(acc):].lower()
                    mode = 'm' if ('min' in rest or rest == 'm') else ('maj' if 'maj' in rest else '')
                    return f"{root}{acc}{mode}"

        # Check immediate parent folder name (e.g. /rw_insp90_tezlah_Em/)
        parent_tokens = re.split(r'[_ \-\.\(\)\[\]]+', os.path.basename(parent_path))
        for t in reversed(parent_tokens):
            if t.upper() in INVALID_KEY_TOKENS:
                continue
            m = STRONG_KEY_PATTERN.match(t)
            if m:
                raw = m.group(1)
                if len(raw) > 1:
                    root = raw[0].upper()
                    acc = '#' if '#' in raw else ('b' if 'b' in raw.lower() else '')
                    rest = raw[len(root) + len(acc):].lower()
                    mode = 'm' if ('min' in rest or rest == 'm') else ('maj' if 'maj' in rest else '')
                    return f"{root}{acc}{mode}"
        return None

    @classmethod
    def classify(cls, full_path, source_root=""):
        """Classifies a sample into standardized categories and subcategories."""
        fn = os.path.basename(full_path)
        fn_lower = fn.lower()
        path_lower = full_path.lower()
        dir_name = os.path.dirname(full_path)

        fn_tokens = tokenize(fn)
        path_tokens = tokenize(full_path)
        all_tokens = fn_tokens | path_tokens

        # Extract origin pack name
        parts = full_path.split(os.sep)
        pack_name = "Unknown Pack"
        try:
            if 'packs' in parts:
                idx = parts.index('packs')
                if idx + 1 < len(parts):
                    pack_name = parts[idx + 1]
            elif source_root and full_path.startswith(source_root):
                rel = os.path.relpath(full_path, source_root)
                pack_name = rel.split(os.sep)[0]
        except Exception:
            pass
        pack_tokens = tokenize(pack_name)

        bpm = cls.extract_bpm(fn, dir_name)
        key = cls.extract_key(fn, dir_name)

        # Loop vs One-Shot
        is_loop = False
        if all_tokens & {'loop', 'loops', 'stack', 'stacks', 'songstarter', 'songstarters', 'break', 'breaks'}:
            is_loop = True
        elif all_tokens & {'one_shot', 'oneshot', 'shot', 'shots', 'hit', 'hits'}:
            is_loop = False
        elif bpm is not None:
            is_loop = True

        category = "Other"
        subcategory = "Uncategorized"

        # -------------------------------------------------------------
        # 1. VOCALS (Highest priority for human voice / speech)
        # -------------------------------------------------------------
        if all_tokens & {'spoken', 'dialogue', 'speech', 'voiceover', 'quote', 'saying', 'speechclip'}:
            category = "Vocals"
            subcategory = "Spoken Word"
        elif all_tokens & {'choir', 'chorale', 'hymn'}:
            category = "Vocals"
            subcategory = "Choir"
        elif all_tokens & {'adlib', 'adlibs', 'shout', 'shouts', 'chant', 'chants', 'yell'}:
            category = "Vocals"
            subcategory = "Adlibs & Shouts"
        elif all_tokens & {'hook', 'hooks', 'acapella', 'acapellas', 'verse', 'chorus', 'phrases', 'phrase'}:
            if fn_tokens & {'vocal', 'vocals', 'vox', 'voice', 'singing', 'hook', 'phrase', 'acapella'} or 'vocal' in path_lower:
                category = "Vocals"
                subcategory = "Hooks & Phrases"

        if category == "Other" and (all_tokens & {'vocal', 'vocals', 'vox', 'voice', 'voices', 'singing'} or pack_tokens & {'vocal', 'vocals', 'voices'}):
            category = "Vocals"
            if all_tokens & {'atmosphere', 'atmos', 'texture', 'drone', 'pad'}:
                subcategory = "Vocal Textures & Atmos"
            elif is_loop:
                subcategory = "Vocal Loops"
            else:
                subcategory = "Vocal One-Shots"

        # -------------------------------------------------------------
        # 2. PADS & ATMOSPHERES
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'pad', 'pads'} or 'pad' in path_lower):
            category = "Pads"
            subcategory = "Pad Loops" if is_loop else "Pad One-Shots"
        elif category == "Other" and (all_tokens & {'atmosphere', 'atmos', 'drone', 'soundscape'} or 'atmos' in path_lower):
            category = "Pads"
            subcategory = "Atmospheres & Drones"

        # -------------------------------------------------------------
        # 3. BASS & 808 (Evaluated before general drums for 808s in drum packs)
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'808', '808s'} or fn_tokens & {'bass', 'sub'} or (all_tokens & {'bass'} and not all_tokens & {'double_bass', 'bassoon', 'brass'})):
            category = "Bass"
            if all_tokens & {'808', '808s'} or '808' in path_lower:
                subcategory = "808"
            elif all_tokens & {'synth', 'reese', 'acid', 'neuro'}:
                subcategory = "Synth Bass"
            elif all_tokens & {'guitar', 'electric', 'acoustic', 'upright'}:
                subcategory = "Electric & Acoustic Bass"
            elif all_tokens & {'sub'}:
                subcategory = "Sub Bass"
            else:
                subcategory = "Bass Loops" if is_loop else "Bass One-Shots"

        # -------------------------------------------------------------
        # 4. DRUMS & PERCUSSION
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'kick', 'kicks', 'snare', 'snares', 'clap', 'claps', 'snap', 'snaps',
                                                   'hihat', 'hihats', 'hat', 'hats', 'cymbal', 'cymbals', 'crash', 'ride',
                                                   'tom', 'toms', 'perc', 'percussion', 'shaker', 'tambourine', 'conga',
                                                   'bongo', 'rim', 'rimshot', 'rimshots', 'drum', 'drums', 'fill', 'roll',
                                                   'break', 'breaks', 'drm'} or fn_lower.endswith('_drm.wav')):
            category = "Drums"
            if all_tokens & {'kick', 'kicks'}:
                subcategory = "Kicks"
            elif all_tokens & {'snare', 'snares'}:
                subcategory = "Snares"
            elif all_tokens & {'clap', 'claps', 'snap', 'snaps'}:
                subcategory = "Claps & Snaps"
            elif 'open' in all_tokens and (all_tokens & {'hihat', 'hihats', 'hat', 'hats'} or 'open_hihats' in path_lower):
                subcategory = "Hi-Hats/Open"
            elif all_tokens & {'hihat', 'hihats', 'hat', 'hats'}:
                subcategory = "Hi-Hats/Closed" if not is_loop else "Hi-Hat Loops"
            elif all_tokens & {'cymbal', 'cymbals', 'crash', 'ride', 'splash'}:
                subcategory = "Cymbals & Rides"
            elif all_tokens & {'tom', 'toms'}:
                subcategory = "Toms"
            elif all_tokens & {'rim', 'rimshot', 'rimshots'}:
                subcategory = "Rims"
            elif all_tokens & {'fill', 'roll', 'fills', 'rolls'}:
                subcategory = "Fills & Rolls"
            elif all_tokens & {'break', 'breaks'}:
                subcategory = "Breakbeats"
            elif is_loop:
                if all_tokens & {'perc', 'percussion'}:
                    subcategory = "Percussion Loops"
                elif all_tokens & {'hihat', 'hat'}:
                    subcategory = "Hi-Hat Loops"
                else:
                    subcategory = "Full Drum Loops"
            else:
                subcategory = "Percussion One-Shots"

        # -------------------------------------------------------------
        # 5. KEYS & PIANO
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'piano', 'rhodes', 'wurlitzer', 'organ', 'clavinet', 'keys', 'epiano', 'pianoloop'} or 'piano' in path_lower):
            category = "Keys & Piano"
            if all_tokens & {'rhodes', 'wurlitzer', 'epiano'}:
                subcategory = "Rhodes & E-Piano"
            elif all_tokens & {'organ'}:
                subcategory = "Organ"
            else:
                subcategory = "Piano"

        # -------------------------------------------------------------
        # 6. GUITARS
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'guitar', 'guitars', 'ukulele', 'lick', 'riff'} or 'guitar' in path_lower):
            category = "Guitars"
            if all_tokens & {'acoustic'}:
                subcategory = "Acoustic Guitar"
            elif all_tokens & {'electric'}:
                subcategory = "Electric Guitar"
            else:
                subcategory = "Guitars"

        # -------------------------------------------------------------
        # 7. BRASS & WOODWINDS
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'sax', 'saxophone', 'trumpet', 'trombone', 'horn', 'horns', 'brass', 'flute', 'clarinet', 'woodwind'} or 'horn' in path_lower or 'sax' in path_lower):
            category = "Brass & Winds"
            if all_tokens & {'sax', 'saxophone'} or 'sax' in path_lower:
                subcategory = "Saxophone"
            elif all_tokens & {'flute', 'woodwind', 'clarinet'}:
                subcategory = "Flutes & Woodwinds"
            else:
                subcategory = "Trumpet & Horns"

        # -------------------------------------------------------------
        # 8. STRINGS & TRADITIONAL
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'violin', 'cello', 'strings', 'string', 'orchestral', 'viola', 'harp', 'pizzicato', 'yangqin', 'koto', 'sitar'} or 'string' in path_lower):
            category = "Strings"
            subcategory = "Strings"

        # -------------------------------------------------------------
        # 9. MELODIES & SONGSTARTERS / STACKS
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'songstarter', 'songstarters', 'stack', 'stacks', 'melody', 'melodic',
                                                   'chords', 'chord', 'progression', 'composition', 'groove', 'resampled',
                                                   'vinyl', 'loop', 'loops'} or 'melodic' in path_lower or 'melody' in path_lower):
            category = "Melodies"
            if all_tokens & {'songstarter', 'songstarters'}:
                subcategory = "Songstarters"
            elif all_tokens & {'stack', 'stacks', 'composition'}:
                subcategory = "Stacks & Compositions"
            elif all_tokens & {'chord', 'chords', 'progression'}:
                subcategory = "Chords & Progressions"
            else:
                subcategory = "Melody Loops"

        # -------------------------------------------------------------
        # 10. SYNTHS & LEADS
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'synth', 'lead', 'pluck', 'arp', 'arpeggio', 'bell', 'bells'} or 'synth' in path_lower):
            category = "Synths"
            if all_tokens & {'bell', 'bells'}:
                subcategory = "Bells & Mallets"
            elif all_tokens & {'arp', 'arpeggio'}:
                subcategory = "Arps & Sequences"
            elif all_tokens & {'pluck'}:
                subcategory = "Plucks"
            elif all_tokens & {'lead'}:
                subcategory = "Leads"
            else:
                subcategory = "Synth Loops" if is_loop else "Synth One-Shots"

        # -------------------------------------------------------------
        # 11. FX, SOUND DESIGN & FOLEY
        # -------------------------------------------------------------
        elif category == "Other" and (all_tokens & {'fx', 'sfx', 'riser', 'sweep', 'downlifter', 'impact', 'foley', 'noise',
                                                   'glitch', 'scratch', 'texture', 'textures', 'drone', 'siren', 'chirp',
                                                   'rain', 'nature', 'water', 'underwater', 'field', 'video', 'game',
                                                   'background', 'ambience', 'ambient', 'birds'} or pack_tokens & {'nature', 'water', 'police', 'biotopia'}):
            category = "FX & Textures"
            if all_tokens & {'riser', 'sweep', 'uplifter'}:
                subcategory = "Risers & Sweeps"
            elif all_tokens & {'impact', 'hit', 'boom', 'drop'}:
                subcategory = "Impacts & Drops"
            elif all_tokens & {'foley', 'field', 'noise', 'rain', 'nature', 'water', 'underwater', 'birds'} or 'nature' in pack_tokens:
                subcategory = "Foley & Field Recordings"
            elif all_tokens & {'texture', 'textures', 'drone', 'background'}:
                subcategory = "Textures & Drones"
            elif all_tokens & {'siren', 'video', 'game', 'glitch', 'scratch'} or 'police' in pack_tokens:
                subcategory = "Sound Effects"
            else:
                subcategory = "Misc FX"

        return {
            'source_path': full_path,
            'filename': fn,
            'pack': pack_name,
            'category': category,
            'subcategory': subcategory,
            'is_loop': is_loop,
            'bpm': bpm,
            'key': key
        }


class LibraryOrganizer:
    """Scans the source library, classifies each sample, and builds the target directory tree."""

    def __init__(self, source_dir, target_dir, mode='copy', group_by_key=False, dry_run=False, verbose=False, write_report=False):
        self.source_dir = os.path.abspath(source_dir)
        self.target_dir = os.path.abspath(target_dir)
        self.mode = mode
        self.group_by_key = group_by_key
        self.dry_run = dry_run
        self.verbose = verbose
        self.write_report = write_report
        self.stats = {
            'total_found': 0,
            'processed': 0,
            'categories': Counter(),
            'subcategories': Counter(),
            'keys': Counter(),
            'collisions_resolved': 0,
            'errors': []
        }
        self.samples = []

    def scan(self):
        """Recursively scans the source folder for supported audio files."""
        print(f"\n🔍 Scanning source directory: {self.source_dir}...")
        if not os.path.isdir(self.source_dir):
            raise FileNotFoundError(f"Source directory not found: {self.source_dir}")

        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.startswith('.'):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_p = os.path.join(root, f)
                    self.stats['total_found'] += 1
                    meta = SampleClassifier.classify(full_p, self.source_dir)
                    self.samples.append(meta)
                    self.stats['categories'][meta['category']] += 1
                    self.stats['subcategories'][f"{meta['category']} > {meta['subcategory']}"] += 1
                    if meta['key']:
                        self.stats['keys'][meta['key']] += 1

        print(f"✅ Found and classified {self.stats['total_found']} audio samples.\n")

    def build_target_path(self, meta):
        """Generates destination directory path and handles filename collisions."""
        cat = meta['category']
        subcat = meta['subcategory']
        key = meta['key']

        path_parts = [self.target_dir, cat]
        if subcat and subcat != "Uncategorized":
            path_parts.append(subcat)

        # Optional subfolder grouping by musical key:
        if self.group_by_key and key:
            path_parts.append(key)

        target_folder = os.path.join(*path_parts)
        target_filename = meta['filename']

        # Collision avoidance: If filename exists, append Pack tag
        final_path = os.path.join(target_folder, target_filename)
        if os.path.exists(final_path) and not self.dry_run:
            name, ext = os.path.splitext(target_filename)
            pack_tag = meta['pack'].replace('/', '-').strip()
            target_filename = f"{name} [{pack_tag}]{ext}"
            final_path = os.path.join(target_folder, target_filename)

            counter = 2
            while os.path.exists(final_path):
                target_filename = f"{name} [{pack_tag}]_{counter}{ext}"
                final_path = os.path.join(target_folder, target_filename)
                counter += 1
            self.stats['collisions_resolved'] += 1

        return target_folder, final_path

    def organize(self):
        """Executes the copy/symlink/move operations."""
        print(f"🚀 Organizing library into destination: {self.target_dir}")
        print(f"   Mode: {self.mode.upper()} {'(SIMULATION / DRY-RUN)' if self.dry_run else ''}")
        print(f"   Key Subfolders (--group-by-key): {'Enabled' if self.group_by_key else 'Disabled'}\n")

        for meta in self.samples:
            target_folder, dest_file = self.build_target_path(meta)
            src_file = meta['source_path']

            if self.verbose:
                key_info = f" [Key: {meta['key']}]" if meta['key'] else ""
                bpm_info = f" [{meta['bpm']} BPM]" if meta['bpm'] else ""
                print(f"  • {meta['category']} -> {meta['subcategory']}{key_info}{bpm_info}")
                print(f"    Source: {src_file}")
                print(f"    Target: {dest_file}")

            if not self.dry_run:
                try:
                    os.makedirs(target_folder, exist_ok=True)
                    if self.mode == 'copy':
                        shutil.copy2(src_file, dest_file)
                    elif self.mode == 'symlink':
                        if os.path.islink(dest_file) or os.path.exists(dest_file):
                            os.remove(dest_file)
                        os.symlink(src_file, dest_file)
                    elif self.mode == 'move':
                        shutil.move(src_file, dest_file)
                    self.stats['processed'] += 1
                except Exception as e:
                    self.stats['errors'].append((src_file, str(e)))
                    print(f"⚠️ Error processing {src_file}: {e}", file=sys.stderr)
            else:
                self.stats['processed'] += 1

        if not self.dry_run and self.write_report:
            self._save_report()

    def _save_report(self):
        """Saves a JSON index of all classified samples into the target directory."""
        try:
            os.makedirs(self.target_dir, exist_ok=True)
            report_path = os.path.join(self.target_dir, "library_index.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_samples': self.stats['total_found'],
                    'categories': dict(self.stats['categories']),
                    'subcategories': dict(self.stats['subcategories']),
                    'keys': dict(self.stats['keys']),
                    'samples': self.samples
                }, f, indent=2, ensure_ascii=False)
            print(f"\n📄 Saved search index: {report_path}")
        except Exception as e:
            print(f"Note: Could not save search index report: {e}")

    def print_summary(self):
        """Prints a comprehensive ASCII summary and statistics table."""
        print("\n" + "=" * 65)
        print("📊 SUMMARY & STATISTICS")
        print("=" * 65)
        print(f"Samples Processed:      {self.stats['processed']} / {self.stats['total_found']}")
        if self.stats['collisions_resolved'] > 0:
            print(f"Name Collisions Resolved: {self.stats['collisions_resolved']}")

        print("\n📁 CATEGORIES OVERVIEW:")
        for cat, count in sorted(self.stats['categories'].items(), key=lambda x: -x[1]):
            bar = "█" * int((count / max(self.stats['total_found'], 1)) * 30)
            print(f"  {cat:15} : {count:4d} samples {bar}")

        print("\n📂 TOP SUBCATEGORIES:")
        for subcat, count in sorted(self.stats['subcategories'].items(), key=lambda x: -x[1])[:15]:
            print(f"  • {subcat:35} : {count:3d}")

        if self.stats['keys']:
            print("\n🎹 DETECTED MUSICAL KEYS (TOP 12):")
            top_keys = sorted(self.stats['keys'].items(), key=lambda x: -x[1])[:12]
            key_line = ", ".join([f"{k} ({c})" for k, c in top_keys])
            print(f"  {key_line}")

        if self.stats['errors']:
            print(f"\n⚠️ Encountered {len(self.stats['errors'])} errors during execution.")

        print("=" * 65)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_dst = os.path.join(script_dir, "Splice_Organized")

    parser = argparse.ArgumentParser(
        description="Splice Sample Organizer (sampy): Recursively organize Splice samples into a clean directory tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Preview without modifying or copying any files (Dry-run):
  python3 organize_samples.py -s /path/to/Splice/packs --dry-run

  # 2. Copy samples into ./Splice_Organized right next to the script:
  python3 organize_samples.py -s /path/to/Splice/packs

  # 3. Specify custom target destination:
  python3 organize_samples.py -s /path/to/Splice/packs -t /path/to/Organized_Library

  # 4. Instant organization via symlinks (0 MB extra disk space):
  python3 organize_samples.py -s /path/to/Splice/packs --mode symlink

  # 5. Group tonal samples (Melodies, Pads, Vocals, 808s) into Key subfolders:
  python3 organize_samples.py -s /path/to/Splice/packs --group-by-key
        """
    )

    parser.add_argument(
        'source_pos',
        nargs='?',
        metavar='SOURCE',
        help="Path to your Splice packs folder (can also be passed via -s / --source)"
    )
    parser.add_argument(
        '-s', '--source',
        dest='source_opt',
        help="Path to your Splice packs folder (required)"
    )
    parser.add_argument(
        '-t', '--target',
        default=default_dst,
        help=f"Target directory for the organized tree (default: ./Splice_Organized next to script)"
    )
    parser.add_argument(
        '-m', '--mode',
        choices=['copy', 'symlink', 'move'],
        default='copy',
        help="Operation mode: 'copy' (safe physical copy), 'symlink' (instant, 0 MB disk space), 'move' (moves originals)"
    )
    parser.add_argument(
        '-k', '--group-by-key',
        action='store_true',
        help="Subdivide tonal sample folders (Melodies, Pads, Vocals, 808s) into musical key folders (e.g. Am/, Cm/)"
    )
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        help="Simulate scan & classification without copying, moving, or linking any files"
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Print detailed source and destination paths for every file"
    )
    parser.add_argument(
        '-i', '--write-index',
        action='store_true',
        help="Save an optional library_index.json search index in the target folder (disabled by default)"
    )

    args = parser.parse_args()

    # Determine source directory (from -s/--source or positional argument)
    source_input = args.source_opt or args.source_pos
    if not source_input:
        parser.print_help()
        print("\n❌ Error: The source directory containing your Splice packs is required!", file=sys.stderr)
        print("Example: python3 organize_samples.py -s /path/to/Splice/packs", file=sys.stderr)
        sys.exit(1)

    # Resolve and validate source path
    resolved_source = os.path.expanduser(source_input)
    if not os.path.exists(resolved_source):
        # Graceful check for typical Splice subfolder structures
        possible_sub = os.path.join(resolved_source, "sounds", "packs")
        parent_sounds = os.path.join(os.path.dirname(resolved_source), "sounds", "packs")
        if os.path.exists(possible_sub):
            print(f"ℹ️ Found Splice packs in subfolder: {possible_sub}")
            resolved_source = possible_sub
        elif os.path.exists(parent_sounds):
            print(f"ℹ️ Found Splice packs in: {parent_sounds}")
            resolved_source = parent_sounds
        else:
            print(f"❌ Error: Source directory does not exist: {resolved_source}", file=sys.stderr)
            sys.exit(1)

    resolved_target = os.path.expanduser(args.target)

    organizer = LibraryOrganizer(
        source_dir=resolved_source,
        target_dir=resolved_target,
        mode=args.mode,
        group_by_key=args.group_by_key,
        dry_run=args.dry_run,
        verbose=args.verbose,
        write_report=args.write_index
    )

    organizer.scan()
    organizer.organize()
    organizer.print_summary()


if __name__ == '__main__':
    main()
