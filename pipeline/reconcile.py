"""Verify complete historical careers against published primary reference totals.

A career matching a reference total is only *one* necessary quality gate, not
proof that all matches, innings, team totals, or delivery data are complete.
The report is deterministic and reports failures; it never confers all-time
certification on its own. Career references are expressly source-attributed.
"""
from __future__ import annotations
import json, pathlib
from collections import defaultdict,Counter
from datetime import datetime,timezone
from .ingest import ROOT
from .model import read_innings

# Historical retired careers only: their reference totals are time-invariant.
# Sources: ICC individual player pages and ICC Hall of Fame.
REFERENCE={
 ('Don Bradman','test'):(6996,'https://www.icc-cricket.com/hall-of-fame/hall-of-famers/hall-of-famer-donald-bradman'),
 ('Viv Richards','test'):(8540,'https://www.icc-cricket.com/rankings/2536/vivian-richards'),
 ('Viv Richards','odi'):(6721,'https://www.icc-cricket.com/rankings/2536/vivian-richards'),
 ('Sachin Tendulkar','test'):(15921,'https://www.icc-cricket.com/rankings/2962/sachin-tendulkar'),
 ('Sachin Tendulkar','odi'):(18426,'https://www.icc-cricket.com/rankings/2962/sachin-tendulkar'),
}

def reconcile_rows(rows):
    totals=defaultdict(int);inns=Counter();dates=defaultdict(list);sources=defaultdict(set)
    for r in rows:
        k=(r['name'],r['format'])
        if k in REFERENCE:
            totals[k]+=int(r['runs']);inns[k]+=1;dates[k].append(r['date']);sources[k].add('historic-scorecard' if r.get('scorecardOnly') else 'delivery')
    audits=[]
    for (name,fmt),(expected,url) in REFERENCE.items():
        actual=totals[(name,fmt)]
        audits.append({'player':name,'format':fmt,'referenceRuns':expected,'observedRuns':actual,
            'deltaRuns':actual-expected,'observedInnings':inns[(name,fmt)],
            'firstObservedDate':min(dates[(name,fmt)],default=None),
            'lastObservedDate':max(dates[(name,fmt)],default=None),
            'sourceTiers':sorted(sources[(name,fmt)]),'careerRunsReconciled':actual==expected,
            'referenceUrl':url})
    return {'generatedUTC':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'checks':audits,'checkedCareers':len(audits),'passingCareers':sum(r['careerRunsReconciled'] for r in audits),
      'allReferenceCareerRunTotalsMatch':all(r['careerRunsReconciled'] for r in audits),
      'officialMatchByMatchCensusReconciled':False,'allTimeRankingPermitted':False,
      'limitation':'Matching a career run total does NOT prove match coverage, ball counts, dismissals, batting order, or identity matching. Official scorecard census and source-rights verification remain outstanding.'}

def reconcile(root=ROOT):
    root=pathlib.Path(root)
    rows=read_innings(root/'data'/'generated',root/'data'/'historical'/'innings.csv')
    result=reconcile_rows(rows)
    public=root/'site'/'data';public.mkdir(parents=True,exist_ok=True)
    (public/'career-reconciliation.json').write_text(json.dumps(result,indent=2)+'\n')
    report_file=public/'report.json'
    if report_file.exists():
        report=json.loads(report_file.read_text());report['careerValidation']=result
        wire=json.dumps(report,separators=(',',':'));report_file.write_text(wire)
        (public/'bootstrap.js').write_text('window.CGL_REPORT='+wire.replace('</','<\\/')+';\n')
    return result

def main():
    r=reconcile()
    print(f"Reference retired-career runs reconciled: {r['passingCareers']}/{r['checkedCareers']} (not an official-match coverage certification)")
    for x in r['checks']:
        print(f" - {x['player']} / {x['format']}: {x['observedRuns']:,} of {x['referenceRuns']:,} (delta {x['deltaRuns']:+,}) {'PASS' if x['careerRunsReconciled'] else 'REQUIRES REVIEW'}")

if __name__=='__main__':main()
