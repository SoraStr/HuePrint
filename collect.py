#!/usr/bin/env python3
"""
Batch RGB/Hex LLM Fingerprinting Data Collector.

Supported protocols (--protocol):
  1. cc / chat-completions / openai : OpenAI-compatible POST /v1/chat/completions
  2. anthropic-messages / messages  : Anthropic POST /v1/messages
  3. claude-code / cc-anthropic     : Claude Code style POST /v1/messages (with Claude Code system header/beta)
  4. claude-cli                     : Local `claude -p` CLI subprocess invocation
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import math
import os
import random
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import unicodedata

THINK_TAG_RE = re.compile(r"<(think|thinking|reasoning)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
THINK_CLOSE_RE = re.compile(r"^(.*?)</(think|thinking|reasoning)>\s*(.*)$", re.DOTALL | re.IGNORECASE)
THINK_UNCLOSED_RE = re.compile(r"<(think|thinking|reasoning)>(.*)$", re.DOTALL | re.IGNORECASE)
HEX_RE = re.compile(r"(?<![0-9a-zA-Z#])(#?)([0-9a-fA-F]{6})(?![0-9a-zA-Z])")
RGB_STRICT_3_RE = re.compile(r"^(\d{1,3})(\s*,\s*)(\d{1,3})(\s*,\s*)(\d{1,3})$")
SINGLE_WORD_RE = re.compile(r"^[\w\u4e00-\u9fff\u0400-\u04ff\u0600-\u06ff]+$")
REFUSAL_RE = re.compile(
    r"\b(cannot|can't|sorry|unable|as an ai|i don't have personal preferences)\b"
    r"|(抱歉|无法|作为人工智能|没有个人偏好)",
    re.IGNORECASE,
)

def parse_color_response(
    raw_text: str,
    expected_format: str,
    explicit_reasoning: str = "",
) -> dict[str, Any]:
    """Normalize raw completion into canonical RGB integers + syntactic & CoT side-channels."""
    raw_text = raw_text or ""
    reasoning_parts: list[str] = [explicit_reasoning] if explicit_reasoning else []

    def _collect_think(m: re.Match[str]) -> str:
        reasoning_parts.append(m.group(2).strip())
        return " "

    visible = THINK_TAG_RE.sub(_collect_think, raw_text).strip()
    m_close = THINK_CLOSE_RE.match(visible)
    if m_close:
        reasoning_parts.append(m_close.group(1).strip())
        visible = m_close.group(3).strip()
    m_unclosed = THINK_UNCLOSED_RE.search(visible)
    if m_unclosed:
        reasoning_parts.append(m_unclosed.group(2).strip())
        visible = visible[:m_unclosed.start()].strip()
    reasoning_text = "\n".join(p for p in reasoning_parts if p).strip()
    first_think_word = None
    if reasoning_text:
        tokens = re.findall(r"[\w\u4e00-\u9fff\u0400-\u04ff\u0600-\u06ff]+", reasoning_text)
        if tokens:
            first_think_word = tokens[0].lower()

    base = {
        "parser_version": "3.0",
        "visible_text": visible,
        "has_reasoning_trace": bool(reasoning_text),
        "reasoning_char_len": len(reasoning_text),
        "first_think_word": first_think_word,
        "status": "invalid",
        "rgb": None,
        "voxel_bin_8": None,
        "canonical_hex": None,
        "syntax": None,
    }

    if not visible:
        base["status"] = "empty"
        return base

    if expected_format == "single_word":
        if REFUSAL_RE.search(visible):
            base["status"] = "refusal"
            return base
        raw_clean = unicodedata.normalize("NFKC", visible).strip()
        strict_tok = bool(SINGLE_WORD_RE.fullmatch(raw_clean))
        cleaned = raw_clean.strip("`'\"").rstrip(".").strip().lower()
        if SINGLE_WORD_RE.fullmatch(cleaned):
            base.update({
                "status": "valid",
                "canonical_hex": cleaned,
                "voxel_bin_8": cleaned,
                "rgb": [0, 0, 0],
                "syntax": {"strict_single_token_format": strict_tok},
            })
            return base
    elif expected_format == "hex":
        for m in HEX_RE.finditer(visible):
            has_hash = (m.group(1) == "#")
            hex_digits = m.group(2)
            # Without an explicit '#', reject pure alphabetic 6-letter words (e.g. 'facade', 'beaded', 'coffee')
            if not has_hash and not any(c.isdigit() for c in hex_digits):
                continue
            full_match = m.group(0)
            r = int(hex_digits[0:2], 16)
            g = int(hex_digits[2:4], 16)
            b = int(hex_digits[4:6], 16)
            letters = [c for c in hex_digits if c.isalpha()]
            if not letters:
                case_style = "numeric_only"
            elif all(c.isupper() for c in letters):
                case_style = "upper"
            elif all(c.islower() for c in letters):
                case_style = "lower"
            else:
                case_style = "mixed"
            is_websafe = (
                hex_digits[0].lower() == hex_digits[1].lower()
                and hex_digits[2].lower() == hex_digits[3].lower()
                and hex_digits[4].lower() == hex_digits[5].lower()
            )
            StrictSingle = (visible.strip().strip("`'\".") == full_match)
            base.update({
                "status": "valid",
                "rgb": [r, g, b],
                "voxel_bin_8": f"{r // 32}_{g // 32}_{b // 32}",
                "canonical_hex": f"#{hex_digits.upper()}",
                "syntax": {
                    "has_hash": has_hash,
                    "letter_case": case_style,
                    "is_websafe_pair": is_websafe,
                    "strict_single_token_format": StrictSingle,
                },
            })
            return base

    elif expected_format == "rgb_triplet":
        raw_strip = visible.strip()
        strict_tok = bool(RGB_STRICT_3_RE.fullmatch(raw_strip))
        cleaned = raw_strip.strip("`'\"").rstrip(".").strip()
        if (cleaned.startswith("(") and cleaned.endswith(")")) or (cleaned.startswith("[") and cleaned.endswith("]")):
            cleaned = cleaned[1:-1].strip()
        m = RGB_STRICT_3_RE.fullmatch(cleaned)
        if m:
            r, sep1, g, sep2, b = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4), int(m.group(5))
            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                base.update({
                    "status": "valid",
                    "rgb": [r, g, b],
                    "voxel_bin_8": f"{r // 32}_{g // 32}_{b // 32}",
                    "canonical_hex": f"#{r:02X}{g:02X}{b:02X}",
                    "syntax": {
                        "space_after_comma": (" " in sep1) or (" " in sep2),
                        "strict_single_token_format": strict_tok,
                    },
                })
                return base
    if REFUSAL_RE.search(visible):
        base["status"] = "refusal"
    return base


def normalize_protocol(proto: str) -> str:
    p = proto.strip().lower().replace("_", "-")
    if p in ("cc", "chat-completions", "openai", "openai-cc"):
        return "cc"
    if p in ("anthropic", "anthropic-messages", "messages"):
        return "anthropic-messages"
    if p in ("claude-code", "cc-anthropic", "claude-code-messages"):
        return "claude-code"
    if p in ("claude-cli", "cc-cli"):
        return "claude-cli"
    if p in ("cloudflare", "cf", "workers-ai", "cloudflare-rest"):
        return "cloudflare"
    if p in ("cloudflare-gateway", "cf-gateway", "cf-ai-v1", "ai-gateway"):
        return "cloudflare-gateway"
    raise ValueError(f"Unsupported protocol: {proto}")


def _resolve_account_id(account_id: str) -> str:
    raw = (account_id or "").strip()
    if raw.startswith("${") and raw.endswith("}"):
        env_key = raw[2:-1].strip()
        raw = os.environ.get(env_key, "") if env_key else ""
    elif raw.startswith("$") and len(raw) > 1:
        raw = os.environ.get(raw[1:].strip(), "")
    return raw or os.environ.get("CF_ACCOUNT_ID") or os.environ.get("CLOUDFLARE_ACCOUNT_ID") or ""


def build_endpoint_url(base_url: str, protocol: str, model: str = "", account_id: str = "") -> str:
    base = base_url.rstrip("/")
    if protocol == "cloudflare":
        if "/ai/run/" in base:
            return base
        if base.endswith("/ai/run"):
            return f"{base}/{model}"
        acc = _resolve_account_id(account_id)
        if "/accounts/" in base:
            return f"{base}/ai/run/{model}"
        if not acc:
            raise ValueError("Cloudflare protocol requires account_id (or CF_ACCOUNT_ID env)")
        return f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{model}"
    if protocol == "cloudflare-gateway":
        if base.endswith("/messages") or base.endswith("/chat/completions"):
            return base
        if "/ai/v1" in base:
            return f"{base}/messages"
        if "/accounts/" in base:
            return f"{base}/ai/v1/messages"
        acc = _resolve_account_id(account_id)
        if not acc:
            raise ValueError("Cloudflare gateway protocol requires account_id (or CF_ACCOUNT_ID env)")
        return f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/v1/messages"
    if protocol == "cc":
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"
    else:
        if base.endswith("/messages"):
            return base
        if base.endswith("/v1"):
            return f"{base}/messages"
        return f"{base}/v1/messages"

def _sync_http_post(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> tuple[int, dict[str, Any]]:
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
            err_json = {"raw_error": err_body}
        return e.code, err_json


async def call_model_api(
    target: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    timeout: float,
) -> dict[str, Any]:
    protocol = normalize_protocol(target["protocol"])
    model = target["model"]
    max_tokens = int(target.get("max_tokens", 16))
    reasoning_mode = target.get("reasoning_mode", "disabled")

    if protocol == "claude-cli":
        t0 = time.perf_counter()
        cmd = [
            "claude", "-p",
            "--model", model,
            "--system-prompt", system_prompt,
            "--output-format", "json",
            user_prompt,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI exited {proc.returncode}: {stderr.decode('utf-8', 'replace')}")
        out_str = stdout.decode("utf-8", "replace").strip()
        try:
            data = json.loads(out_str)
            text = data.get("result", out_str)
        except Exception:
            data = {}
            text = out_str
        return {
            "raw_text": text,
            "explicit_reasoning": "",
            "finish_reason": data.get("stop_reason") if isinstance(data, dict) else None,
            "reported_model": data.get("model", model) if isinstance(data, dict) else model,
            "provider": "claude-cli",
            "response_id": data.get("id") if isinstance(data, dict) else None,
            "temperature_sent": None,
            "latency_ms": latency_ms,
            "usage": data.get("usage", {}) if isinstance(data, dict) else {},
        }
    api_key = target.get("api_key") or os.environ.get(target.get("api_key_env", ""), "")
    if not api_key:
        for fallback_env in ("CF_API_TOKEN", "CLOUDFLARE_API_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "API_KEY"):
            if os.environ.get(fallback_env):
                api_key = os.environ[fallback_env]
                break

    url = build_endpoint_url(
        target.get("base_url", "https://api.cloudflare.com/client/v4"),
        protocol,
        model=model,
        account_id=target.get("account_id", ""),
    )
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; OpenAI-Python/1.50)",
    }
    temp_sent: float | None = temperature
    if protocol == "cloudflare-gateway":
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens,
        }
        if target.get("send_temperature", False):
            payload["temperature"] = temperature
        else:
            temp_sent = None
        if reasoning_mode in ("low", "medium", "high") and target.get("send_thinking", False):
            payload["thinking"] = {"type": "enabled", "budget_tokens": int(target.get("thinking_budget", 1024))}
    elif protocol in ("cc", "cloudflare"):
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload: dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if protocol == "cc":
            payload["model"] = model
        if reasoning_mode in ("low", "medium", "high"):
            payload["reasoning_effort"] = reasoning_mode
        elif reasoning_mode == "disabled":
            if "openrouter.ai" in url:
                payload["reasoning"] = {"enabled": False}
            elif protocol == "cloudflare" and any(k in model.lower() for k in ("qwen3", "glm-4.7")):
                payload["chat_template_kwargs"] = {"enable_thinking": False}
    else:
        auth_mode = target.get("auth_mode", "auto")
        if api_key:
            if auth_mode == "bearer" or protocol == "claude-code":
                headers["Authorization"] = f"Bearer {api_key}"
                headers["x-api-key"] = api_key
            else:
                headers["x-api-key"] = api_key
        headers["anthropic-version"] = target.get("anthropic_version", "2023-06-01")

        system_field: Any = system_prompt
        if protocol == "claude-code":
            headers["anthropic-beta"] = "claude-code-20250219"
            headers["User-Agent"] = "claude-cli/1.0.0 (external, cli)"
            system_field = [
                {"type": "text", "text": "You are Claude Code, Anthropic's official CLI for Claude."},
                {"type": "text", "text": system_prompt},
            ]

        payload = {
            "model": model,
            "system": system_field,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if reasoning_mode in ("low", "medium", "high"):
            budget_map = {"low": 1024, "medium": 2048, "high": 4096}
            budget = int(target.get("thinking_budget", budget_map[reasoning_mode]))
            payload["thinking"] = {"type": "enabled", "budget_tokens": budget}
            payload["temperature"] = 1.0  # Anthropic thinking requires T=1.0
            if payload["max_tokens"] <= budget:
                payload["max_tokens"] = budget + 64

    if target.get("extra_headers"):
        headers.update(target["extra_headers"])
    if target.get("extra_body"):
        payload.update(target["extra_body"])

    # Read temperature_sent from final payload after all thinking/extra_body overrides
    temp_sent = payload.get("temperature", None)

    t0 = time.perf_counter()
    status, data = await asyncio.to_thread(_sync_http_post, url, headers, payload, timeout)
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    if status >= 400:
        raise RuntimeError(f"HTTP {status}: {json.dumps(data, ensure_ascii=False)[:400]}")

    extracted = _extract_completion(data, model, target.get("id", protocol))
    return {
        "raw_text": extracted["raw_text"],
        "explicit_reasoning": extracted["explicit_reasoning"],
        "finish_reason": extracted["finish_reason"],
        "reported_model": extracted["reported_model"],
        "provider": extracted["provider"] if protocol != "cloudflare" else "cloudflare-workers-ai",
        "response_id": extracted["response_id"],
        "temperature_sent": temp_sent,
        "latency_ms": latency_ms,
        "usage": extracted["usage"],
    }

def _extract_completion(data: Any, fallback_model: str, fallback_provider: str) -> dict[str, Any]:
    """Normalize OpenAI, Anthropic, and Cloudflare-native response envelopes alike."""
    res_obj = data.get("result") if isinstance(data, dict) and isinstance(data.get("result"), dict) else data
    raw_text = ""
    explicit_reasoning = ""
    finish_reason = res_obj.get("stop_reason") or res_obj.get("finish_reason")
    choices = res_obj.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        raw_text = msg.get("content") or ""
        explicit_reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        finish_reason = choices[0].get("finish_reason") or finish_reason
        if not raw_text and explicit_reasoning and len(explicit_reasoning.strip()) <= 24:
            raw_text = explicit_reasoning
            explicit_reasoning = ""
    elif isinstance(res_obj.get("content"), list):
        text_parts: list[str] = []
        think_parts: list[str] = []
        for blk in res_obj["content"]:
            if not isinstance(blk, dict):
                continue
            btype = blk.get("type")
            if btype == "text":
                text_parts.append(blk.get("text", ""))
            elif btype in ("thinking", "redacted_thinking"):
                think_parts.append(blk.get("thinking", ""))
        raw_text = "".join(text_parts)
        explicit_reasoning = "\n".join(think_parts)
    else:
        raw_text = res_obj.get("response") or ""
    usage = res_obj.get("usage") or {}
    prompt_details = usage.get("prompt_tokens_details") or {}
    comp_details = usage.get("completion_tokens_details") or {}
    if "prompt_tokens" in usage:
        usage_norm = {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": comp_details.get("reasoning_tokens", 0),
            "cached_tokens": prompt_details.get("cached_tokens", 0),
            "neurons": usage.get("neurons"),
        }
    else:
        usage_norm = {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "reasoning_tokens": None,
            "cached_tokens": usage.get("cache_read_input_tokens", 0),
            "neurons": usage.get("neurons"),
        }

    return {
        "raw_text": raw_text,
        "explicit_reasoning": explicit_reasoning,
        "finish_reason": finish_reason,
        "reported_model": res_obj.get("model") or fallback_model,
        "provider": res_obj.get("provider") or fallback_provider,
        "response_id": res_obj.get("id"),
        "usage": usage_norm,
    }


def load_completed_keys(out_path: Path) -> set[str]:
    done: set[str] = set()
    if not out_path.exists():
        return done
    with out_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if "trial_key" in row and not row.get("error"):
                    done.add(row["trial_key"])
            except Exception:
                continue
    return done


def build_schedule(
    battery: dict[str, Any],
    targets: list[dict[str, Any]],
    reps_t1: int,
    reps_t0: int,
    languages: list[str],
    tasks: list[str],
    seed: int,
    completed: set[str],
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for target in targets:
        target_id = target.get("id") or f"{target['protocol']}:{target['model']}"
        for task_id in tasks:
            task_cfg = battery["tasks"][task_id]
            fmt = task_cfg["format"]
            for lang in languages:
                sys_prompt = battery["system_prompts"][fmt][lang]
                usr_prompt = task_cfg["prompts"][lang]
                for temp, reps in ((1.0, reps_t1), (0.0, reps_t0)):
                    for rep in range(1, reps + 1):
                        t_key = f"{target_id}|{task_id}|{lang}|T{temp:.1f}|r{rep}"
                        if t_key in completed:
                            continue
                        jobs.append({
                            "trial_key": t_key,
                            "target": target,
                            "target_id": target_id,
                            "task_id": task_id,
                            "format": fmt,
                            "condition": task_cfg["condition"],
                            "lang": lang,
                            "temperature": temp,
                            "rep": rep,
                            "parity": "odd" if (rep % 2 == 1) else "even",
                            "system_prompt": sys_prompt,
                            "user_prompt": usr_prompt,
                        })
    rng = random.Random(seed)
    rng.shuffle(jobs)
    return jobs


async def run_collection(args: argparse.Namespace) -> int:
    battery = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    if args.targets_config:
        cfg = json.loads(Path(args.targets_config).read_text(encoding="utf-8"))
        targets = cfg["targets"] if isinstance(cfg, dict) and "targets" in cfg else cfg
    else:
        if not args.model:
            raise ValueError("Must specify --model or --targets-config")
        targets = [{
            "id": args.target_id or f"{args.protocol}:{args.model}",
            "protocol": args.protocol,
            "base_url": args.base_url,
            "account_id": args.cf_account_id,
            "api_key": args.api_key,
            "api_key_env": args.api_key_env,
            "model": args.model,
            "max_tokens": args.max_tokens,
            "reasoning_mode": args.reasoning_mode,
        }]

    languages = [x.strip() for x in args.languages.split(",") if x.strip()] if args.languages else battery["languages"]
    tasks = [x.strip() for x in args.tasks.split(",") if x.strip()] if args.tasks else list(battery["tasks"].keys())

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    completed = load_completed_keys(out_path)

    jobs = build_schedule(
        battery=battery,
        targets=targets,
        reps_t1=args.reps_t1,
        reps_t0=args.reps_t0,
        languages=languages,
        tasks=tasks,
        seed=args.seed,
        completed=completed,
    )

    total = len(jobs)
    print(
        f"[Collector] Targets={len(targets)} | Tasks={len(tasks)} | Langs={len(languages)} "
        f"| Pending={total} (Skipped completed={len(completed)})"
    )
    if args.dry_run or total == 0:
        if jobs:
            print("[Dry-Run Sample Job]:", json.dumps({k: v for k, v in jobs[0].items() if k != "target"}, ensure_ascii=False))
        return 0

    sem = asyncio.Semaphore(args.concurrency)
    write_lock = asyncio.Lock()
    stats = {"done": 0, "valid": 0, "invalid": 0, "failed": 0}

    with out_path.open("a", encoding="utf-8") as out_file:
        async def worker(job: dict[str, Any]) -> None:
            async with sem:
                last_err = None
                for attempt in range(1, args.max_retries + 1):
                    try:
                        res = await call_model_api(
                            target=job["target"],
                            system_prompt=job["system_prompt"],
                            user_prompt=job["user_prompt"],
                            temperature=job["temperature"],
                            timeout=args.timeout,
                        )
                        parsed = parse_color_response(
                            raw_text=res["raw_text"],
                            expected_format=job["format"],
                            explicit_reasoning=res["explicit_reasoning"],
                        )
                        record = {
                            "trial_key": job["trial_key"],
                            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "target_id": job["target_id"],
                            "protocol": normalize_protocol(job["target"]["protocol"]),
                            "claimed_model": job["target"]["model"],
                            "reported_model": res.get("reported_model"),
                            "provider": res.get("provider"),
                            "task_id": job["task_id"],
                            "condition": job["condition"],
                            "format": job["format"],
                            "lang": job["lang"],
                            "temperature": job["temperature"],
                            "temperature_sent": res.get("temperature_sent"),
                            "rep": job["rep"],
                            "parity": job["parity"],
                            "latency_ms": res["latency_ms"],
                            "response_id": res.get("response_id"),
                            "finish_reason": res.get("finish_reason"),
                            "usage": res["usage"],
                            "raw_text": res["raw_text"],
                            "explicit_reasoning": res.get("explicit_reasoning", ""),
                            "parsed": parsed,
                        }
                        async with write_lock:
                            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                            out_file.flush()
                            stats["done"] += 1
                            if parsed["status"] == "valid":
                                stats["valid"] += 1
                            else:
                                stats["invalid"] += 1
                            if stats["done"] % max(1, args.log_every) == 0 or stats["done"] == total:
                                print(
                                    f"  [{stats['done']}/{total}] valid={stats['valid']} "
                                    f"invalid={stats['invalid']} failed={stats['failed']} "
                                    f"last={job['trial_key']} -> {parsed.get('canonical_hex')} ({res['latency_ms']}ms)"
                                )
                        return
                    except Exception as exc:
                        last_err = str(exc)
                        if attempt < args.max_retries:
                            backoff = (1.5 ** attempt) + random.uniform(0.05, 0.35)
                            await asyncio.sleep(backoff)

                async with write_lock:
                    stats["done"] += 1
                    stats["failed"] += 1
                    print(f"  [ERROR] {job['trial_key']} failed after {args.max_retries} retries: {last_err}", file=sys.stderr)

        await asyncio.gather(*(worker(j) for j in jobs))

    print(f"[Done] valid={stats['valid']} invalid={stats['invalid']} failed={stats['failed']} -> {out_path}")
    return 0 if stats["failed"] == 0 else 1


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Batch RGB/Hex LLM Fingerprinting Collector (CC & Anthropic Messages)")
    p.add_argument("--prompts", default="config/prompts.json", help="Path to prompts battery JSON")
    p.add_argument("--targets-config", default="", help="Path to multi-target JSON config")
    p.add_argument("--protocol", default="cc", help="cloudflare | cc | anthropic-messages | claude-code | claude-cli")
    p.add_argument("--base-url", default="https://api.openai.com/v1", help="API base URL")
    p.add_argument("--cf-account-id", default="", help="Cloudflare Account ID (or env CF_ACCOUNT_ID)")
    p.add_argument("--api-key", default="", help="API key / Cloudflare token (overrides env)")
    p.add_argument("--api-key-env", default="", help="Env var holding API key")
    p.add_argument("--model", default="", help="Model identifier")
    p.add_argument("--target-id", default="", help="Custom target label in output")
    p.add_argument("--max-tokens", type=int, default=16, help="Max completion tokens (16 for direct, >=512 for CoT)")
    p.add_argument("--reasoning-mode", default="disabled", choices=["disabled", "auto", "low", "medium", "high"])
    p.add_argument("--reps-t1", type=int, default=30, help="Repetitions per cell at T=1.0")
    p.add_argument("--reps-t0", type=int, default=3, help="Repetitions per cell at T=0.0")
    p.add_argument("--languages", default="", help="Comma-separated subset of languages (default: all 4)")
    p.add_argument("--tasks", default="", help="Comma-separated subset of tasks (default: all 8)")
    p.add_argument("--concurrency", type=int, default=8, help="Concurrent requests")
    p.add_argument("--timeout", type=float, default=45.0, help="Per-request timeout in seconds")
    p.add_argument("--max-retries", type=int, default=3, help="Max retries on transient errors")
    p.add_argument("--seed", type=int, default=20260711, help="Shuffle seed for MAR execution order")
    p.add_argument("--output", default="data/responses.jsonl", help="Output JSONL file (resumable)")
    p.add_argument("--log-every", type=int, default=10, help="Progress log interval")
    p.add_argument("--dry-run", action="store_true", help="Print schedule summary without sending requests")
    return p


if __name__ == "__main__":
    parser = build_arg_parser()
    sys.exit(asyncio.run(run_collection(parser.parse_args())))
