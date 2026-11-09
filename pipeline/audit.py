"""Independent source coverage audit. Match presence != official completeness."""
from collections import Counter
import json
from datetime import date, datetime, timezone
from pathlib import Path
from .ingest import ROOT

FORMAT_START={'test':1877,'odi':1971,'t20i':2005}
FORMAT_NAMES={'test':'Tests','odi':'ODIs','t20i':'T20Is'}

def audit(root=ROOT):
    root=Path(root)
    manifest=json.loads((root/'data/generated/manifest.json').read_text())
    matches=json.loads((root/'data/generated/matches.json').read_text())
    report=json.loads((root/'site/data/report.json').read_text())
    if len(matches)!=manifest['matchCount']:
        raise ValueError('Delivery manifest and unique match rows disagree')
    if report['metadata'].get('isAllTimeEligible'):
        raise ValueError('Historical completeness needs independent official match-by-match reconciliation')
    modern=Counter((m['format'],int(m['year'])) for m in matches)
    history=Counter()
    for k,n in report['metadata'].get('historicalMatchesByYear',{}).items():
        fmt,year=k.split(':');history[(fmt,int(year))]=int(n)
    latest=max([date.today().year]+[int(m['year']) for m in matches])
    formats={}
    for fmt,start in FORMAT_START.items():
        rows=[]
        for year in range(start,latest+1):
            old=history[(fmt,year)];new=modern[(fmt,year)]
            rows.append({'year':year,'historicalScorecardMatches':old,'deliveryMatches':new,'observedMatches':old+new})
        observed=[r['year'] for r in rows if r['observedMatches']]
        formats[fmt]={'firstOfficialYear':start,'firstObservedYear':min(observed) if observed else None,
                      'lastObservedYear':max(observed) if observed else None,
                      'observedMatches':sum(x['observedMatches'] for x in rows),
                      'historicalScorecardMatches':sum(x['historicalScorecardMatches'] for x in rows),
                      'deliveryMatches':sum(x['deliveryMatches'] for x in rows),
                      'yearsWithZeroObservedMatches':[x['year'] for x in rows if x['observedMatches']==0],
                      'yearly':rows,'officialMatchesCoveredPercent':None}
    hist=report['metadata'].get('hasHistoricalScorecards',False)
    rec_file=root/'site/data/career-reconciliation.json'
    career=json.loads(rec_file.read_text()) if rec_file.exists() else {}
    coverage={'calculatedUTC':datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'scope':'Non-overlapping historical scorecard batting records + Cricsheet international ball-by-ball records; NOT a certified official match census',
              'deliveryObservedMatches':manifest['matchCount'],
              'historicalObservedMatches':report['metadata'].get('historicalDistinctMatchesAfterDedup',0),
              'totalObservedMatches':sum(x['observedMatches'] for x in formats.values()),
              'earliestDeliveryDate':manifest['earliestDate'],'latestDeliveryDate':manifest['latestDate'],
              'historicalSourceImported':hist,'historicalInnings':report['metadata'].get('historicalObservedInnings',0),
              'historicalSource':report['metadata'].get('historicalSource'),
              'historicalCompletenessCertified':False,'allTimeRankingPermitted':False,
              'referenceCareerRunsPassing':career.get('passingCareers',0),
              'referenceCareerRunsChecked':career.get('checkedCareers',0),
              'referenceCareerRunsAllMatch':career.get('allReferenceCareerRunTotalsMatch',False),
              'historicalIdentityAmbiguities':report['metadata'].get('historicalIdentityAmbiguities',0),
              'historicalDuplicatesSuppressed':report['metadata'].get('historicalOverlapSuppressed',0),
              'officialCensusReconciliation':'NOT COMPLETED — no season-by-season official match-ID census',
              'notes':[
                  'Positive source-match counts do not establish every official international match was captured.',
                  'Historical scorecard source spans the 1877–2017 era when available, but its year-by-year completeness is NOT verified.',
                  'Modern Cricsheet record wins for overlapping entire matches; historic source counts are non-overlapping matches only.',
                  'Historical batting position and balls faced are unavailable for some/all older source rows; never impute them.',
                  'Historical scorecard data is based on publicly posted ESPNcricinfo-derived data; source re-use rights need verification before republication.',
                  'Historical era-parity rankings are NOT equivalent to modern bowler-adjusted quality rankings.',
                  'Compare player career innings totals against authoritative official career stats and investigate discrepancies before all-time conclusions.',
                  'Cricsheet withholds some Afghanistan matches and some other events.'
              ],'formats':formats}
    (root/'site/data').mkdir(parents=True,exist_ok=True)
    (root/'site/data/coverage-status.json').write_text(json.dumps(coverage,indent=2)+'\n')
    lines=['# Cricket Greatness Lab · independent source coverage audit','',
           f"Generated on **{coverage['calculatedUTC']}**.",'',
           f"**{coverage['deliveryObservedMatches']:,}** source delivery matches; **{coverage['historicalObservedMatches']:,}** extra historical scorecard matches.",'',
           f"**Combined observed matches:** {coverage['totalObservedMatches']:,} across Tests, ODIs and T20Is; all independently deduplicated by match signature.",'',
           '**Official all-time completeness: NOT CERTIFIED.** This means the website must not publish a definitive greatest-ever result.','',
           f"**Retired-career ICC run-total checks passing:** {career.get('passingCareers',0)}/{career.get('checkedCareers',0)}. These checks do not certify every match.",'',
           '| Format | Origin | First observed year | Modern delivery matches | Older scorecard matches | Combined matches |',
           '|---|---:|---:|---:|---:|---:|']
    for fmt,x in formats.items():
        lines.append(f"| {FORMAT_NAMES[fmt]} | {x['firstOfficialYear']} | {x['firstObservedYear'] or 'none'} | {x['deliveryMatches']:,} | {x['historicalScorecardMatches']:,} | {x['observedMatches']:,} |")
    lines.extend(['','## Annual observed match counts (NOT a completeness denominator)','',
                  '| Year | Test modern | Test historical | ODI modern | ODI historical | T20I modern | T20I historical |',
                  '|---:|---:|---:|---:|---:|---:|---:|'])
    for yr in range(1877,latest+1):
        vals=[]
        for fmt in ('test','odi','t20i'):
            vals.extend((str(modern[(fmt,yr)]) if yr>=FORMAT_START[fmt] else '—',
                         str(history[(fmt,yr)]) if yr>=FORMAT_START[fmt] else '—'))
        lines.append('| '+str(yr)+' | '+' | '.join(vals)+' |')
    lines.extend(['','## Retired-career scoring reconciliation','',
                  '| Batter | Format | Observed runs | ICC reference runs | Difference | Result |',
                  '|---|---|---:|---:|---:|---|'])
    for c in career.get('checks',[]):
        lines.append(f"| {c['player']} | {c['format'].upper()} | {c['observedRuns']:,} | {c['referenceRuns']:,} | {c['deltaRuns']:+,} | {'PASS' if c['careerRunsReconciled'] else 'MISSING / DISCREPANCY'} |")
    lines.extend(['','## Historical player sensitivity','',
                  '- Tendulkar (1989 debut) must be evaluated with 1989–2001 ODI scorecards, not only post-2002 deliveries.',
                  '- Richards (1975 ODI debut) and Bradman (1928 Test debut) must not be excluded from any all-era leaderboard.',
                  '- The model now computes a separate common-denominator scorecard-parity index for older and newer batters.',
                  '- Historical source does not provide reliable original batting order, all balls faced, modern opponent-bowler exposure, or complete official-match verification.',
                  '- Pre-2002 record presence is now explicit; source completeness is STILL an open validation step.','',
                  '## Source hashes',''])
    for src,digest in manifest['sha256'].items():lines.append(f'- Cricsheet `{src}`: `{digest}`')
    if manifest.get('historical'):
        h=manifest['historical'];lines.extend(['',f"- Historical source: {h.get('source','unknown')}",
                       f"- Historical innings SHA256: `{h.get('sourceSHA256','unknown')}`",
                       f"- Historical source rights: {h.get('sourceLicense','unknown')}"])
    lines.extend(['','Read `docs/sources.md` for provenance and rights. No unlicensed original source ZIP/CSV is shipped.'])
    (root/'data/coverage.md').write_text('\n'.join(lines)+'\n')
    return coverage

def main():
    c=audit()
    print('Coverage audit:',c['totalObservedMatches'],'combined observed games; historical certified:',c['historicalCompletenessCertified'])

if __name__=='__main__':main()
