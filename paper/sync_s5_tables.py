"""Synchronize Study S5 competitor benchmark tables and compact EN summary tables from immutable JSON."""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S5_JSON = ROOT / "extensions" / "competitor_benchmark_20261120" / "results" / "s5_results.json"
S3_OVERHEAD = ROOT / "results" / "service_audit" / "overhead.json"
BASE_JSON = ROOT / "results" / "benchmark" / "baseline_results.json"
EXACT_MMD_JSON = ROOT / "results" / "diagnostics" / "exact_mmd_baselines.json"


def _table(headers: list[str], rows: list[list[object]]) -> str:
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        + ["| " + " | ".join(map(str, r)) + " |" for r in rows]
    )


def _pct(v: float) -> str:
    return f"{100.0 * v:.2f}%"


def render_tables(zh: bool = False) -> dict[str, str]:
    s5 = json.loads(S5_JSON.read_text(encoding="utf-8"))
    s3_ov_all = json.loads(S3_OVERHEAD.read_text(encoding="utf-8"))["aggregate"]
    s3_ov = next(x for x in s3_ov_all if x["cohort"] == "S3_color" and x["role"] == "query")

    a = s5["S5a_LLMmap_OpenSet"]
    b = s5["S5b_Gao_LongForm"]
    c = s5["S5c_HuePrint_Anchor"]

    a1_m = a["verification"]["1v1_8calls_mean_3disjoint"]
    a3 = a["verification"]["3v3_24calls_rep012v345"]
    a_ov1 = a["overhead"]["1trace_8calls"]
    a_ov3 = a["overhead"]["3trace_24calls"]

    bh_10 = b["verification_mmd_hamming"]["K5_2v2_10calls_mean20"]
    bh_30 = b["verification_mmd_hamming"]["K10_3v3_30calls"]
    bh_50 = b["verification_mmd_hamming"]["K10_5v5_50calls"]
    bg_10 = b["verification_mmd_4gram"]["K5_2v2_10calls_mean20"]
    bg_30 = b["verification_mmd_4gram"]["K10_3v3_30calls"]
    b_ov10 = b["overhead"]["K5_2v2_10calls"]
    b_ov30 = b["overhead"]["K10_3v3_30calls"]
    b_ov50 = b["overhead"]["K10_5v5_50calls"]

    c_e_fh = c["verification_3v3_30calls"]["first_vs_second_half"]["energy_reg"]
    c_e_oe = c["verification_3v3_30calls"]["odd_vs_even"]["energy_reg"]
    c_ov = c["overhead"]["3v3_30calls"]

    cpu_llmmap_s = a["cpu_scoring_median_ms"] / 1000.0
    cpu_gao_ms = b["cpu_single_pair_median_ms"]

    def usd_pair(ov: dict) -> str:
        return f"{ov['usd_L_median']:.4f} / {ov['usd_G_median']:.4f}"

    # 1. Study S5 Main Head-to-Head Competitor Table
    main_rows = [
        [
            "LLMmap [16] open-set (1v1)",
            8,
            f"{a_ov1['output_tokens_median']:,.1f}",
            usd_pair(a_ov1),
            f"{a1_m['eer_pct']:.2f}% ({a1_m['auc']:.4f})",
            f"{a1_m['within_family_eer_pct']:.2f}%",
            f"{cpu_llmmap_s:.2f} s CPU; 4/8 flagged (95% q1)",
        ],
        [
            "LLMmap [16] open-set (3v3)",
            24,
            f"{a_ov3['output_tokens_median']:,.1f}",
            usd_pair(a_ov3),
            f"{a3['eer_pct']:.2f}% ({a3['auc']:.4f})",
            f"{a3['within_family_eer_pct']:.2f}%",
            f"{3 * cpu_llmmap_s:.1f} s CPU; 2.66× G-USD vs. HP",
        ],
        [
            "Gao [4] Hamming (K=5, 2v2)",
            10,
            f"{b_ov10['output_tokens_median']:,.1f}",
            usd_pair(b_ov10),
            f"{bh_10['eer_pct']:.2f}% ({bh_10['auc']:.4f})",
            f"{bh_10['within_family_eer_pct']:.2f}%",
            f"{cpu_gao_ms:.2f} ms CPU; G-USD match (30c)",
        ],
        [
            "Gao [4] 4-gram (K=5, 2v2)",
            10,
            f"{b_ov10['output_tokens_median']:,.1f}",
            usd_pair(b_ov10),
            f"{bg_10['eer_pct']:.2f}% ({bg_10['auc']:.4f})",
            f"{bg_10['within_family_eer_pct']:.2f}%",
            "G-USD matched; char 4-gram",
        ],
        [
            "Gao [4] Hamming (K=10, 3v3)",
            30,
            f"{b_ov30['output_tokens_median']:,.1f}",
            usd_pair(b_ov30),
            f"{bh_30['eer_pct']:.2f}% ({bh_30['auc']:.4f})",
            f"{bh_30['within_family_eer_pct']:.2f}%",
            "3.28× G-USD, 8.6× tok. vs. HP",
        ],
        [
            "Gao [4] 4-gram (K=10, 3v3)",
            30,
            f"{b_ov30['output_tokens_median']:,.1f}",
            usd_pair(b_ov30),
            f"{bg_30['eer_pct']:.2f}% ({bg_30['auc']:.4f})",
            f"{bg_30['within_family_eer_pct']:.2f}%",
            "0.00% EER at 3.28× G-USD",
        ],
        [
            "Gao [4] Hamming (K=10, 5v5)",
            50,
            f"{b_ov50['output_tokens_median']:,.1f}",
            usd_pair(b_ov50),
            f"{bh_50['eer_pct']:.2f}% ({bh_50['auc']:.4f})",
            f"{bh_50['within_family_eer_pct']:.2f}%",
            r"1.08× S3 G-USD; 10% $p\le0.05$",
        ],
        [
            r"HuePrint S5c $\tilde D_{\mathrm{E-reg}}$ (3v3)",
            30,
            f"{c_ov['output_tokens_median']:,.1f}",
            usd_pair(c_ov),
            f"{c_e_fh['eer_pct']:.2f}% ({c_e_fh['auc']:.4f})",
            f"{c_e_fh['within_family_eer_pct']:.2f}%",
            f"0.12 ms; odd/even {c_e_oe['eer_pct']:.2f}%/{c_e_oe['within_family_eer_pct']:.2f}%",
        ],
        [
            r"HuePrint S3 $\tilde D_{\mathrm{E-reg}}$ (15v15)",
            150,
            f"{s3_ov['output_tokens_median']:,.1f}",
            f"{s3_ov['catalog_scenario_llama33_usd_median']:.4f} / {s3_ov['catalog_scenario_gpt4o_usd_median']:.4f}",
            "0.00% (1.0000)",
            "0.00%",
            "0.31 ms; < Gao 50c G-USD",
        ],
    ]
    main_tbl = _table(
        (
            ["方法与调度", "调用数", "输出 Token", "USD L / G", "全配对 EER (AUC)", "同家族 EER", "本地 CPU 与运行说明"]
            if zh
            else [
                "Method and schedule",
                "Calls",
                "Out. tok.",
                "USD L / G",
                "All-pairs EER (AUC)",
                "Within-fam. EER",
                "Local CPU and operational notes",
            ]
        ),
        main_rows,
    )

    # 2. Study S5 Mixed-Routing Supplement Table
    mixed_rows = []
    for lam in ("0.20", "0.40", "0.50"):
        a1 = a["mixed_routing"]["by_lambda"][lam]["1trace_8calls"]
        a3_m = a["mixed_routing"]["by_lambda"][lam]["3trace_24calls_avg"]
        b3 = b["mixed_routing"]["3v3_30calls"]["by_lambda"][lam]
        b5 = b["mixed_routing"]["5v5_50calls"]["by_lambda"][lam]
        c3 = c["mixed_routing_3v3_30calls"]["by_lambda"][lam]
        for label, calls, blk in [
            ("LLMmap open-set (1v1)", 8, a1),
            ("LLMmap open-set (3v3)", 24, a3_m),
            ("Gao Hamming (3v3)", 30, b3),
            ("Gao Hamming (5v5)", 50, b5),
            (r"HuePrint S5c $\tilde D_{\mathrm{E-reg}}$ (3v3)", 30, c3),
        ]:
            mixed_rows.append([
                lam,
                label,
                calls,
                f"{blk['auc']:.4f}",
                f"{blk['det_at_q95_fpr5_pct']:.2f}%",
                f"{blk['within_family_auc']:.4f}",
                f"{blk['within_family_det_q95_pct']:.2f}%",
            ])
    mixed_tbl = _table(
        (
            [r"$\lambda$", "方法与调度", "调用数", "全配对 AUC", "全配对检出 @ 5% FPR", "同家族 AUC", "同家族检出 @ 5% FPR"]
            if zh
            else [
                r"$\lambda$",
                "Method and schedule",
                "Calls",
                "All-pairs AUC",
                "All-pairs Det. @ 5% FPR",
                "Within-fam. AUC",
                "Within-fam. Det. @ 5% FPR",
            ]
        ),
        mixed_rows,
    )

    # 3. 9-Day OpenRouter Longitudinal Table (S3a -> S5c)
    long_info = c["longitudinal_s3_to_s5c"]
    long_rows = []
    sym_map = {
        "energy_reg": r"$\tilde D_{\mathrm{E-reg}}$",
        "hybrid": r"$D_{\mathrm{hyb}}$",
        "color_mmd_u": "Color MMD-U",
    }
    for split_key, split_label, metrics in [
        ("6v6", "S3a (first 6) → S5c (6)", ["energy_reg", "hybrid", "color_mmd_u"]),
        ("15v6", "S3a (first 15) → S5c (6)", ["energy_reg", "hybrid"]),
    ]:
        for m in metrics:
            x = long_info[split_key][m]
            long_rows.append([
                split_label,
                sym_map[m],
                x["top1_hits"],
                f"{x['auc']:.4f}",
                f"{x['eer_pct']:.2f}%",
                f"{x['within_family_eer_pct']:.2f}%",
            ])
    long_tbl = _table(
        (
            ["迁移路径（间隔 8.59 天）", "指标", "Top-1", "AUC", "全配对 EER", "同家族 EER"]
            if zh
            else ["Transfer (8.59 d elapsed)", "Metric", "Top-1", "AUC", "All-pairs EER", "Within-fam. EER"]
        ),
        long_rows,
    )

    # 4. Compact S3 Parity Summary for Main Manuscript (full 16x9 lives in Supplement K)
    base = json.loads(BASE_JSON.read_text(encoding="utf-8"))["results"]
    exact_mmd = json.loads(EXACT_MMD_JSON.read_text(encoding="utf-8"))["results"]
    E = r"$\tilde D_{\mathrm{E-reg}}$"
    HEX = r"$D_{\mathrm{hex}}$"

    def sel(dataset: str, n: int, metric: str, k: int, cond: str) -> float:
        src = exact_mmd if metric == "string_mmd_u" else base
        rows = [r for r in src if (r["dataset"], r["n_total_per_cell"], r["metric"], r["K"], r["condition"]) == (dataset, n, metric, k, cond)]
        assert rows, (dataset, n, metric, k, cond)
        return statistics.mean(r["eer"] for r in rows)

    s3_compact_rows = []
    for n, dataset, metric, label in [
        (6, "S3_color", "string_mmd_u", "Color MMD-U"),
        (6, "S3_color", "energy_reg", "Color " + E),
        (6, "S3_color", "hex_jsd", "Color " + HEX),
        (6, "S3_word", "string_mmd_u", "Word MMD-U"),
        (6, "S3_word", "word_jsd", "Word JSD"),
        (30, "S3_color", "string_mmd_u", "Color MMD-U"),
        (30, "S3_color", "energy_reg", "Color " + E),
        (30, "S3_color", "hex_jsd", "Color " + HEX),
        (30, "S3_word", "string_mmd_u", "Word MMD-U"),
        (30, "S3_word", "word_jsd", "Word JSD"),
    ]:
        k1 = _pct(sel(dataset, n, metric, 1, "clean"))
        k4 = _pct(sel(dataset, n, metric, 4, "clean"))
        k10 = _pct(sel(dataset, n, metric, 10, "clean"))
        jit = _pct(sel(dataset, n, metric, 10, "jitter8")) if dataset == "S3_color" else "—"
        s3_compact_rows.append([n, label, k1, k4, k10, jit])
    s3_compact_tbl = _table(
        ["N", "探针 / 统计量" if zh else "Probe / stat.", "K=1", "K=4", "K=10", "K=10, ±8"],
        s3_compact_rows,
    )

    return {
        "S5_TABLE_main": main_tbl,
        "S5_TABLE_mixed": mixed_tbl,
        "S5_TABLE_longitudinal": long_tbl,
        "S3_TABLE_compact": s3_compact_tbl,
    }


def sync(check: bool = False) -> None:
    for lang in ("EN", "ZH"):
        paths = [ROOT / "paper" / f"MANUSCRIPT_{lang}.md", ROOT / "paper" / f"SUPPLEMENT_{lang}.md"]
        texts = {p: p.read_text(encoding="utf-8") for p in paths if p.exists()}
        blocks = render_tables(zh=(lang == "ZH"))
        for marker, content in blocks.items():
            pattern = rf"<!-- {marker} -->[\s\S]*?<!-- /{marker} -->"
            owners = [p for p, text in texts.items() if re.search(pattern, text)]
            assert len(owners) == 1, (lang, marker, owners)
            owner = owners[0]
            block = f"<!-- {marker} -->\n{content}\n<!-- /{marker} -->"
            if check:
                assert re.search(pattern, texts[owner])[0] == block, (lang, marker)
            else:
                texts[owner] = re.sub(pattern, lambda _: block, texts[owner])
        if not check:
            for p, text in texts.items():
                p.write_text(text, encoding="utf-8")
    print("Study S5 & compact summary tables verified." if check else "Study S5 & compact summary tables synchronized.")


if __name__ == "__main__":
    sync("--check" in sys.argv)
