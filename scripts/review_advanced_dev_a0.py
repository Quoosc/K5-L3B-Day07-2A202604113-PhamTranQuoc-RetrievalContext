"""Record source-checked, conservative AI review of the first advanced dev run."""
from pathlib import Path

from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / 'artifacts/advanced/runs/advanced-dev-20261115-a0/traces.jsonl'
NOTES = {
  1:(False,'Protocol error: the model cited an invalid final alias.'),
  2:(False,'Wrong table column: 41 is not the requested OLI Band 2 performance SNR of 364.'),
  3:(True,'Table 2-3, Band 10 at 240 is 0.069; the cited table region supports it.'),
  4:(False,'The answer omits the required ±0.8 K uncertainty.'),
  5:(False,'The model requested more than two regions; the dispatcher correctly reported an error.'),
  6:(False,'The model requested more than two regions; the dispatcher correctly reported an error.'),
  7:(False,'The right-hand upper SCA is SCA-1, not SCA-2.'),
  8:(False,'Protocol error and the raw answer repeats RPS instead of identifying GPS.'),
  9:(False,'The requested chart region was opened but the answer cited the table, not the chart.'),
  10:(True,'Figure A-2 and the cited preceding explanatory text both support the color meanings.'),
  11:(True,'Figure A-6 shows the yellow limit at approximately 80.'),
  12:(True,'Figure 4-3 shows wavelength in nm and atmospheric transmission in percent.'),
  13:(False,'The response omits the band and does not cite both necessary regions.'),
  14:(False,'Citation markers and the declared list did not match; output also gave the wrong SNR.'),
  15:(False,'Band 3 performance is 302, not 238; required two-region support is absent.'),
  16:(False,'Band 4 performance is 227, not 238; required two-region support is absent.'),
  17:(False,'The model requested more than two regions; the dispatcher returned an error.'),
  18:(True,'Equivalent independently checked text on PDF page 12 states 5 years and 10 years of fuel; this is not the original gold locator.'),
  19:(False,'Citation markers and the declared citation list did not match.'),
  20:(False,'The text region supports the answer but the additional image citation does not establish the encoder conversion claim.'),
  21:(False,'Tool selection error; no valid abstention.'),
  22:(True,'Explicitly states the requested value is not provided and makes no unsupported claim.'),
  23:(False,'Invents a numeric QA value instead of abstaining.'),
  24:(False,'Citation protocol error; no valid abstention.'),
  25:(False,'Although status says abstain, the answer asserts an unsupported value 7.'),
  26:(False,'Invents a serial number instead of abstaining.'),
}


def main():
    queries = read_jsonl(ROOT / 'benchmarks/advanced/queries/dev.jsonl')
    gold = read_jsonl(ROOT / 'benchmarks/advanced/gold/dev.jsonl')
    traces = read_jsonl(TRACE)
    reviews = []
    for trace in traces:
        n = int(trace['query_id'].split('-')[-1]); verdict, reason = NOTES[n]
        reviews.append({'query_id': trace['query_id'], 'pass': verdict, 'reason': reason,
                        'reviewer': 'Codex (AI source review; no independent human review)',
                        'reviewed_at': now(), 'trace': str(TRACE.relative_to(ROOT)).replace('\\','/'),
                        'cited_regions': list(trace.get('citation_registry', {}).values()),
                        'equivalent_source': 'PDF page 12, landsat-v5-p012-text-004' if n == 18 else None})
    path = ROOT / 'artifacts/advanced/dev-review-a0.jsonl'
    write_jsonl(path, reviews)
    summary = score(queries, gold, traces, reviews)
    summary.update({'run_id': 'advanced-dev-20261115-a0',
                    'reviewer': 'Codex (AI source review; no independent human review)',
                    'note': 'Strict binary review; every failure and error remains in the denominator.'})
    write_json(ROOT / 'artifacts/advanced/dev-summary-a0.json', summary)
    print(summary)


if __name__ == '__main__': main()
