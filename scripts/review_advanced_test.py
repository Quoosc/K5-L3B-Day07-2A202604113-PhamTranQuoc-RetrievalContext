"""Record a conservative source-by-source AI review of the frozen advanced test."""
import math
from pathlib import Path
import statistics

from src.day07.advanced_eval import score
from src.day07.common import now, read_jsonl, write_json, write_jsonl

ROOT=Path(__file__).resolve().parents[1]
TRACE=ROOT/'artifacts/advanced/runs/advanced-test-20261116-final/traces.jsonl'
VISION=ROOT/'artifacts/advanced/runs/advanced-test-20261116-composite/traces.jsonl'
NOTES={
  1:(True,'Table 1-1 supports 3.14 Terabit, file-based for Landsat 8.'),
  2:(True,'Table 2-2 supports OLI Band 7 performance SNR 334.'),
  3:(True,'Table 2-3 supports TIRS Band 11 NEΔT 0.059 at 280.'),
  4:(True,'Table A-1 supports −4.4 ± 1.75 K at 300 K for Band 11.'),
  5:(True,'Table 2-1 image supports 0.851–0.879 µm for Landsat 8 Band 5.'),
  6:(True,'Table 1-1 supports X-Band Earth Coverage for Landsat 8 image downlink.'),
  7:(True,'Figure 2-1 labels the lower-right component Solar Panel.'),
  8:(True,'Figure 2-5 shows Bands 12–14 Blind at the top of the even stack.'),
  9:(False,'The answer does not identify the left baffle as Nadir or the right baffle as spaceview; it names a direction instead.'),
  10:(True,'Figure A-5 labels the bottom component Focal Plane Array (FPA).'),
  11:(False,'The lower SCA is SCA-C/SCA02; Band 10 is a band, not the requested SCA.'),
  12:(False,'The NIR red bar is about 204; 360 exceeds the absolute tolerance of 20.'),
  13:(True,'The Cirrus red bar is about 165; the answer 150 is within the absolute tolerance of 20.'),
  14:(True,'Figure A-6 shows the red limit line near 85.'),
  15:(True,'Figure 4-3 shows TIRS bands 10 and 11 beyond 10,000 nm.'),
  16:(False,'The response omits the square marker shape, and also cites the other panel for a question about the left panel.'),
  17:(True,'Table 2-1 supports Band 5 and Table 2-2 supports SNR 204; both citations are correct.'),
  18:(True,'Table 2-1 supports Band 6 and Table 2-2 supports SNR 265; both citations are correct.'),
  19:(True,'Table 2-1 supports Band 7 and Table 2-2 supports SNR 334; both citations are correct.'),
  20:(True,'Table 2-1 supports Band 8 and Table 2-2 supports SNR 149; both citations are correct.'),
  21:(True,'The cited Global Survey Mission text states once every 16 days.'),
  22:(False,'The answer gives 4,096 but omits 256 for the previous 8-bit instruments.'),
  23:(True,'The cited QA-band text supports lower NDVI and delayed phenology measurements.'),
  24:(False,'The model abstained although Appendix A.2 gives December 19, 2014.'),
  25:(True,'Explicitly abstains without inventing an acquisition date; absence audit remains provisional.'),
  26:(True,'Explicitly abstains without inventing a password; absence audit remains provisional.'),
  27:(True,'States that the requested fictional QA value is not provided; no value is invented.'),
  28:(True,'Explicitly abstains without naming an operator; absence audit remains provisional.'),
  29:(True,'Explicitly abstains without inventing a storage price; absence audit remains provisional.'),
  30:(True,'States that the requested fictional IP address is not provided; no address is invented.'),
}


def main():
    queries=read_jsonl(ROOT/'benchmarks/advanced/queries/test.jsonl')
    gold=read_jsonl(ROOT/'benchmarks/advanced/gold/test.jsonl')
    traces=read_jsonl(TRACE); vision=read_jsonl(VISION)
    if [t['query_id'] for t in traces] != [q['id'] for q in queries] or [t['query_id'] for t in vision] != [q['id'] for q in queries]:
        raise ValueError('Both trace files must contain exactly the complete ordered test split')
    first={t['query_id']:t for t in vision}; reviews=[]
    for trace in traces:
        initial=first[trace['query_id']]
        verdict,reason=NOTES[int(trace['query_id'].split('-')[-1])]
        reviews.append({'query_id':trace['query_id'],'pass':verdict,'reason':reason,
                        'reviewer':'Codex (AI source review; no independent human review)',
                        'reviewed_at':now(),'trace':TRACE.relative_to(ROOT).as_posix(),
                        'policy_branch':trace.get('policy_branch'),'vision_stage_status':initial['status'],
                        'vision_stage_error':initial.get('error'),
                        'cited_regions':list(trace.get('citation_registry',{}).values())})
    write_jsonl(ROOT/'artifacts/advanced/test-review-composite.jsonl',reviews)
    result=score(queries,gold,traces,reviews)
    durations=sorted(t.get('combined_elapsed_ms',t.get('elapsed_ms',0))/1000 for t in traces)
    result.update({'run_id':'advanced-test-20261116-final',
                   'reviewer':'Codex (AI source review; no independent human review)',
                   'vision_stage_errors':sum(t['status']=='error' for t in vision),
                   'vision_stage_timeouts':sum('timeout' in str(t.get('error','')).casefold() or
                                               'timed out' in str(t.get('error','')).casefold() for t in vision),
                   'latency_seconds':{'median':statistics.median(durations),
                                      'p95':durations[math.ceil(.95*len(durations))-1],
                                      'note':'Sum of per-case stage times; excludes server startup and waiting between stages.'},
                   'vision_prompt_tokens':sum(t.get('usage',{}).get('prompt_tokens',0) for t in traces),
                   'refiner_prompt_tokens':sum(t.get('refiner_usage',{}).get('prompt_tokens',0) for t in traces),
                   'api_cost_usd':sum(t.get('api_cost_usd',0) for t in traces),
                   'note':'Frozen pipeline, all 30 cases included; source/absence review is AI-assisted and requires independent confirmation.'})
    write_json(ROOT/'artifacts/advanced/test-summary-composite.json',result)
    print(result)


if __name__=='__main__': main()
