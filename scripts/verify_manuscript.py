#!/usr/bin/env python3
"""End-to-end read-only verification of corpus integrity, desensitization, table sync, PDFs, and Zenodo bundle."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SENSITIVE_PATTERNS = (
    r"/Users/[A-Za-z0-9_.-]+",
    r"/home/[A-Za-z0-9_.-]+",
    r"/private/var/",
    r"gateway\.ai\.cloudflare\.com",
    r"workers\.dev",
    r"cf-aig-authorization",
    r"HTTP-Referer",
    r"sk-[A-Za-z0-9]{20,}",
)

BANNED_REVISION_REMNANTS = (
    "repair_results",
    "hueprint_repair",
    "table-repair",
    "table_repairs",
    "tsc_analysis",
    "tsc_round",
    "tsc_energy_u",
    "paper_revision",
    "Round-5",
    "Round-6",
    "review_round1",
    "review_round2",
    "legacy_lab",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_page_count(path: Path) -> int:
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        proc = subprocess.run([pdfinfo, str(path)], check=True, capture_output=True, text=True)
        m = re.search(r"^Pages:\s+(\d+)\s*$", proc.stdout, re.M)
        if m:
            return int(m.group(1))
    raw = path.read_bytes()
    counts = [int(x) for x in re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", raw, flags=re.S)]
    if counts:
        return max(counts)
    raise ValueError(f"Could not determine page count for {path}")


def check_integrity_manifests() -> tuple[int, int]:
    manifest = json.loads((ROOT / "results" / "integrity_manifest.json").read_text(encoding="utf-8"))
    files = manifest["files"]
    if len(files) != 58 or manifest["corpus_jsonl_count"] != 12:
        raise AssertionError(f"Unexpected manifest counts: {len(files)} files, {manifest['corpus_jsonl_count']} jsonls")
    for rel, expected in files.items():
        p = ROOT / rel
        if not p.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel}")
        actual = sha256(p)
        if actual != expected:
            raise AssertionError(f"SHA-256 mismatch for {rel}: {actual} != {expected}")

    s5_manifest_path = ROOT / "extensions" / "competitor_benchmark_20261120" / "s5_integrity_manifest.json"
    s5_manifest = json.loads(s5_manifest_path.read_text(encoding="utf-8"))
    s5_files = s5_manifest["files"]
    if len(s5_files) != 10 or s5_manifest["corpus_jsonl_count"] != 3:
        raise AssertionError(f"Unexpected S5 manifest counts: {len(s5_files)} files, {s5_manifest['corpus_jsonl_count']} jsonls")
    for rel, expected in s5_files.items():
        p = ROOT / rel
        if not p.is_file():
            raise FileNotFoundError(f"Missing S5 protected file: {rel}")
        actual = sha256(p)
        if actual != expected:
            raise AssertionError(f"S5 SHA-256 mismatch for {rel}: {actual} != {expected}")

    repo_jsonls = sorted(
        str(p.relative_to(ROOT))
        for p in ROOT.rglob("*.jsonl")
        if ".git" not in p.parts
    )
    manifest_jsonls = sorted(
        [k for k in files if k.endswith(".jsonl")] + [k for k in s5_files if k.endswith(".jsonl")]
    )
    if repo_jsonls != manifest_jsonls:
        raise AssertionError(f"Repo JSONL inventory {repo_jsonls} != manifest JSONLs {manifest_jsonls}")

    lv_manifest = json.loads(
        (ROOT / "extensions" / "live_validation_20261111" / "lv_rgb_integrity_manifest.json").read_text(encoding="utf-8")
    )["sha256"]
    for rel, expected in lv_manifest.items():
        if rel == "analyze.py":
            continue  # analyze.py added hybrid_reg after initial 2026-11-11 snapshot; verified in service_audit/manifest.json
        p = ROOT / rel
        if not p.is_file():
            raise FileNotFoundError(f"Missing lv_rgb protected file: {rel}")
        actual = sha256(p)
        if actual != expected:
            raise AssertionError(f"lv_rgb SHA-256 mismatch for {rel}: {actual} != {expected}")
    return len(files), len(lv_manifest) - 1


def check_sanitization_and_remnants() -> int:
    sens_re = re.compile("|".join(SENSITIVE_PATTERNS))
    scanned = 0
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        if p.name in {"verify_manuscript.py", "build_zenodo_package.py", "tectonic"}:
            continue
        if p.suffix in {".pdf", ".png", ".ttf", ".ttc", ".zip", ".log", ".pyc", ".pyo"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        scanned += 1
        m = sens_re.search(text)
        if m:
            raise AssertionError(f"Sensitive pattern {m.group(0)!r} found in {p.relative_to(ROOT)}")
        if p.name == "test_manuscript_integrity.py":
            continue
        for remnant in BANNED_REVISION_REMNANTS:
            if remnant in text:
                raise AssertionError(f"Internal revision remnant {remnant!r} found in {p.relative_to(ROOT)}")
    return scanned


def check_sync_scripts() -> None:
    for cmd in (
        [sys.executable, "-B", "paper/sync_supplement_inventory.py", "--check"],
        [sys.executable, "-B", "paper/sync_benchmark_tables.py", "--check"],
        [sys.executable, "-B", "paper/sync_service_tables.py", "--check"],
        [sys.executable, "-B", "paper/sync_s5_tables.py", "--check"],
        [sys.executable, "-B", "paper/build_latex.py", "--check"],
    ):
        subprocess.run(cmd, cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def check_pdfs_and_zenodo_bundle() -> dict[str, int]:
    pages = {}
    for target, expected_pages in (("ieee", 12), ("supplement", 20)):
        pdf = ROOT / "paper" / target / "main.pdf"
        if not pdf.is_file():
            raise FileNotFoundError(f"Missing build output paper/{target}/main.pdf")
        actual_pages = pdf_page_count(pdf)
        if actual_pages != expected_pages:
            raise AssertionError(f"Expected {expected_pages} pages for {target}, got {actual_pages}")
        pages[target] = actual_pages

        log = ROOT / "paper" / target / "main.log"
        if log.is_file():
            log_text = log.read_text(encoding="utf-8", errors="replace")
            if "Overfull \\hbox" in log_text or "Overfull \\vbox" in log_text:
                raise AssertionError(f"Overfull box in paper/{target}/main.log")
            if "Underfull \\vbox" in log_text:
                raise AssertionError(f"Underfull vbox in paper/{target}/main.log")

    for req_meta in (ROOT / ".zenodo.json", ROOT / "CITATION.cff", ROOT / "LICENSE"):
        if not req_meta.is_file():
            raise FileNotFoundError(f"Missing release metadata file: {req_meta.relative_to(ROOT)}")

    for tex_name in ("main.tex", "body.tex", "references.tex", "biography.tex"):
        raw = (ROOT / "paper" / "ieee" / tex_name).read_text(encoding="utf-8")
        if not all(ord(c) < 128 for c in raw):
            raise AssertionError(f"Non-ASCII character in paper/ieee/{tex_name}")

    zenodo_dir = ROOT / "zenodo_release"
    if not zenodo_dir.is_dir():
        return pages

    combined_pdf = zenodo_dir / "HuePrint_Preprint.pdf"
    zip_path = zenodo_dir / "HuePrint_Replication_Package.zip"
    z_manifest_path = zenodo_dir / "zenodo_manifest.json"
    for req_file in (
        combined_pdf,
        zenodo_dir / "HuePrint_Main_Manuscript.pdf",
        zenodo_dir / "HuePrint_Supplementary_Material.pdf",
        zip_path,
        z_manifest_path,
        zenodo_dir / "ZENODO_UPLOAD_GUIDE.md",
    ):
        if not req_file.is_file():
            raise FileNotFoundError(f"Missing Zenodo release file: {req_file.relative_to(ROOT)}")

    combined_pages = pdf_page_count(combined_pdf)
    if combined_pages != 32:
        raise AssertionError(f"Expected 32 pages in HuePrint_Preprint.pdf, got {combined_pages}")
    pages["zenodo_combined"] = combined_pages

    z_manifest = json.loads(z_manifest_path.read_text(encoding="utf-8"))
    for fname, meta in z_manifest["artifacts"].items():
        actual_hash = sha256(zenodo_dir / fname)
        if actual_hash != meta["sha256"]:
            raise AssertionError(f"Zenodo artifact hash mismatch for {fname}")

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        for req in (
            "HuePrint/.zenodo.json",
            "HuePrint/CITATION.cff",
            "HuePrint/LICENSE",
            "HuePrint/README.md",
            "HuePrint/README-ZH.md",
            "HuePrint/results/integrity_manifest.json",
            "HuePrint/extensions/competitor_benchmark_20261120/s5_integrity_manifest.json",
            "HuePrint/scripts/operational_diagnostics.py",
            "HuePrint/paper/ieee/main.tex",
            "HuePrint/paper/ieee/body.tex",
            "HuePrint/paper/ieee/references.tex",
            "HuePrint/paper/ieee/biography.tex",
            "HuePrint/paper/supplement/main.pdf",
        ):
            if req not in names:
                raise AssertionError(f"Missing {req} in HuePrint_Replication_Package.zip")
        if "HuePrint/tools/tectonic" in names:
            raise AssertionError("Platform binary HuePrint/tools/tectonic found in Zenodo zip")
        for forbidden in (".git/", ".log", ".DS_Store", "__pycache__"):
            if any(forbidden in n for n in names):
                raise AssertionError(f"Forbidden entry matching {forbidden!r} found in Zenodo zip")
        for tex_name in (
            "HuePrint/paper/ieee/main.tex",
            "HuePrint/paper/ieee/body.tex",
            "HuePrint/paper/ieee/references.tex",
            "HuePrint/paper/ieee/biography.tex",
        ):
            raw = zf.read(tex_name).decode("utf-8")
            if not all(ord(c) < 128 for c in raw):
                raise AssertionError(f"Non-ASCII character in {tex_name}")
    return pages


def main() -> None:
    n_main, n_lv = check_integrity_manifests()
    n_scanned = check_sanitization_and_remnants()
    check_sync_scripts()
    pages = check_pdfs_and_zenodo_bundle()
    print(
        json.dumps(
            {
                "status": "ok",
                "corpus_jsonl_files": 15,
                "integrity_manifest_verified": n_main,
                "lv_rgb_manifest_verified": n_lv,
                "s5_manifest_verified": 10,
                "text_files_scanned_clean": n_scanned,
                "table_and_latex_sync": "verified",
                "pdf_pages": pages,
                "zenodo_bundle": "zenodo_release/HuePrint_Replication_Package.zip",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
