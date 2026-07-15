#!/usr/bin/env python3
"""Findet exakte und inhaltlich ähnliche Duplikate in einem Verzeichnisbaum.

Exakte Duplikate: SHA-256-Hash-Vergleich über den vollständigen Dateiinhalt.
Near-Duplikate: Textähnlichkeit (difflib) für .txt/.md immer, .pdf/.docx
sofern die optionalen Bibliotheken pypdf / python-docx installiert sind.

Nur Analyse, keine Datei wird verändert oder gelöscht.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from difflib import SequenceMatcher

SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv"}
# Wenn ein Verzeichnis eine dieser Dateien enthält, ist es mit hoher Sicherheit
# ein Code-/Projektordner. Das Skill fasst solche Ordner ohnehin nicht an
# (eigene Konventionen, Git) — also gar nicht erst hineinscannen, sonst
# erzeugt der Duplikat-Report nur Rauschen aus __init__.py-Dateien,
# node_modules-Resten und Framework-Boilerplate.
PROJECT_MARKER_FILES = {
    ".git", "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml",
    "go.mod", "tsconfig.json", "pom.xml", "build.gradle", "Gemfile", "composer.json",
}
DUPLICATE_NAME_MARKERS = ("(1)", "(2)", "(3)", " copy", "-kopie", "_kopie", " kopie")
TEXT_SIMILARITY_THRESHOLD = 0.85
NEAR_DUP_FILE_LIMIT = 2000


def iter_files(root, skip_project_dirs, skipped_project_dirs):
    for dirpath, dirnames, filenames in os.walk(root):
        # Der Scan-Wurzelordner selbst wird nie als "Projekt" übersprungen,
        # nur seine Unterordner — sonst würde ein einzelnes package.json im
        # Downloads-Root den ganzen Lauf abwürgen.
        if skip_project_dirs and dirpath != root:
            if any(marker in filenames or marker in dirnames for marker in PROJECT_MARKER_FILES):
                skipped_project_dirs.append(dirpath)
                dirnames[:] = []  # nicht tiefer absteigen
                continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for name in filenames:
            yield os.path.join(dirpath, name)


def sha256_of(path, chunk_size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def looks_like_duplicate_name(path):
    name = os.path.basename(path).lower()
    return any(marker in name for marker in DUPLICATE_NAME_MARKERS)


def pick_master(paths):
    clean = [p for p in paths if not looks_like_duplicate_name(p)]
    candidates = clean if clean else paths
    return min(candidates, key=lambda p: os.path.getmtime(p))


def hash_all(files, warnings):
    """Hasht jede Datei einmal und gibt {pfad: hash} zurück. Der Rückgabewert
    wird sowohl für die exakte Duplikaterkennung als auch für den
    Teilmengen-Vergleich der Ordner genutzt — nicht doppelt hashen."""
    file_hashes = {}
    for path in files:
        try:
            file_hashes[path] = sha256_of(path)
        except OSError as e:
            warnings.append(f"Konnte nicht gehasht werden: {path} ({e})")
    return file_hashes


def find_exact_duplicates(file_hashes):
    by_hash = {}
    for path, digest in file_hashes.items():
        by_hash.setdefault(digest, []).append(path)

    groups = []
    for digest, paths in by_hash.items():
        if len(paths) > 1:
            groups.append(
                {
                    "hash": digest,
                    "files": sorted(paths),
                    "empfehlung_behalten": pick_master(paths),
                }
            )
    return groups


def build_known_hashes(dirs, skip_project_dirs, warnings):
    """Hasht alle Dateien in einem oder mehreren Ziel-Homes (PARA-Ordnern) und
    gibt {hash: [pfade]} zurück — die "bekannten Hashes" dessen, was dort schon
    liegt. Teuer bei großen Homes (hasht den ganzen Baum); für den inkrementellen
    Fall ist das Manifest (scripts/manifest.py) der günstigere Weg. Diese Funktion
    ist der vollständige, aber gründliche Abgleich."""
    known = {}
    for d in dirs:
        if not os.path.isdir(d):
            warnings.append(f"Ziel-Home für --against ist kein Verzeichnis: {d}")
            continue
        root = os.path.abspath(d)
        skipped_here = []
        for path in iter_files(root, skip_project_dirs, skipped_here):
            try:
                known.setdefault(sha256_of(path), []).append(path)
            except OSError as e:
                warnings.append(f"Ziel-Home: konnte nicht gehasht werden: {path} ({e})")
    return known


def find_already_in_target(file_hashes, known_hashes):
    """Meldet Quelldateien, deren Inhalt (Hash) schon in einem Ziel-Home liegt —
    ein erneuter Import wäre also eine Dublette. Rückgabe pro Treffer: die
    Quelldatei plus die Fundstellen im Ziel-Home."""
    results = []
    for path, digest in file_hashes.items():
        treffer = known_hashes.get(digest)
        if treffer:
            results.append({
                "quelldatei": path,
                "hash": digest,
                "ziel_treffer": sorted(treffer),
                "hinweis": "Inhaltsgleiche Datei existiert bereits im Ziel-Home — "
                           "erneuter Import wäre eine Dublette.",
            })
    return sorted(results, key=lambda r: r["quelldatei"])


FOLDER_VARIANT_SUFFIX = re.compile(r"\s*(?:\(\d+\)|\d+|copy|kopie)\s*$", re.IGNORECASE)


def normalize_folder_base(name):
    """"files (2)" -> "files", "brand-kit 2" -> "brand-kit". Dient nur dazu,
    Varianten-Ordner fürs Reporting zu gruppieren; der eigentliche Vergleich
    läuft über den Inhalt (Hash-Mengen), nicht über den Namen."""
    return FOLDER_VARIANT_SUFFIX.sub("", name).strip().lower()


def find_subset_folders(root, file_hashes, warnings):
    """Findet Ordner, deren Inhalt (als Menge von Datei-Hashes) vollständig in
    einem anderen Ordner enthalten ist — z.B. "files (2)" komplett in
    "files (3)". Das ist KEIN exaktes Duplikat (der größere Ordner hat mehr
    Dateien), wird von der reinen Hash-Gleichheit also nicht erfasst, ist aber
    genau der Fall, der bei mehrfach heruntergeladenen/entpackten Ordnern
    ("Ordner (1)", "(2)", ...) ständig auftritt. Nur direkte Unterordner der
    Scan-Wurzel werden verglichen, damit das überschaubar und aussagekräftig
    bleibt."""
    try:
        entries = sorted(os.listdir(root))
    except OSError as e:
        warnings.append(f"Konnte Wurzelverzeichnis nicht lesen: {root} ({e})")
        return []

    dir_hashes = {}
    for name in entries:
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        prefix = d + os.sep
        hs = {h for p, h in file_hashes.items() if p.startswith(prefix)}
        if hs:
            dir_hashes[d] = hs

    results = []
    dirs = list(dir_hashes.keys())
    for a in dirs:
        for b in dirs:
            if a == b:
                continue
            ha, hb = dir_hashes[a], dir_hashes[b]
            if ha == hb:
                # Inhaltlich identische Ordner — nur einmal berichten
                # (kleinere Zeichenkette zuerst), sonst tauchen sie doppelt auf.
                if a < b:
                    results.append({
                        "beziehung": "identisch",
                        "ordner_a": a,
                        "ordner_b": b,
                        "hinweis": "Beide Ordner haben inhaltlich exakt dieselben Dateien.",
                    })
            elif ha < hb:
                results.append({
                    "beziehung": "a_enthalten_in_b",
                    "ordner_a": a,
                    "ordner_b": b,
                    "gemeinsame_basis": normalize_folder_base(os.path.basename(a)) or None,
                    "hinweis": (
                        f"'{os.path.basename(a)}' ist inhaltlich vollständig in "
                        f"'{os.path.basename(b)}' enthalten — Kandidat zum Löschen, "
                        "sofern der größere Ordner der gewünschte Stand ist."
                    ),
                })
    return results


def extract_text(path, ext, warnings):
    if ext in (".txt", ".md"):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except OSError as e:
            warnings.append(f"Konnte Text nicht lesen: {path} ({e})")
            return None

    if ext == ".pdf":
        try:
            import pypdf
        except ImportError:
            warnings.append(
                "pypdf nicht installiert — PDF-Near-Duplicate-Erkennung übersprungen "
                "(pip install pypdf für vollständige Prüfung)"
            )
            return None
        try:
            reader = pypdf.PdfReader(path)
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:
            warnings.append(f"Konnte PDF nicht lesen: {path} ({e})")
            return None

    if ext == ".docx":
        try:
            import docx
        except ImportError:
            warnings.append(
                "python-docx nicht installiert — DOCX-Near-Duplicate-Erkennung übersprungen "
                "(pip install python-docx für vollständige Prüfung)"
            )
            return None
        try:
            document = docx.Document(path)
            return "\n".join(p.text for p in document.paragraphs)
        except Exception as e:
            warnings.append(f"Konnte DOCX nicht lesen: {path} ({e})")
            return None

    return None


def find_near_duplicates(files, exact_dup_paths, warnings):
    candidates = [
        p for p in files
        if os.path.splitext(p)[1].lower() in (".txt", ".md", ".pdf", ".docx")
        and p not in exact_dup_paths
    ]

    if len(candidates) > NEAR_DUP_FILE_LIMIT:
        warnings.append(
            f"{len(candidates)} Text-Dokumente gefunden, mehr als das Limit von "
            f"{NEAR_DUP_FILE_LIMIT} für den paarweisen Vergleich. "
            "Near-Duplicate-Erkennung übersprungen — bitte mit --skip-near-duplicates "
            "bestätigen oder auf ein kleineres Verzeichnis eingrenzen."
        )
        return []

    texts = {}
    for path in candidates:
        ext = os.path.splitext(path)[1].lower()
        text = extract_text(path, ext, warnings)
        if text and text.strip():
            texts[path] = text

    by_ext = {}
    for path, text in texts.items():
        ext = os.path.splitext(path)[1].lower()
        by_ext.setdefault(ext, []).append((path, text))

    groups = []
    seen = set()
    for ext, items in by_ext.items():
        for i in range(len(items)):
            path_a, text_a = items[i]
            if path_a in seen:
                continue
            group = [path_a]
            for j in range(i + 1, len(items)):
                path_b, text_b = items[j]
                if path_b in seen:
                    continue
                ratio = SequenceMatcher(None, text_a, text_b).ratio()
                if ratio >= TEXT_SIMILARITY_THRESHOLD:
                    group.append(path_b)
                    seen.add(path_b)
            if len(group) > 1:
                seen.add(path_a)
                groups.append(
                    {
                        "extension": ext,
                        "files": sorted(group),
                        "hinweis": "Textähnlichkeit >= {:.0%} — Empfehlung nicht automatisch, "
                        "bitte Inhalte vergleichen bevor eine Version gelöscht wird.".format(
                            TEXT_SIMILARITY_THRESHOLD
                        ),
                    }
                )
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="Zu scannendes Verzeichnis")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON statt Klartext")
    parser.add_argument(
        "--skip-near-duplicates",
        action="store_true",
        help="Nur exakte Duplikate suchen, keinen Textähnlichkeitsvergleich durchführen",
    )
    parser.add_argument(
        "--include-project-dirs",
        action="store_true",
        help="Auch Code-/Projektordner (mit .git, package.json usw.) mitscannen. "
        "Standardmäßig werden sie übersprungen und im Feld skipped_project_dirs gemeldet.",
    )
    parser.add_argument(
        "--against",
        action="append",
        default=[],
        metavar="ZIEL_HOME",
        help="Ein Ziel-PARA-Home (mehrfach angebbar). Meldet Quelldateien, die "
        "inhaltsgleich schon dort liegen (Feld bereits_im_ziel) — verhindert "
        "erneuten Import. Hasht den ganzen Ziel-Baum; für den inkrementellen Fall "
        "ist scripts/manifest.py günstiger.",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"Kein Verzeichnis: {args.directory}", file=sys.stderr)
        sys.exit(1)

    root = os.path.abspath(args.directory)
    warnings = []
    skipped_project_dirs = []
    files = list(iter_files(root, not args.include_project_dirs, skipped_project_dirs))

    file_hashes = hash_all(files, warnings)
    exact_groups = find_exact_duplicates(file_hashes)
    subset_folders = find_subset_folders(root, file_hashes, warnings)

    # Nur die redundanten Duplikate ausschliessen, nicht die ganze Gruppe -
    # sonst wird z.B. "vertrag_v2.txt" nie mit "vertrag.txt" verglichen, nur
    # weil "vertrag.txt" zufaellig auch ein exaktes Duplikat einer dritten
    # Datei ist.
    exact_dup_redundant_paths = {
        p for g in exact_groups for p in g["files"] if p != g["empfehlung_behalten"]
    }

    near_groups = []
    if not args.skip_near_duplicates:
        near_groups = find_near_duplicates(files, exact_dup_redundant_paths, warnings)

    bereits_im_ziel = []
    if args.against:
        known_hashes = build_known_hashes(args.against, not args.include_project_dirs, warnings)
        bereits_im_ziel = find_already_in_target(file_hashes, known_hashes)

    result = {
        "scanned_files": len(files),
        "exact_duplicates": exact_groups,
        "near_duplicates": near_groups,
        "subset_folders": subset_folders,
        "bereits_im_ziel": bereits_im_ziel,
        "skipped_project_dirs": skipped_project_dirs,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Gescannte Dateien: {result['scanned_files']}")
        print(f"\nExakte Duplikat-Gruppen: {len(exact_groups)}")
        for g in exact_groups:
            print(f"  Behalten: {g['empfehlung_behalten']}")
            for f in g["files"]:
                marker = " <- behalten" if f == g["empfehlung_behalten"] else " (Duplikat)"
                print(f"    {f}{marker}")
        print(f"\nNear-Duplikat-Gruppen: {len(near_groups)}")
        for g in near_groups:
            print(f"  [{g['extension']}] {g['hinweis']}")
            for f in g["files"]:
                print(f"    {f}")
        print(f"\nTeilmengen-/identische Ordner: {len(subset_folders)}")
        for s in subset_folders:
            print(f"  {s['hinweis']}")
        if args.against:
            print(f"\nSchon im Ziel-Home vorhanden: {len(bereits_im_ziel)}")
            for b in bereits_im_ziel:
                print(f"  {b['quelldatei']}")
                for t in b["ziel_treffer"]:
                    print(f"    -> bereits: {t}")
        if skipped_project_dirs:
            print(f"\nÜbersprungene Code-/Projektordner ({len(skipped_project_dirs)}):")
            for d in skipped_project_dirs:
                print(f"  - {d}")
        if warnings:
            print("\nHinweise:")
            for w in warnings:
                print(f"  - {w}")


if __name__ == "__main__":
    main()
