#!/usr/bin/env python3
"""
Standalone OpenRouter Collector for Study S5 (Competitor Benchmark).

Collects three matched arms on the exact 20-model S3 OpenRouter cohort in one session:
  - s5a_llmmap          : LLMmap (USENIX Security 2025) official 8 open-set queries x 6 reps = 960 calls
  - s5b_gao_longform    : Gao et al. (ICLR 2025) official continuation prompts x 10 reps = 2,000 calls
  - s5c_hueprint_anchor : HuePrint 10 English probes (identical to Study S3) x 6 reps = 1,200 calls

Design invariants:
  - Reads OPENROUTER_API_KEY strictly from environment; never logs or writes secrets.
  - Resume-safe by unique trial_key.
  - Records HTTP 400/403 provider moderation/safety blocks cleanly without attempting to bypass them.
  - Does not modify any file outside extensions/competitor_benchmark_20261120/.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import random
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from collect import _extract_completion, parse_color_response  # noqa: E402

TARGETS_PATH = ROOT / "extensions" / "live_validation_20261111" / "configs" / "targets.s3_20models_locked64.json"
S5_PROMPTS_PATH = EXT_DIR / "configs" / "prompts_s5_competitors.json"
HUEPRINT_PROMPTS_PATH = ROOT / "config" / "prompts.json"
DATA_DIR = EXT_DIR / "data"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _sync_post(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = {"raw_error": err_body[:500]}
        return e.code, err_json


def _is_moderation_or_policy_block(status: int, err_obj: dict[str, Any]) -> bool:
    inner_code = None
    if isinstance(err_obj, dict) and isinstance(err_obj.get("error"), dict):
        inner_code = err_obj["error"].get("code")
    eff_status = inner_code if isinstance(inner_code, int) else status
    if eff_status not in (400, 403, 422, 451):
        return False
    blob = json.dumps(err_obj, ensure_ascii=False).lower()
    keywords = (
        "moderation",
        "flagged",
        "safety",
        "policy",
        "content_filter",
        "harmful",
        "prohibited",
        "blocked",
        "violat",
    )
    return any(k in blob for k in keywords) or eff_status in (403, 451)


def _build_payload(
    target: dict[str, Any],
    system_prompt: str | None,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    extra_decoding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload: dict[str, Any] = {
        "model": target["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_decoding:
        for k, v in extra_decoding.items():
            if v is not None:
                payload[k] = v

    reasoning_mode = target.get("reasoning_mode", "disabled")
    if reasoning_mode == "disabled":
        payload["reasoning"] = {"enabled": False}
    if target.get("extra_body"):
        payload.update(target["extra_body"])
    return payload


def _build_jobs(arm: str, targets: list[dict[str, Any]], s5_cfg: dict[str, Any], hp_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    if arm == "s5a_llmmap":
        cfg = s5_cfg["s5a_llmmap"]
        for rep in range(int(cfg["reps"])):
            for p in cfg["prompts"]:
                for t in targets:
                    jobs.append({
                        "arm": arm,
                        "trial_key": f"{arm}|{t['id']}|{p['prompt_id']}|rep{rep}",
                        "target": t,
                        "prompt_id": p["prompt_id"],
                        "category": p["category"],
                        "format": "llmmap_text",
                        "system_prompt": cfg["system_prompt"],
                        "user_prompt": p["text"],
                        "temperature": float(cfg["temperature"]),
                        "max_tokens": int(cfg["max_tokens"]),
                        "extra_decoding": None,
                        "rep": rep,
                    })
    elif arm == "s5b_gao_longform":
        cfg = s5_cfg["s5b_gao_longform"]
        extra_dec = {
            "top_p": cfg.get("top_p", 1.0),
            "frequency_penalty": cfg.get("frequency_penalty", 0.0),
            "presence_penalty": cfg.get("presence_penalty", 0.0),
        }
        for rep in range(int(cfg["reps"])):
            for p in cfg["prompts"]:
                for t in targets:
                    jobs.append({
                        "arm": arm,
                        "trial_key": f"{arm}|{t['id']}|{p['prompt_id']}|rep{rep}",
                        "target": t,
                        "prompt_id": p["prompt_id"],
                        "category": p["topic"],
                        "format": "gao_continuation",
                        "system_prompt": cfg["system_prompt"],
                        "user_prompt": p["text"],
                        "temperature": float(cfg["temperature"]),
                        "max_tokens": int(cfg["max_tokens"]),
                        "extra_decoding": extra_dec,
                        "rep": rep,
                    })
    elif arm == "s5c_hueprint_anchor":
        cfg = s5_cfg["s5c_hueprint_anchor"]
        sys_prompts = hp_cfg["system_prompts"]
        tasks = hp_cfg["tasks"]
        for rep in range(int(cfg["reps"])):
            for task_id in cfg["tasks"]:
                tinfo = tasks[task_id]
                fmt = tinfo["format"]
                for t in targets:
                    jobs.append({
                        "arm": arm,
                        "trial_key": f"{arm}|{t['id']}|{task_id}|en|T1.0|rep{rep}",
                        "target": t,
                        "prompt_id": task_id,
                        "category": tinfo["condition"],
                        "format": fmt,
                        "system_prompt": sys_prompts[fmt]["en"],
                        "user_prompt": tinfo["prompts"]["en"],
                        "temperature": float(cfg["temperature"]),
                        "max_tokens": int(cfg["max_tokens"]),
                        "extra_decoding": None,
                        "rep": rep,
                    })
    else:
        raise ValueError(f"Unknown arm: {arm}")
    return jobs


async def _run_job(
    job: dict[str, Any],
    api_key: str,
    timeout: float,
    max_retries: int,
) -> dict[str, Any]:
    target = job["target"]
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (compatible; OpenAI-Python/1.50)",
    }
    payload = _build_payload(
        target=target,
        system_prompt=job["system_prompt"],
        user_prompt=job["user_prompt"],
        temperature=job["temperature"],
        max_tokens=job["max_tokens"],
        extra_decoding=job["extra_decoding"],
    )

    last_err = ""
    last_status = 0
    for attempt in range(max_retries):
        t0 = time.perf_counter()
        try:
            status, data = await asyncio.to_thread(_sync_post, OPENROUTER_URL, headers, payload, timeout)
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            last_status = 0
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < max_retries:
                await asyncio.sleep(min(20.0, 1.5 * (2 ** attempt) + random.uniform(0.1, 0.7)))
                continue
            return _make_error_record(job, last_status, latency_ms, last_err, blocked=False)

        if status == 200 and isinstance(data, dict) and "error" not in data:
            ext = _extract_completion(data, target["model"], target["id"])
            rec: dict[str, Any] = {
                "trial_key": job["trial_key"],
                "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "arm": job["arm"],
                "target_id": target["id"],
                "family": target["family"],
                "claimed_model": target["model"],
                "reported_model": ext["reported_model"],
                "provider": ext["provider"],
                "prompt_id": job["prompt_id"],
                "category": job["category"],
                "format": job["format"],
                "lang": "en",
                "temperature": job["temperature"],
                "max_tokens": job["max_tokens"],
                "rep": job["rep"],
                "http_status": status,
                "blocked_by_moderation": False,
                "error_message": None,
                "latency_ms": latency_ms,
                "response_id": ext["response_id"],
                "finish_reason": ext["finish_reason"],
                "usage": ext["usage"],
                "raw_text": ext["raw_text"],
                "explicit_reasoning": ext["explicit_reasoning"],
            }
            if job["arm"] == "s5c_hueprint_anchor":
                rec["task_id"] = job["prompt_id"]
                rec["condition"] = job["category"]
                rec["parsed"] = parse_color_response(ext["raw_text"], job["format"], ext["explicit_reasoning"])
            return rec

        # Some providers reject frequency_penalty / presence_penalty (400 invalid param); fall back cleanly once.
        err_blob = json.dumps(data, ensure_ascii=False)[:500]
        if status == 400 and job["arm"] == "s5b_gao_longform" and (
            "frequency_penalty" in err_blob.lower() or "presence_penalty" in err_blob.lower() or "penalty" in err_blob.lower()
        ):
            payload.pop("frequency_penalty", None)
            payload.pop("presence_penalty", None)
            continue

        # Moderation / policy block: record transparently, never bypass or retry
        if _is_moderation_or_policy_block(status, data if isinstance(data, dict) else {"raw": err_blob}):
            return _make_error_record(job, status, latency_ms, err_blob, blocked=True)

        # Transient error (429 / 5xx / embedded OpenRouter error)
        last_status = status
        last_err = err_blob
        if attempt + 1 < max_retries:
            backoff = min(25.0, 2.0 * (2 ** attempt) + random.uniform(0.2, 1.0))
            await asyncio.sleep(backoff)
            continue
        return _make_error_record(job, last_status, latency_ms, last_err, blocked=False)

    return _make_error_record(job, last_status, 0.0, last_err, blocked=False)


def _make_error_record(job: dict[str, Any], status: int, latency_ms: float, err_msg: str, blocked: bool) -> dict[str, Any]:
    target = job["target"]
    rec: dict[str, Any] = {
        "trial_key": job["trial_key"],
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "arm": job["arm"],
        "target_id": target["id"],
        "family": target["family"],
        "claimed_model": target["model"],
        "reported_model": None,
        "provider": None,
        "prompt_id": job["prompt_id"],
        "category": job["category"],
        "format": job["format"],
        "lang": "en",
        "temperature": job["temperature"],
        "max_tokens": job["max_tokens"],
        "rep": job["rep"],
        "http_status": status,
        "blocked_by_moderation": blocked,
        "error_message": err_msg[:400],
        "latency_ms": latency_ms,
        "response_id": None,
        "finish_reason": "moderation_block" if blocked else "api_error",
        "usage": {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "cached_tokens": 0, "neurons": None},
        "raw_text": "",
        "explicit_reasoning": "",
    }
    if job["arm"] == "s5c_hueprint_anchor":
        rec["task_id"] = job["prompt_id"]
        rec["condition"] = job["category"]
        rec["parsed"] = parse_color_response("", job["format"], "")
    return rec


async def run_arm(arm: str, concurrency: int, timeout: float, max_retries: int, retry_errors: bool) -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is required.")

    targets = json.loads(TARGETS_PATH.read_text(encoding="utf-8"))["targets"]
    s5_cfg = json.loads(S5_PROMPTS_PATH.read_text(encoding="utf-8"))
    hp_cfg = json.loads(HUEPRINT_PROMPTS_PATH.read_text(encoding="utf-8"))
    jobs = _build_jobs(arm, targets, s5_cfg, hp_cfg)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"{arm}.jsonl"

    done_keys: set[str] = set()
    if out_path.is_file():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if retry_errors and r.get("http_status") != 200 and not r.get("blocked_by_moderation"):
                continue
            done_keys.add(r["trial_key"])

    pending = [j for j in jobs if j["trial_key"] not in done_keys]
    print(f"[{arm}] total={len(jobs)} done={len(done_keys)} pending={len(pending)} concurrency={concurrency}", flush=True)
    if not pending:
        return

    sem = asyncio.Semaphore(concurrency)
    write_lock = asyncio.Lock()
    stats = {"ok": 0, "blocked": 0, "err": 0}
    t_start = time.perf_counter()

    async def worker(job: dict[str, Any]) -> None:
        async with sem:
            rec = await _run_job(job, api_key=api_key, timeout=timeout, max_retries=max_retries)
        async with write_lock:
            with out_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec["http_status"] == 200:
                stats["ok"] += 1
            elif rec["blocked_by_moderation"]:
                stats["blocked"] += 1
            else:
                stats["err"] += 1
            done = stats["ok"] + stats["blocked"] + stats["err"]
            if done % 100 == 0 or done == len(pending):
                elapsed = time.perf_counter() - t_start
                print(
                    f"[{arm}] {done}/{len(pending)} ok={stats['ok']} blocked={stats['blocked']} err={stats['err']} ({elapsed:.1f}s)",
                    flush=True,
                )

    # Interleave targets by keeping rep outer-loop order (already interleaved across targets)
    await asyncio.gather(*(worker(j) for j in pending))

    # Deduplicate cleanly if --retry-errors appended replacement rows (keep latest per trial_key)
    if retry_errors and out_path.is_file():
        latest: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            k = r["trial_key"]
            if k not in latest:
                order.append(k)
            latest[k] = r
        with out_path.open("w", encoding="utf-8") as f:
            for k in order:
                f.write(json.dumps(latest[k], ensure_ascii=False) + "\n")
        print(f"[{arm}] compacted to {len(order)} unique trials.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Study S5 OpenRouter Competitor Benchmark Collector")
    parser.add_argument(
        "--arm",
        choices=["s5a_llmmap", "s5b_gao_longform", "s5c_hueprint_anchor", "all"],
        default="all",
    )
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()

    arms = ["s5a_llmmap", "s5b_gao_longform", "s5c_hueprint_anchor"] if args.arm == "all" else [args.arm]
    for arm in arms:
        asyncio.run(run_arm(arm, args.concurrency, args.timeout, args.max_retries, args.retry_errors))


if __name__ == "__main__":
    main()
