#!/usr/bin/env python3
"""Build a desensitized, deterministic Zenodo preprint and replication release bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "zenodo_release"
ARCHIVE_PREFIX = "HuePrint"
NORMALIZED_ZIP_TIME = (2026, 11, 19, 0, 0, 0)

EXCLUDED_TOP_DIRS = {".git", ".venv", "venv", "zenodo_release", "artifacts", "__pycache__"}
EXCLUDED_FILE_NAMES = {".DS_Store", "tectonic"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".pyd", ".log", ".zip", ".tar.gz"}

SENSITIVE_CHECK_PATTERNS = (
    r"/Users/[A-Za-z0-9_.-]+",
    r"/home/[A-Za-z0-9_.-]+",
    r"/private/var/",
    r"gateway\.ai\.cloudflare\.com",
    r"workers\.dev",
    r"cf-aig-authorization",
    r"HTTP-Referer",
    r"sk-[A-Za-z0-9]{20,}",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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


def check_and_clean_tex_logs() -> bool:
    checked_any = False
    for target, expected_pages in (("ieee", 12), ("supplement", 16)):
        log_path = ROOT / "paper" / target / "main.log"
        if log_path.is_file():
            checked_any = True
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            if "Overfull \\hbox" in log_text or "Overfull \\vbox" in log_text:
                raise AssertionError(f"Overfull box detected in paper/{target}/main.log")
            if "Underfull \\vbox" in log_text:
                raise AssertionError(f"Underfull vbox detected in paper/{target}/main.log")
            m = re.search(r"Output written on main\.xdv \((\d+) pages", log_text)
            if not m or int(m.group(1)) != expected_pages:
                raise AssertionError(f"Expected {expected_pages} pages in {target} log, got {m.group(1) if m else 'none'}")
            log_path.unlink()
    return checked_any


def should_include(rel_path: Path) -> bool:
    if not rel_path.parts:
        return False
    if rel_path.parts[0] in EXCLUDED_TOP_DIRS:
        return False
    if any(part == "__pycache__" or part.startswith("._") for part in rel_path.parts):
        return False
    if rel_path.name in EXCLUDED_FILE_NAMES or rel_path.name.startswith("._"):
        return False
    if any(str(rel_path).endswith(suf) for suf in EXCLUDED_SUFFIXES):
        return False
    return True


def iter_release_files() -> list[Path]:
    files = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if should_include(rel):
            files.append(rel)
    return files


def build_replication_zip(zip_path: Path, rel_files: list[Path]) -> dict[str, str]:
    sens_re = re.compile("|".join(SENSITIVE_CHECK_PATTERNS))
    digests: dict[str, str] = {}
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in rel_files:
            src = ROOT / rel
            data = src.read_bytes()
            if rel.name not in {"verify_manuscript.py", "build_zenodo_package.py"} and src.suffix not in {
                ".pdf",
                ".png",
                ".ttf",
                ".ttc",
            }:
                text = data.decode("utf-8", errors="ignore")
                m = sens_re.search(text)
                if m:
                    raise AssertionError(f"Sensitive pattern {m.group(0)!r} found in {rel}")
            arcname = f"{ARCHIVE_PREFIX}/{rel.as_posix()}"
            info = zipfile.ZipInfo(filename=arcname, date_time=NORMALIZED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # Unix
            mode = 0o755 if (src.suffix == ".py" and data.startswith(b"#!")) else 0o644
            info.external_attr = (mode & 0xFFFF) << 16
            info.extra = b""
            info.comment = b""
            zf.writestr(info, data)
            digests[rel.as_posix()] = sha256_bytes(data)
    return digests


def write_upload_guide(out_dir: Path, manifest: dict) -> None:
    meta = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    version = meta["version"]
    is_new_version = not version.startswith("1.")
    upload_entry = (
        f"在已有 Zenodo v1 记录页右侧点击 **New version**（保留原 Concept DOI 并生成 v{version} 版本 DOI），"
        "删除草稿中的旧版文件后拖入以下 4 个新版文件"
        if is_new_version
        else "在 `https://zenodo.org/uploads/new` 直接拖入以下 4 个文件"
    )
    guide = f"""# Zenodo 预印本与复现包上传指南（v{version} Ready-to-Upload）

本目录包含已全部完成脱敏校验、页面排版核验与确定性元数据清理的 Zenodo **v{version}** 提交文件。

## 一、上传文件清单（{upload_entry}）

| 序号 | 文件名 | 页数 / 规模 | 用途说明 |
| :---: | :--- | :---: | :--- |
| 1 | `HuePrint_Preprint.pdf` | 28 页 | **主稿（12 页）+ 补充材料（16 页）完整合订本**——上传后请在文件列表勾选 **Set as default preview**，使读者打开页面即可直接通读全文、定理证明与附表 |
| 2 | `HuePrint_Main_Manuscript.pdf` | 12 页 | 独立英文主稿 PDF（IEEEtran 12 页，0 溢行/溢页） |
| 3 | `HuePrint_Supplementary_Material.pdf` | 16 页 | 独立补充材料 PDF（含中/英/俄/阿四语原始探针与完整证明） |
| 4 | `HuePrint_Replication_Package.zip` | {manifest['replication_zip_files']} 个文件 | 自包含离线复现代码与 12 份只读云端响应语料包（已剔除 `.git`、平台二进制、构建日志、macOS 扩展属性与本地路径） |

> 若希望页面文件列表更极简，也可**仅上传第 1 项 `HuePrint_Preprint.pdf` 与第 4 项 `HuePrint_Replication_Package.zip`**（两份独立 PDF 已同时收录在压缩包 `HuePrint/paper/` 内）。

## 二、Zenodo 表单核心字段填写对照（与根目录 `.zenodo.json` 完全一致）

- **Resource type**: `Publication` → `Preprint`
- **Title**: `{meta['title']}`
- **Creators**:
  - Family name: `He` / Given names: `Xiguan`
  - Affiliation: `College of Information, Yunnan University of Chinese Medicine`
- **Publication date**: `{meta['publication_date']}`
- **Version**: `{version}`
- **Language**: `English`
- **License**: `Creative Commons Attribution 4.0 International (CC-BY-4.0)`（在 Notes 中已注明代码部分同时遵循 MIT License）
- **Keywords**: `{", ".join(meta['keywords'])}`
- **Description**: 可直接复制根目录 `.zenodo.json` 中的 `description` 字段内容（已包含 v{version} 更新摘要）
- **Visibility**: `Public`

## 三、SHA-256 校验摘要

- `HuePrint_Preprint.pdf`: `{manifest['artifacts']['HuePrint_Preprint.pdf']['sha256']}`
- `HuePrint_Main_Manuscript.pdf`: `{manifest['artifacts']['HuePrint_Main_Manuscript.pdf']['sha256']}`
- `HuePrint_Supplementary_Material.pdf`: `{manifest['artifacts']['HuePrint_Supplementary_Material.pdf']['sha256']}`
- `HuePrint_Replication_Package.zip`: `{manifest['artifacts']['HuePrint_Replication_Package.zip']['sha256']}`
"""
    (out_dir / "ZENODO_UPLOAD_GUIDE.md").write_text(guide, encoding="utf-8")


def build_package(out_dir: Path) -> dict:
    main_pdf = ROOT / "paper" / "ieee" / "main.pdf"
    supp_pdf = ROOT / "paper" / "supplement" / "main.pdf"
    if not main_pdf.is_file() or not supp_pdf.is_file():
        raise FileNotFoundError("Missing compiled paper/ieee/main.pdf or paper/supplement/main.pdf")

    logs_checked = check_and_clean_tex_logs()

    main_pages = pdf_page_count(main_pdf)
    supp_pages = pdf_page_count(supp_pdf)
    if main_pages != 12 or supp_pages != 16:
        raise AssertionError(f"Unexpected page counts: main={main_pages}, supplement={supp_pages}")

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_main = out_dir / "HuePrint_Main_Manuscript.pdf"
    out_supp = out_dir / "HuePrint_Supplementary_Material.pdf"
    out_combined = out_dir / "HuePrint_Preprint.pdf"
    out_zip = out_dir / "HuePrint_Replication_Package.zip"

    shutil.copy2(main_pdf, out_main)
    shutil.copy2(supp_pdf, out_supp)

    pdfunite = shutil.which("pdfunite")
    if not pdfunite:
        raise RuntimeError("pdfunite is required to merge main and supplementary PDFs losslessly")
    subprocess.run([pdfunite, str(main_pdf), str(supp_pdf), str(out_combined)], check=True)
    combined_pages = pdf_page_count(out_combined)
    if combined_pages != main_pages + supp_pages:
        raise AssertionError(f"Merged PDF has {combined_pages} pages, expected {main_pages + supp_pages}")

    rel_files = iter_release_files()
    archived_digests = build_replication_zip(out_zip, rel_files)

    xattr_bin = shutil.which("xattr")
    if xattr_bin:
        subprocess.run([xattr_bin, "-cr", str(out_dir)], check=False)

    meta = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    manifest = {
        "version": meta["version"],
        "publication_date": meta["publication_date"],
        "bundle_dir": out_dir.relative_to(ROOT).as_posix() if out_dir.is_relative_to(ROOT) else str(out_dir),
        "tex_logs_checked_and_cleaned": logs_checked,
        "pages": {
            "main_manuscript": main_pages,
            "supplementary_material": supp_pages,
            "combined_preprint": combined_pages,
        },
        "artifacts": {
            name: {
                "bytes": (out_dir / name).stat().st_size,
                "sha256": sha256_file(out_dir / name),
            }
            for name in (
                "HuePrint_Preprint.pdf",
                "HuePrint_Main_Manuscript.pdf",
                "HuePrint_Supplementary_Material.pdf",
                "HuePrint_Replication_Package.zip",
            )
        },
        "replication_zip_prefix": ARCHIVE_PREFIX,
        "replication_zip_files": len(archived_digests),
    }
    write_upload_guide(out_dir, manifest)
    (out_dir / "zenodo_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    manifest = build_package(args.out_dir.resolve())
    print(
        f"Built Zenodo release -> {manifest['bundle_dir']} "
        f"(combined={manifest['pages']['combined_preprint']}p, zip_files={manifest['replication_zip_files']})"
    )


if __name__ == "__main__":
    main()
