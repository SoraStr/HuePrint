#!/usr/bin/env python3
"""Publish only allow-listed endpoint labels and exact non-secret probe text.

The two supplement manuscripts remain editable. This command replaces only the
named inventory block; appendices and subsequent analyses are never restored.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '<!-- SUPPLEMENT_INVENTORY -->'
END = '<!-- /SUPPLEMENT_INVENTORY -->'
INPUTS = [
    'data/census_40models.jsonl', 'config/family_map.json',
    'config/prompts.json', 'config/prompts.implicit_css.json',
    'config/prompts.implicit_v5_exact.json',
]


def code(value):
    return '`' + str(value).replace('|', '\\|') + '`'


def inventory(language):
    zh = language == 'ZH'
    families = json.loads((ROOT / INPUTS[1]).read_text())['families']
    grouped = {}
    for line in (ROOT / INPUTS[0]).read_text().splitlines():
        row = json.loads(line)
        grouped.setdefault(row['target_id'], []).append(row)
    assert len(grouped) == len(families) == 56
    lines = [BEGIN, '', '## C. ' + ('完整端点清单与标签来源' if zh else 'Complete Endpoint Inventory and Label Provenance'), '']
    lines += [
        ('本表完整列出数据集 A 的 56 个端点，每端点 48 条响应。标识符、声明模型名和返回模型名逐字取自冻结响应日志；家族与厂商标签取自版本化标签映射。这些是实验标签，不是独立认证的权重身份或产品目录。'
         if zh else 'This table lists all 56 Dataset A endpoints, with 48 responses each. Identifiers, declared models, and returned model labels are copied from the frozen response log; family and vendor labels come from the versioned mapping. They are experimental labels, not independently authenticated weight identities or a verified product catalog.'), '',
        ('来源：`data/census_40models.jsonl`（56 个端点，2,688 条记录）及 `config/family_map.json`。`CF-W` 表示 Cloudflare Workers AI；`CF-G` 表示 Cloudflare AI Gateway。日志中的 provider 字段在 CF-G 行仅为目标别名，不能据此推断独立后端。'
         if zh else 'Sources: `data/census_40models.jsonl` (56 endpoints, 2,688 records) and `config/family_map.json`. CF-W denotes Cloudflare Workers AI; CF-G denotes Cloudflare AI Gateway. The provider field for CF-G rows is a target alias and does not independently identify the backend.'), '',
        ('**表 S3：Dataset A 端点标签**' if zh else '**TABLE S3: Dataset A Endpoint Labels**'), '',
        ('| 端点 ID / 声明模型 | 返回模型标签 | 来源 | 厂商 / 家族 |'
         if zh else '| Endpoint ID / declared model | Returned model label | Source | Vendor / family |'),
        '| --- | --- | --- | --- |',
    ]
    for target, rows in sorted(grouped.items()):
        assert len(rows) == 48
        declared = sorted({x['claimed_model'] for x in rows})
        reported = sorted({str(x.get('reported_model') or '(not reported)') for x in rows})
        protocols = {x['protocol'] for x in rows}
        assert protocols <= {'cloudflare', 'cloudflare-gateway'}
        source = ', '.join('CF-W' if x == 'cloudflare' else 'CF-G' for x in sorted(protocols))
        family = families[target]
        lines.append('| ' + code(target) + ' / ' + ', '.join(map(code, declared)) + ' | ' + ', '.join(map(code, reported)) + ' | ' + source + ' | ' + code(family['vendor']) + ' / ' + code(family['family']) + ' |')
    sections = [
        ('D', INPUTS[2], '核心 40 单元多语言探针原文', 'Exact Forty-Cell Multilingual Probe Battery'),
        ('E', INPUTS[3], 'S4a CSS 与 JSON 金丝雀探针原文', 'Exact S4a CSS and JSON Canary Probes'),
        ('F', INPUTS[4], 'S4b 对照探针原文', 'Exact S4b Comparison Probes'),
    ]
    counts = {}
    for letter, source, title_zh, title_en in sections:
        battery = json.loads((ROOT / source).read_text())
        languages = battery['languages']
        cells = sum(len(task['prompts']) for task in battery['tasks'].values())
        counts[letter] = {'tasks': len(battery['tasks']), 'cells': cells, 'languages': languages}
        lines += ['', f'## {letter}. ' + (title_zh if zh else title_en), '',
                  ('来源：' if zh else 'Source: ') + code(source) + '. ' +
                  (f'{len(battery["tasks"])} 项任务，{len(languages)} 种语言，{cells} 个单元。以下引文保留原始 Unicode 文本；每个用户提示配合同格式、同语言的系统提示使用。'
                   if zh else f'{len(battery["tasks"])} tasks, {len(languages)} languages, and {cells} cells. The quoted prompts preserve the original Unicode text. Each user prompt is paired with the system prompt for its format and language.'), '']
        lines += ['### ' + ('系统提示' if zh else 'System prompts'), '']
        for fmt, prompts in battery['system_prompts'].items():
            lines += ['**' + fmt + '**', '']
            for lang, prompt in prompts.items():
                lines += [f'**{lang}:** {prompt}', '']
        lines += ['### ' + ('用户提示' if zh else 'User prompts'), '']
        for task_id, task in battery['tasks'].items():
            lines += ['**' + task_id + '** (' + task['format'] + '; ' + task['condition'] + ')', '']
            for lang, prompt in task['prompts'].items():
                lines += [f'**{lang}:** {prompt}', '']
    lines += [END]
    assert counts['D']['cells'] == 40 and counts['E']['cells'] == counts['F']['cells'] == 16
    return '\n'.join(lines), counts


def main():
    check = '--check' in sys.argv
    for language in ['EN', 'ZH']:
        path = ROOT / f'paper/SUPPLEMENT_{language}.md'
        text = path.read_text()
        block, counts = inventory(language)
        pattern = re.compile(re.escape(BEGIN) + r'.*?' + re.escape(END), re.S)
        match = pattern.search(text)
        assert match, path
        if check:
            assert match.group() == block, f'Out-of-date supplement inventory: {path}'
        else:
            path.write_text(pattern.sub(lambda _: block, text))
    manifest = {'sources': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS},
                'endpoints': 56, 'responses': 2688, 'probe_cells': counts,
                'published_fields': ['target_id', 'claimed_model', 'reported_model', 'protocol', 'vendor', 'family', 'system_prompts', 'tasks'],
                'excluded_fields': ['api keys', 'headers', 'base URLs', 'account identifiers', 'request/response access URLs']}
    path = ROOT/'paper/supplement/inventory_manifest.json'
    output = json.dumps(manifest, ensure_ascii=False, indent=2) + '\n'
    if check:
        assert path.read_text() == output
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output)
    print('Verified' if check else 'Synchronized', '56 endpoints, 40 core cells, and 32 S4 cells.')


if __name__ == '__main__':
    main()
