"""Verify evidence against the six core rubric groups and the all-or-nothing bonus.

This is an evidence audit, not an instructor grade or an automatic semantic judge.
"""
import argparse
import json
from pathlib import Path
import subprocess

from src.day07.__main__ import code_hashes
from src.day07.advanced_eval import validate as advanced_validate
from src.day07.common import now, read_json, read_jsonl, sha256, write_json
from src.day07.evaluation import validate as base_validate

ROOT=Path(__file__).resolve().parents[1]


def audit():
    confirmation=read_json(ROOT/'artifacts/source-verification.json')
    base=ROOT/'benchmarks/base'; chunks=read_jsonl(ROOT/'artifacts/base/chunks.jsonl')
    validations={split:base_validate(read_jsonl(base/'queries'/f'{split}.jsonl'),
                    read_jsonl(base/'gold'/f'{split}.jsonl'),chunks,split) for split in ('dev','test')}
    lock=read_json(ROOT/'artifacts/base/freeze.json')
    dev=read_json(ROOT/'artifacts/base/dev_review.json')
    metrics=read_json(ROOT/'artifacts/base/submission-metrics.json')
    configs=read_json(ROOT/'configs/base.json')['configurations']
    current_hashes=code_hashes(ROOT/'configs/base.json',ROOT/'artifacts/base/chunks.jsonl',base)
    tracked=set(subprocess.check_output(['git','ls-files'],cwd=ROOT,encoding='utf-8').splitlines())
    required=('src/day07/agent.py','src/day07/retrieval.py','configs/base.json',
              'benchmarks/base/queries/test.jsonl','artifacts/base/freeze.json',
              'artifacts/base/runs/base-test-20261115-v1/D0.jsonl',
              'report/individual/2A202604113_PhamTranQuoc.md','docs/REPRODUCE.md')
    clean_path=ROOT/'artifacts/clean-checkout-check.json'
    clean=read_json(clean_path) if clean_path.exists() else {}
    access=read_json(ROOT/'artifacts/repository-access.json')
    def group(name,points,checks,evidence):
        return {'rubric_group':name,'maximum_points':points,'checks':checks,
                'all_checks_pass':all(checks.values()),'evidence':evidence}
    methods={c['method'] for c in configs}
    test_summaries=[metrics['test'][c]['source_review'] for c in ('D0','H0')]
    groups=[
        group('Dữ liệu và benchmark',13,{
            'base_dev_and_test_validated':all(validations.values()),
            'author_source_verification':confirmation['status']=='AUTHOR_SOURCE_VERIFICATION_CONFIRMED',
            'day6_chunks_156':len(chunks)==156,
            'day6_manifest_and_licenses':all((ROOT/p).exists() for p in [
                'artifacts/base/day6_manifest.json','artifacts/base/CPYTHON_LICENSE.txt','artifacts/base/CPYTHON_DOCUMENTATION_LICENSE.rst'])},
            ['artifacts/base/day6_manifest.json','benchmarks/base/manifest.json','artifacts/source-verification.json']),
        group('Retrieval',17,{'dense_lexical_hybrid':{'dense','lexical','hybrid'}<=methods,
            'same_dev_cases_all_methods':all(d['operations']['cases']==23 for d in metrics['dev'].values()),
            'ranking_and_context_metrics':all(k in metrics['test']['D0']['retrieval_context'] for k in ['hit1','evidence_hit3','context_evidence_rate'])},
            ['src/day07/retrieval.py','artifacts/base/submission-metrics.json']),
        group('Agent và context',17,{'real_model_recorded':bool(lock['model_sha256']),
            'tool_trace_all_test_cases':all(sum(int(v) for v in metrics['test'][c]['operations']['retrieval_tool_call_distribution_all'].values())==7 for c in ('D0','H0')),
            'context_review_five_each':all(sum(s['context_grades'].values())==5 for s in test_summaries),
            'safety_and_failure_probe':(ROOT/'artifacts/base/safety-smoke-v2.jsonl').is_file()},
            ['src/day07/agent.py','src/day07/context.py','artifacts/base/safety-smoke-v2.jsonl']),
        group('Đánh giá',17,{'same_seven_test_cases':all(s['cases']==7 for s in test_summaries),
            'five_grounded_and_two_absence_each':all(sum(s['grounded_grades'].values())==5 and s['abstention']['N']==2 for s in test_summaries),
            'errors_retained':all(s['errors']==1 for s in test_summaries),
            'tool_call_distributions':all('retrieval_tool_call_distribution_errors' in metrics['test'][c]['operations'] for c in ('D0','H0'))},
            ['artifacts/base/test-review-D0.jsonl','artifacts/base/test-review-H0.jsonl','artifacts/base/submission-metrics.json']),
        group('Thử nghiệm và cải thiện',13,{'two_improvement_variants':{'H1','H2'}<={c['id'] for c in configs},
            'chosen_on_dev':lock['chosen']==dev['chosen']=='H0',
            'original_dev_review_unchanged':sha256(ROOT/'artifacts/base/dev_review.json')==lock['dev_review_sha256'],
            'original_code_benchmark_corpus_unchanged':current_hashes==lock['hashes'],
            'dev_analysis_report':all(s in (ROOT/'report/individual/2A202604113_PhamTranQuoc.md').read_text(encoding='utf-8') for s in ['b-dev-q24','b-dev-q01','b-dev-q04'])},
            ['configs/base.json','artifacts/base/dev_review.json','artifacts/base/freeze.json','report/individual/2A202604113_PhamTranQuoc.md']),
        group('Tái lập và báo cáo',8,{'runbook':(ROOT/'docs/REPRODUCE.md').is_file(),
            'dependency_locks':(ROOT/'requirements-lock.txt').is_file(),
            'base_index_archive':(ROOT/'artifacts/base/qdrant-snapshot.zip').is_file(),
            'required_files_in_git_index':all(p in tracked for p in required),
            'clean_checkout_checks_pass':clean.get('all_checks_pass') is True,
            'repository_public_for_grader':access['private'] is False},
            ['docs/REPRODUCE.md','requirements-lock.txt','artifacts/base/qdrant-snapshot.zip','artifacts/clean-checkout-check.json'])]
    bonus={'maximum_points':15,'status':'not_yet_verified','all_or_nothing':True}
    summary=ROOT/'artifacts/advanced/v2-test-summary.json'
    if summary.is_file():
        score=read_json(summary)
        elements=read_jsonl(ROOT/'artifacts/advanced/elements.jsonl')
        stats=advanced_validate(read_jsonl(ROOT/'benchmarks/advanced-v2/queries/test.jsonl'),
              read_jsonl(ROOT/'benchmarks/advanced-v2/gold/test.jsonl'),elements,'test')
        bonus.update(passed=score['passed'],total=score['total'],required=score['required_passes'],
            checks={'threshold':score['meets_90_percent'],'all_30_covered':score['total']==stats['total']==30,
                    'source_confirmed':confirmation['status']=='AUTHOR_SOURCE_VERIFICATION_CONFIRMED',
                    'index_audit':(ROOT/'artifacts/advanced/index-audit-author-confirmed.json').is_file(),
                    'pre_test_freeze':(ROOT/'artifacts/advanced/freeze-v2.json').is_file()})
        bonus['all_checks_pass']=all(bonus['checks'].values())
        bonus['status']='evidence_supports_bonus_gate' if bonus['all_checks_pass'] else 'bonus_gate_not_met'
    return {'checked_at':now(),'audit_kind':'rubric evidence completeness; not an instructor-awarded grade',
            'base_groups':groups,'base_evidence_complete':all(g['all_checks_pass'] for g in groups),
            'base_maximum_points':85,'bonus':bonus,
            'core_validations':validations,
            'note':'Core has no absolute metric threshold. Original test errors and lower H0 score remain disclosed. Final awarded points belong to the instructor.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    report=audit();write_json(args.output,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['base_evidence_complete']: raise SystemExit(1)


if __name__=='__main__':main()
