"""Free retrieval calibration and held-out evaluation. No paid API calls.

python scripts/benchmark.py --modes keyword semantic hybrid
Uses a cached sentence-transformers model only; never downloads it implicitly.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import hashlib
import json
import os
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rag.local_support import SectionRetriever, extract_guidance
from app.workflow.nodes import contextual_query


def selected(ranking, threshold, k):
    return [c for c in ranking if c.score >= threshold][:k]


def summarize(rows):
    answerable = [r for r in rows if not r['expects_abstention']]
    outside = [r for r in rows if r['expects_abstention']]
    targeted = [r for r in rows if r['section_match'] is not None]
    rate = lambda values: round(mean(values), 4) if values else None
    return {'cases': len(rows), 'answerable_cases': len(answerable), 'uncovered_cases': len(outside), 'targeted_cases': len(targeted), 'source_hits': sum(r['source_hit'] for r in answerable), 'correct_abstentions': sum(r['abstained'] for r in outside), 'next_section_matches': sum(r['section_match'] for r in targeted), 'source_hit_rate': rate([r['source_hit'] for r in answerable]),
            'avoidable_refusal_rate': rate([r['abstained'] for r in answerable]),
            'out_of_scope_abstention_rate': rate([r['abstained'] for r in outside]),
            'next_section_match_rate': rate([r['section_match'] for r in targeted]),
            'verbatim_step_traceability': rate([r['traceable'] for r in rows if r['has_step']]),
            'mean_retrieval_ms': round(mean(r['retrieval_ms'] for r in rows), 3) if rows else None}


def evaluate(cases, rankings, sections, threshold, k):
    rows = []
    for case in cases:
        ranking, latency = rankings[case['id']]
        chunks = selected(ranking, threshold, k)
        guidance = extract_guidance(chunks, case.get('attempts', []), sections)
        sources = {c.doc_id for c in chunks}
        steps = guidance['steps']
        matched = bool(steps and steps[0]['title'] in case['expected_sections']) if case['expected_sections'] else None
        traceable = all(any(step['text'] == s.chunk.text and step['step_id'] == s.step_id for s in sections) for step in steps)
        rows.append({'id': case['id'], 'kind': case['kind'], 'expects_abstention': case['expects_abstention'],
                     'source_hit': bool(sources & set(case['expected_sources'])), 'abstained': not chunks,
                     'section_match': matched, 'traceable': traceable, 'has_step': bool(steps),
                     'retrieved': [asdict(c) for c in chunks], 'answer': guidance['answer'],
                     'steps': steps, 'needs_escalation': guidance['needs_escalation'],
                     'retrieval_ms': latency, 'unsupported_request': case.get('unsupported_request')})
    return rows


def write_markdown(report, path):
    lines=['# Local benchmark results','','Draft development labels; not independent validation. 32 calibration cases; 28 held-out cases.','',
           '| Mode | Source hits | Avoidable refusal | Uncovered abstentions | Next section matches |',
           '|---|---:|---:|---:|---:|']
    for mode,result in report['modes'].items():
        r=result['held_out']
        lines.append(f"| {mode} | {r['source_hits']}/{r['answerable_cases']} | {r['avoidable_refusal_rate']} | {r['correct_abstentions']}/{r['uncovered_cases']} | {r['next_section_matches']}/{r['targeted_cases']} |")
    lines+=['','Recommended configuration, chosen on calibration data only:','```json',json.dumps(report.get('recommended_configuration'),indent=2),'```','','## Failed targeted cases']
    for mode,result in report['modes'].items():
        for row in result['held_out_cases']:
            if row['section_match'] is False or row['expects_abstention'] and not row['abstained']:
                lines.append(f"- {mode}: `{row['id']}`; proposed: {', '.join(s['title'] for s in row['steps']) or 'none'}.")
    lines+=['','## Limits',*['- '+s for s in report['limitations']],'- All emitted steps were mechanically traceable to complete source sections. This does not prove applicability.']
    lines += [f"- {mode} unavailable: {error}" for mode,error in report['unavailable'].items()]
    Path(path).write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modes', nargs='+', choices=['keyword','semantic','hybrid'], default=['keyword','semantic','hybrid'])
    parser.add_argument('--dataset', type=Path, default=Path('data/eval/benchmark_v2.json'))
    parser.add_argument('--docs-path', type=Path, default=Path('data/sample_docs'))
    parser.add_argument('--output', type=Path, default=Path('data/eval/benchmark_report.json'))
    args = parser.parse_args()
    data = json.loads(args.dataset.read_text(encoding='utf-8'))
    cases = data['questions']
    calibration = [c for c in cases if c['split']=='calibration']
    heldout = [c for c in cases if c['split']=='held_out']
    assert {c['family'] for c in calibration}.isdisjoint({c['family'] for c in heldout})
    report = {'dataset_sha256': hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
              'implementation_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('app/rag/local_support.py'),Path('app/workflow/nodes.py'),Path('scripts/benchmark.py')]},
              'runbooks_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.docs_path.glob('*.md'))},
              'package_versions': {name:importlib.metadata.version(name) for name in ['sentence-transformers','torch','transformers','fastapi','streamlit']},
              'python': platform.python_version(), 'platform': platform.platform(),
              'model': 'sentence-transformers/all-MiniLM-L6-v2', 'label_status': data['label_provenance'],
              'limitations': ['Draft labels need independent human review; preliminary held-out outputs were inspected during development.', 'No paid generation or LLM judge used.',
                             'Latency excludes model load and includes cached-query effects.',
                             'Timed human resolution comparison has not been run.',
                             'Traceability verifies extraction, not correctness of runbooks or applicability.'],
              'modes': {}, 'unavailable': {}}
    provider = None
    for mode in args.modes:
        started = time.perf_counter()
        try:
            if mode != 'keyword' and provider is None:
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                from app.rag.embeddings import LocalEmbeddingProvider
                provider = LocalEmbeddingProvider('all-MiniLM-L6-v2')
            retriever = SectionRetriever(args.docs_path, mode, provider if mode != 'keyword' else None)
        except Exception as exc:
            report['unavailable'][mode] = f'{type(exc).__name__}: {exc}'
            continue
        load_seconds = time.perf_counter() - started
        rankings = {}
        for case in cases:
            query = contextual_query({'query':case['question'], 'conversation_history':case.get('history', []), 'issue_query':case.get('issue_query')})
            start = time.perf_counter()
            ranking = retriever.rank(query)
            rankings[case['id']] = (ranking, round((time.perf_counter()-start)*1000, 3))
        best = None
        for threshold in [0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9]:
            for k in [1,3,5]:
                summary = summarize(evaluate(calibration, rankings, retriever.sections, threshold, k))
                # Prefer source coverage, but penalize false answers to uncovered questions.
                objective = 0.7*(summary['source_hit_rate'] or 0) + 0.3*(summary['out_of_scope_abstention_rate'] or 0)
                candidate = (objective, summary['next_section_match_rate'] or 0, -k, threshold)
                if best is None or candidate > best[0]:
                    best = (candidate, threshold, k, summary)
        _, threshold, k, tuned = best
        rows = evaluate(heldout, rankings, retriever.sections, threshold, k)
        report['modes'][mode] = {'configuration': {'retrieval_mode': mode, 'retrieval_top_k': k, 'retrieval_score_threshold': threshold},
                                 'load_seconds': round(load_seconds,3), 'calibration': tuned,
                                 'held_out': summarize(rows), 'held_out_cases':rows,
                                 'calibration_cases':evaluate(calibration, rankings, retriever.sections, threshold, k),
                                 'default_baseline_held_out':summarize(evaluate(heldout,rankings,retriever.sections,0.6,5))}
        print(mode, json.dumps({'configuration':report['modes'][mode]['configuration'], 'held_out':report['modes'][mode]['held_out']}))
    if report['modes']:
        # Recommendation uses calibration results only. Held-out scores never select settings.
        recommendation = max(report['modes'], key=lambda m: (0.7*(report['modes'][m]['calibration']['source_hit_rate'] or 0)+0.3*(report['modes'][m]['calibration']['out_of_scope_abstention_rate'] or 0), report['modes'][m]['calibration']['next_section_match_rate'] or 0))
        report['recommended_configuration'] = report['modes'][recommendation]['configuration']
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2),encoding='utf-8')
    write_markdown(report, args.output.with_suffix('.md'))
    print('Report:', args.output)

if __name__ == '__main__':
    main()
