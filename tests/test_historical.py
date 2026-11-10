"""Synthetic test records; no fabricated cricket statistics are published."""
import csv,gzip,json,pathlib,tempfile,unittest
from zipfile import ZipFile
from pipeline.historical import (load_batting,ingest_historical,fmt_name,parse_day,country,batsman)
from pipeline.ingest import ingest,FILES
from pipeline.ledger import read_innings
from pipeline.scorecard_model import build_from_rows
from pipeline.reconcile import reconcile_rows
from pipeline.audit import audit
from tests.test_pipeline import example

HEAD=['Player','Runs','BF','4s','6s','Inns','Opposition','Ground','Date','Country','Notout','type']

def old(name,team,opp,dt,runs=30,nout='',f='Test',inn=1):
    return dict(Player=f'{name} ({team})',Runs=str(runs),BF='',**{'4s':'1','6s':'0'},
                Inns=str(inn),Opposition='v '+opp,Ground='Melbourne',Date=dt,Country=team,
                Notout=nout,type=f)

class HistoricalTests(unittest.TestCase):
 def test_older_source_columns(self):
    self.assertEqual(fmt_name('Test'),'test')
    self.assertEqual(fmt_name('ODI'),'odi')
    self.assertEqual(fmt_name('T20I'),'t20i')
    self.assertEqual(parse_day('15 Mar 1877'),'1877-03-15')
    self.assertEqual(country('AUS'),'Australia')
    self.assertEqual(country('WI'),'West Indies')
    self.assertEqual(batsman('SR Tendulkar (INDIA)'),'Sachin Tendulkar')
 def test_backfill_1877_1930s_odi_and_no_batting_order_guess(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=pathlib.Path(tmp);raw=root/'historical';raw.mkdir()
      obs=[old('C Bannerman','AUS','England','1877-03-15',165,'TRUE'),
           old('EJ Gregory','AUS','England','1877-03-15',2),
           old('AA Shaw','ENG','Australia','1877-03-15',5),
           old('DG Bradman','AUS','England','1930-01-03',150),
           old('WH Ponsford','AUS','England','1930-01-03',32),
           old('JB Hobbs','ENG','Australia','1930-01-03',50),
           old('IVA Richards','WI','England','1980-05-01',75,f='ODI'),
           old('CG Greenidge','WI','England','1980-05-01',10,f='ODI'),
           old('IT Botham','ENG','West Indies','1980-05-01',9,f='ODI'),
           old('SR Tendulkar','INDIA','Australia','1996-03-01',110,f='ODI'),
           old('R Dravid','INDIA','Australia','1996-03-01',7,f='ODI'),
           old('RT Ponting','AUS','India','1996-03-01',56,f='ODI'),
           old('XB Nowt','AUS','India','1996-03-01','-',f='ODI')]
      with (raw/'all-innings.csv').open('w',newline='') as fp:
        wr=csv.DictWriter(fp,fieldnames=HEAD);wr.writeheader();wr.writerows(obs)
      rows,summary=load_batting(raw/'all-innings.csv')
      self.assertEqual(summary['historicalMatchCount'],4)
      self.assertEqual(summary['historicalInnings'],12)
      self.assertEqual(summary['firstDate'],'1877-03-15')
      t=next(r for r in rows if r['name']=='Sachin Tendulkar')
      self.assertEqual(t['format'],'odi');self.assertEqual(t['role'],'unknown')
      self.assertEqual(t['position'],0)
      self.assertEqual(t['teammate_runs'],7)
      self.assertEqual(t['team_total'],0) # never fabricate team extras
      self.assertEqual(next(r for r in rows if r['name']=='C Bannerman')['dismissed'],0)
      self.assertIn('no_numeric_batting_innings',summary['skipped'])
      result=ingest_historical(raw,root/'data'/'generated')
      self.assertEqual(result['historicalMatchCount'],4)
      self.assertTrue((root/'data'/'generated'/'historical-innings.csv.gz').exists())
 def test_do_not_double_count_historical_and_modern_match(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=pathlib.Path(tmp);raw=root/'raw';raw.mkdir()
      for f,file in FILES.items():
        with ZipFile(raw/file,'w') as z:
          doc=example(f)
          z.writestr('2018.json',json.dumps(doc))
      gen=root/'data'/'generated';ingest(raw,gen)
      hist=root/'history';hist.mkdir()
      obs=[old('V Kohli','INDIA','Australia','2018-01-01',500,f='ODI'),
           old('RG Sharma','INDIA','Australia','2018-01-01',120,f='ODI'),
           old('RT Ponting','AUS','India','2018-01-01',100,f='ODI'),
           old('DG Bradman','AUS','England','1930-01-03',100),
           old('WH Ponsford','AUS','England','1930-01-03',50),
           old('JB Hobbs','ENG','Australia','1930-01-03',48)]
      with (hist/'all-innings.csv').open('w',newline='') as fp:
        wr=csv.DictWriter(fp,fieldnames=HEAD);wr.writeheader();wr.writerows(obs)
      ingest_historical(hist,gen)
      rows=read_innings(gen)
      self.assertTrue(any(r['name']=='Don Bradman' and r['scorecardOnly'] for r in rows))
      self.assertEqual(sum(1 for r in rows if r['format']=='odi' and r['date']=='2018-01-01'),3)
      self.assertGreaterEqual(read_innings.last_audit['duplicateHistoricalMatchInningsSuppressed'],3)
      self.assertEqual(sum(1 for r in rows if r['name']=='Virat Kohli' and r['format']=='odi'),1)
 def test_scorecard_reference_common_baseline_in_all_eras(self):
    with tempfile.TemporaryDirectory() as tmp:
      hist=pathlib.Path(tmp)/'history';hist.mkdir()
      o=[]
      for i in range(30):
        day=f'1930-{1+i//25:02d}-{i%25+1:02d}'
        o.extend([old('DG Bradman','AUS','England',day,120),
                  old('WH Ponsford','AUS','England',day,30),
                  old('HC Smith','AUS','England',day,19),
                  old('JB Hobbs','ENG','Australia',day,40),
                  old('HT Smith','ENG','Australia',day,20)])
      with (hist/'all-innings.csv').open('w',newline='') as fp:
        wr=csv.DictWriter(fp,fieldnames=HEAD);wr.writeheader();wr.writerows(o)
      rows,_=load_batting(hist/'all-innings.csv')
      for r in rows:r['scorecardOnly']=True
      report=build_from_rows(rows,bootstraps=False,format_code='test',minimum_innings=20)
      self.assertFalse(report['certifiedAllTimeRanking'])
      self.assertTrue(report['players'])
      self.assertEqual(report['players'][0]['name'],'Don Bradman')
      self.assertGreater(report['players'][0]['quality'],100)
      # Only five source batters per innings: under the six-player minimum.
      # This correctly returns missing team-carry rather than fabricating peers.
      self.assertIsNone(report['players'][0]['teamCarry'])

 def test_end_to_end_historic_and_modern_reports_remain_uncertified(self):
    with tempfile.TemporaryDirectory() as tmp:
      root=pathlib.Path(tmp);raw=root/'raw';raw.mkdir()
      for f,file in FILES.items():
        with ZipFile(raw/file,'w') as z:
          for i in range(32):
            doc=example(f);doc['info']['dates']=[f'2018-{i%12+1:02d}-{i%27+1:02d}']
            z.writestr(f'{i}.json',json.dumps(doc))
      data=root/'data'/'generated';ingest(raw,data)
      src=root/'historical';src.mkdir()
      obs=[]
      for i in range(30):
        day=f'1930-{1+i//25:02d}-{i%25+1:02d}'
        obs.extend([old('DG Bradman','AUS','England',day,120),old('WH Ponsford','AUS','England',day,30),
             old('HC Smith','AUS','England',day,19),old('JB Hobbs','ENG','Australia',day,40),
             old('HT Smith','ENG','Australia',day,20)])
      obs.extend([old('IVA Richards','WI','England','1981-06-01',122,f='ODI'),
          old('CG Greenidge','WI','England','1981-06-01',50,f='ODI'),
          old('G Boycott','ENG','West Indies','1981-06-01',40,f='ODI')])
      with (src/'all-innings.csv').open('w',newline='') as fp:
        wr=csv.DictWriter(fp,fieldnames=HEAD);wr.writeheader();wr.writerows(obs)
      ingest_historical(src,data)
      report=build_from_rows(read_innings(data),bootstraps=False,format_code='test',minimum_innings=20)
      self.assertFalse(report['certifiedAllTimeRanking'])
      self.assertFalse(report['modernOnlyFeaturesInPrimaryModel'])
      self.assertIn('Don Bradman', [p['name'] for p in report['players']])
      reconciliation=reconcile_rows(read_innings(data))
      self.assertFalse(reconciliation['allReferenceCareerRunTotalsMatch'])
      self.assertEqual(reconciliation['checkedCareers'],5)
      self.assertFalse(reconciliation['allTimeRankingPermitted'])
      cov=audit(root)
      self.assertEqual(cov['formats']['test']['firstObservedYear'],1930)
      self.assertGreater(cov['totalObservedMatches'],96)
      self.assertFalse(cov['historicalCompletenessCertified'])

if __name__=='__main__':unittest.main()
