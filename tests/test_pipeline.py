import gzip,json,pathlib,tempfile,unittest
from zipfile import ZipFile
from pipeline.ingest import parse_match,ingest,FILES
from pipeline.publication import publish
from pipeline.audit import audit

def example(fmt):
    # Fully SYNTHETIC fixture for unit testing; never use as a published observation.
    t='Test' if fmt=='test' else 'ODI' if fmt=='odi' else 'T20'
    deliveries=[
      {'batter':'V Kohli','non_striker':'RG Sharma','bowler':'Bowler A','runs':{'batter':4,'extras':0,'total':4}},
      {'batter':'V Kohli','non_striker':'RG Sharma','bowler':'Bowler A','extras':{'wides':1},'runs':{'batter':0,'extras':1,'total':1}},
      {'batter':'RG Sharma','non_striker':'V Kohli','bowler':'Bowler A','runs':{'batter':1,'extras':0,'total':1}},
      {'batter':'V Kohli','non_striker':'RG Sharma','bowler':'Bowler A','extras':{'noballs':1},'runs':{'batter':2,'extras':1,'total':3}},
      {'batter':'V Kohli','non_striker':'RG Sharma','bowler':'Bowler A','runs':{'batter':0,'extras':0,'total':0},'wickets':[{'player_out':'V Kohli','kind':'bowled'}]},
      {'batter':'RG Sharma','non_striker':'MS Dhoni','bowler':'Bowler A','runs':{'batter':3,'extras':0,'total':3}},
    ]
    return {'info':{'gender':'male','team_type':'international','match_type':t,'dates':['2018-01-01'],
            'teams':['India','Australia'],'city':'Sydney','venue':'SCG, Sydney',
            'outcome':{'winner':'India'},'registry':{'people':{'V Kohli':'vk','RG Sharma':'rs','MS Dhoni':'md','Bowler A':'ba'}}},
            'innings':[{'team':'India','overs':[{'over':0,'deliveries':deliveries}]}]}

class PipelineTests(unittest.TestCase):
 def test_delivery_scoring(self):
    rows,bowl,deliveries,match=parse_match(example('odi'),'fixture.json','odi')
    k={x['name']:x for x in rows}
    self.assertEqual(len(rows),3)
    self.assertEqual(k['V Kohli']['runs'],6)
    self.assertEqual(k['V Kohli']['balls'],3) # wide excluded, no-ball faced
    self.assertEqual(k['RG Sharma']['runs'],4)
    self.assertEqual(k['V Kohli']['dismissed'],1)
    self.assertEqual(k['V Kohli']['team_total'],12)
    self.assertEqual(k['V Kohli']['teammate_runs'],4)
    self.assertEqual(k['V Kohli']['region'],'SENA')
    self.assertEqual(bowl[0]['bowled'],4) # wide and no-ball not legal
    self.assertEqual(bowl[0]['wickets'],1)
    self.assertEqual(len(deliveries),5)
 def test_superover_excluded(self):
    d=example('t20i');d['innings'].append(dict(d['innings'][0],super_over=True))
    row,*_=parse_match(d,'abc.json','t20i')
    self.assertEqual(len(row),3)
 def test_all_three_formats_from_source(self):
    with tempfile.TemporaryDirectory() as tmp:
      base=pathlib.Path(tmp);raw=base/'raw';raw.mkdir()
      for fmt,file in FILES.items():
        with ZipFile(raw/file,'w') as z:
          for i in range(32):
            data=example(fmt);data['info']['dates']=[f'2018-{i%12+1:02d}-{i%27+1:02d}']
            z.writestr(f'{i}.json',json.dumps(data))
      data=base/'data'/'generated';manifest=ingest(raw,data)
      self.assertEqual(manifest['matchCount'],96)
      self.assertGreater(manifest['playerCount'],0)
      site=base/'site'/'data'
      count=publish(data/'innings.csv.gz',site/'innings.json.gz')
      self.assertGreater(count,0)
      self.assertTrue((site/'innings.json.gz').exists())
      self.assertFalse((site/'report.json').exists())
      self.assertFalse((site/'bootstrap.js').exists())
      # The coverage audit must expose missing historical decades, not certify all-time.
      coverage=audit(base)
      self.assertFalse(coverage['historicalCompletenessCertified'])
      self.assertFalse(coverage['allTimeRankingPermitted'])
      self.assertEqual(coverage['formats']['odi']['firstOfficialYear'],1971)
      self.assertIn(1971,coverage['formats']['odi']['yearsWithZeroObservedMatches'])
      self.assertEqual(coverage['formats']['odi']['observedMatches'],32)
 def test_no_imaginary_coverage(self):
    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaises(FileNotFoundError):ingest(pathlib.Path(tmp),pathlib.Path(tmp)/'generated')

if __name__=='__main__':unittest.main()
