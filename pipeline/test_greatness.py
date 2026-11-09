"""Test Batting Greatness, v0.3: comparable scorecard-only era model.

All eras use the SAME fields: Test innings runs and dismissals, match/innings,
year, team, opposition, and recorded venue host. No modern-only deliveries,
balls-faced, batting order, individual bowler data, or inferred pitch reports
are allowed in the primary historical comparison.

Missing historic rows and venue metadata are reported, not filled in.
External historic innings remain in the existing research pipeline; public
output contains only aggregated, derived player-level analysis, not scorecards.
This is observational, conditional uncertainty and an experimental model.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import math
import random
import statistics
from .historical import country
from .ingest import ROOT
from .model import read_innings

MIN_INNINGS=35
BOOTSTRAPS=240
SEED=20771930
OPP_WINDOW=5
YEAR_WINDOWS=(2,5,10,18,30)
REFERENCE_MIN=230
HISTORICAL_PUBLISHING_ALLOWED=False

KNOWN_CAREERS={
    "Don Bradman":{"runs":6996,"innings":80},
    "Virat Kohli":{"runs":9230,"innings":210},
}
FOCUS=["Don Bradman","Virat Kohli","Sachin Tendulkar","Viv Richards",
       "Garfield Sobers","Ricky Ponting","Brian Lara","Jacques Kallis",
       "Steve Smith","Joe Root","Rahul Dravid","Kumar Sangakkara",
       "Kane Williamson","Sunil Gavaskar","Allan Border",
       "Steve Waugh","Shivnarine Chanderpaul","Younis Khan"]

def safe_float(v,default=0.):
    try:
        f=float(v)
        return f if math.isfinite(f) else default
    except (ValueError,TypeError):
        return default

def host_class(r):
    host=country(r.get("host") or "")
    team=country(r.get("team") or "")
    opp=country(r.get("opposition") or "")
    if not host:return "unknown"
    if host==team:return "home"
    if host==opp:return "away"
    return "neutral"

def _sums(rows):
    a=[0.,0.,0.]
    for r in rows:
        a[0]+=r["runs"]
        a[1]+=r["dismissed"]
        a[2]+=1
    return a

def _rating(actual,expected_runs,outs,expected_outs,n, shrink=35):
    if not expected_runs or not n:return None
    rate=(actual+25)/(expected_runs+25)
    survival=(expected_outs+3)/(outs+3)
    z=.72*math.log(max(.04,rate))+.28*math.log(max(.04,survival))
    return 100*math.exp(z*n/(n+shrink))

def _quantile(xs,q):
    arr=sorted(xs)
    if not arr:return None
    p=(len(arr)-1)*q
    l=int(p);h=min(l+1,len(arr)-1)
    return arr[l]*(1-(p-l))+arr[h]*(p-l)

def _year_reference(yr,pid,annual,by_player):
    for width in YEAR_WINDOWS:
        total=[0.,0.,0.]
        for year in range(yr-width,yr+width+1):
            w=1/(1+abs(year-yr))
            all_year=annual.get(year,(0,0,0))
            self_year=by_player.get((year,pid),(0,0,0))
            for j in range(3):total[j]+=(all_year[j]-self_year[j])*w
        if total[2]>=REFERENCE_MIN or width==YEAR_WINDOWS[-1]:
            return ((total[0]+6)/(total[2]+0.15),min(.99,max(.45,(total[1]+2)/(total[2]+2))),total[2])
    return 35.,.84,0.

def _opp_factor(r,by_year_opp,by_year_opp_player,by_match_opp,annual,by_player,by_match,opponent_weight=1.):
    """Opposition-team concession proxy, leave-*player* and leave-*match* out.

    Uses other batters' scoring AGAINST the opponent nation in nearby years.
    Removes all target player's performances, plus all remaining observations
    from the evaluated Test, to avoid rating an attack as weaker just because
    this extraordinary batter made runs against it. Opponent mix remains a
    major confounder; this is not individual opposition bowler quality.
    """
    yr=r["year"];opp=r["opposition"];match=r["match_id"];pid=r["player_id"]
    runs=n=base_runs=base_n=0.
    for y in range(yr-OPP_WINDOW,yr+OPP_WINDOW+1):
        w=1/(1+abs(y-yr))
        a=by_year_opp.get((y,opp),(0,0,0))
        ap=by_year_opp_player.get((y,opp,pid),(0,0,0))
        b=annual.get(y,(0,0,0))
        bp=by_player.get((y,pid),(0,0,0))
        runs+=(a[0]-ap[0])*w;n+=(a[2]-ap[2])*w
        base_runs+=(b[0]-bp[0])*w;base_n+=(b[2]-bp[2])*w
    own=r["matchPlayer"]
    same_opp=by_match_opp.get((match,opp),(0,0,0))
    same_all=by_match.get(match,(0,0,0))
    # Own match was included at weight 1 for the same year; subtract only
    # OTHER players because the rated player's entries were already removed.
    runs-=max(0.,same_opp[0]-own[0]);n-=max(0.,same_opp[2]-own[2])
    base_runs-=max(0.,same_all[0]-own[0]);base_n-=max(0.,same_all[2]-own[2])
    if n<12 or base_n<50:return 1.,0.
    mean=(runs+30*25)/(n+25)
    base=(base_runs+30*25)/(base_n+25)
    log_effect=math.log(max(8,mean)/max(8,base))
    confidence=min(1.,n/(n+110))
    log_effect=max(-.22,min(.22,log_effect*confidence*.7*opponent_weight))
    return math.exp(log_effect),round(confidence,3)

def _venue_factor(r,annual,by_venue,by_player,by_venue_player,weight=1.):
    """Era-relative scoring on away or home grounds, leave-rated-batter-out."""
    kind=r["venueClass"]
    if kind not in ("home","away"):return 1.,0.
    yr=r["year"];pid=r["player_id"];r_sum=n=total=n_total=0.
    for y in range(yr-7,yr+8):
        w=1/(1+abs(y-yr))
        a=by_venue.get((y,kind),(0,0,0))
        ap=by_venue_player.get((y,kind,pid),(0,0,0))
        b=annual.get(y,(0,0,0))
        bp=by_player.get((y,pid),(0,0,0))
        r_sum+=(a[0]-ap[0])*w;n+=(a[2]-ap[2])*w
        total+=(b[0]-bp[0])*w;n_total+=(b[2]-bp[2])*w
    if n<35 or n_total<100:return 1.,0.
    mean=(r_sum+30*40)/(n+40)
    base=(total+30*40)/(n_total+40)
    evidence=min(1.,n/(n+260))
    effect=max(-.12,min(.12,math.log(mean/base)*evidence*.75*weight))
    return math.exp(effect),round(evidence,3)

def _match_factor(r,by_match,base_rpi,weight=1.):
    """Peer match scoring proxy; not observed pitch or weather."""
    a=by_match.get(r["match_id"],(0,0,0))
    # Remove ALL innings of this batter in the match, not only this innings.
    p=r["matchPlayer"]
    peers=[a[j]-p[j] for j in range(3)]
    if peers[2]<9:return 1.,0.
    mean=(peers[0]+8*10)/(peers[2]+10)
    effect=math.log(max(5,mean)/max(5,base_rpi))
    evidence=peers[2]/(peers[2]+18)
    return math.exp(max(-.17,min(.17,effect*.35*evidence*weight))),round(evidence,3)

def _bootstrap(rs,kind,seed):
    by_match=defaultdict(list)
    for r in rs:by_match[r["match_id"]].append(r)
    clusters=list(by_match.values())
    if len(clusters)<12:return None
    rng=random.Random(seed)
    ratings=[]
    for _ in range(BOOTSTRAPS):
        picks=[clusters[rng.randrange(len(clusters))] for _ in clusters]
        sample=[r for cluster in picks for r in cluster]
        if kind=="quality":
            val=_rating(sum(r["runs"] for r in sample),sum(r["expectedRuns"] for r in sample),
                        sum(r["dismissed"] for r in sample),sum(r["expectedOuts"] for r in sample),len(sample))
        else:
            values=[r["carryLog"] for r in sample if r["carryLog"] is not None]
            val=100*math.exp(statistics.mean(values)*len(values)/(len(values)+20)) if values else None
        if val is not None:ratings.append(val)
    return [round(_quantile(ratings,.05),1),round(_quantile(ratings,.95),1)] if ratings else None

def _peak(rs,window=25):
    if len(rs)<window:return None
    ordered=sorted(rs,key=lambda r:(r["date"],r["match_id"],r["innings_id"]))
    best=None
    for i in range(len(ordered)-window+1):
        a=ordered[i:i+window]
        v=_rating(sum(r["runs"] for r in a),sum(r["expectedRuns"] for r in a),
                  sum(r["dismissed"] for r in a),sum(r["expectedOuts"] for r in a),len(a),shrink=0)
        if v is not None and (best is None or v>best["index"]):
            best={"index":v,"start":a[0]["date"],"end":a[-1]["date"],"innings":window}
    return {**best,"index":round(best["index"],1)} if best else None

def _player_metrics(pid,rs):
    n=len(rs)
    runs=sum(r["runs"] for r in rs)
    outs=sum(r["dismissed"] for r in rs)
    expected=sum(r["expectedRuns"] for r in rs)
    expected_outs=sum(r["expectedOuts"] for r in rs)
    quality=_rating(runs,expected,outs,expected_outs,n)
    carry=[r["carryLog"] for r in rs if r["carryLog"] is not None]
    carry_index=100*math.exp(statistics.mean(carry)*len(carry)/(len(carry)+20)) if carry else None
    # Separate from the per-innings Quality measure; sustained surplus and
    # larger sample size matter. Not fitted to external all-time rankings.
    greatness=100+(quality-100)*(.65+.35*min(n,180)/180)+9*math.asinh((runs-expected)/1400)
    peak=_peak(rs)
    return {"quality":round(quality,1),"teamCarry":round(carry_index,1) if carry_index else None,
            "careerGreatness":round(greatness,1),"peakQuality":peak,
            "innings":n,"matches":len({r["match_id"] for r in rs}),
            "runs":int(runs),"dismissals":int(outs),
            "average":round(runs/outs,2) if outs else None,
            "expectedRuns":round(expected,1),
            "runsAboveExpected":round(runs-expected,1),
            "historicalInnings":sum(bool(r["scorecardOnly"]) for r in rs),
            "venueKnownPct":round(100*sum(r["venueClass"]!="unknown" for r in rs)/n,1),
            "opponentEvidencePct":round(100*sum(r["oppEvidence"]>.1 for r in rs)/n,1),
            "peerMatchEvidencePct":round(100*sum(r["matchEvidence"]>.1 for r in rs)/n,1),
            "teamCarryInnings":len(carry)}

def build_from_rows(source_rows, bootstraps=True):
    tests=[]
    for source in source_rows:
        if source.get("format")!="test":continue
        r=dict(source)
        r["runs"]=int(safe_float(r.get("runs")))
        r["dismissed"]=int(safe_float(r.get("dismissed")))
        r["year"]=int(r.get("year") or str(r["date"])[:4])
        r["opposition"]=country(r.get("opposition") or "")
        r["team"]=country(r.get("team") or "")
        r["venueClass"]=host_class(r)
        r["player_id"]=str(r.get("player_id") or r["name"]+"|"+r["team"])
        tests.append(r)
    if not tests:raise ValueError("No Test innings in source records")
    annual=defaultdict(lambda:[0.,0.,0.])
    by_player=defaultdict(lambda:[0.,0.,0.])
    by_year_opp=defaultdict(lambda:[0.,0.,0.])
    by_year_opp_player=defaultdict(lambda:[0.,0.,0.])
    by_match_opp=defaultdict(lambda:[0.,0.,0.])
    by_match=defaultdict(lambda:[0.,0.,0.])
    by_venue=defaultdict(lambda:[0.,0.,0.])
    by_venue_player=defaultdict(lambda:[0.,0.,0.])
    match_players=defaultdict(lambda:[0.,0.,0.])
    innings=defaultdict(list);player_rows=defaultdict(list)
    for r in tests:
        triple=(r["runs"],r["dismissed"],1)
        for dest in (annual[r["year"]],by_player[(r["year"],r["player_id"])],
                     by_year_opp[(r["year"],r["opposition"])],
                     by_year_opp_player[(r["year"],r["opposition"],r["player_id"])],
                     by_match_opp[(r["match_id"],r["opposition"])],
                     by_match[r["match_id"]],by_venue[(r["year"],r["venueClass"])],
                     by_venue_player[(r["year"],r["venueClass"],r["player_id"])],
                     match_players[(r["match_id"],r["player_id"])]):
            for j in range(3):dest[j]+=triple[j]
        innings[r["innings_id"]].append(r)
        player_rows[r["player_id"]].append(r)
    for r in tests:
        r["matchPlayer"]=match_players[(r["match_id"],r["player_id"])]
        base_rpi,base_d,base_n=_year_reference(r["year"],r["player_id"],annual,by_player)
        opp,oe=_opp_factor(r,by_year_opp,by_year_opp_player,by_match_opp,annual,by_player,by_match)
        venue,ve=_venue_factor(r,annual,by_venue,by_player,by_venue_player)
        match,me=_match_factor(r,by_match,base_rpi)
        r["baseExpected"]=base_rpi
        r["opponentFactor"]=opp
        r["venueFactor"]=venue
        r["matchFactor"]=match
        r["oppEvidence"]=oe
        r["venueEvidence"]=ve
        r["matchEvidence"]=me
        r["baselinePeers"]=round(base_n,0)
        r["expectedRuns"]=max(6.,min(130.,base_rpi*opp*venue*match))
        r["expectedOuts"]=max(.35,min(.99,base_d*math.sqrt(1./max(.1,opp*venue*match))))
        r["carryLog"]=None
    for rows in innings.values():
        total=sum(r["runs"] for r in rows)
        if len(rows)<6:continue
        for r in rows:
            others=(total-r["runs"])/(len(rows)-1)
            r["carryLog"]=math.log((r["runs"]+10)/(others+10))
    players=[]
    for pid,rs in player_rows.items():
        if len(rs)<MIN_INNINGS:continue
        metrics=_player_metrics(pid,rs)
        name=Counter(r["name"] for r in rs).most_common(1)[0][0]
        team=Counter(r["team"] for r in rs).most_common(1)[0][0]
        year_first=min(r["date"] for r in rs);year_last=max(r["date"] for r in rs)
        # Same model and features for history and modern. Diagnostics below
        # expose reliability; modern-only data never gives bonus points.
        by_opp=defaultdict(list);by_host=defaultdict(list)
        for r in rs:
            by_opp[r["opposition"]].append(r)
            by_host[r["venueClass"]].append(r)
        opponent_splits=[{"opponent":opp,"innings":len(a),"runs":int(sum(x["runs"] for x in a)),
                          "average":round(sum(x["runs"] for x in a)/sum(x["dismissed"] for x in a),2)
                          if sum(x["dismissed"] for x in a) else None,
                          "quality":round(_rating(sum(x["runs"] for x in a),sum(x["expectedRuns"] for x in a),
                                sum(x["dismissed"] for x in a),sum(x["expectedOuts"] for x in a),len(a)),1)}
                         for opp,a in by_opp.items() if len(a)>=5]
        opponent_splits.sort(key=lambda x:-x["innings"])
        venue_splits=[{"venueClass":h,"innings":len(a),"runs":sum(x["runs"] for x in a),
                       "quality":round(_rating(sum(x["runs"] for x in a),sum(x["expectedRuns"] for x in a),
                           sum(x["dismissed"] for x in a),sum(x["expectedOuts"] for x in a),len(a)),1)}
                      for h,a in by_host.items() if len(a)>=5]
        sens={}
        for label,drop in (("withoutOpposition","opponentFactor"),
                           ("withoutVenue","venueFactor"),
                           ("withoutMatchContext","matchFactor")):
            expected=sum(r["expectedRuns"]/r[drop] for r in rs)
            sens[label]=round(_rating(metrics["runs"],expected,metrics["dismissals"],
                         sum(r["expectedOuts"] for r in rs),len(rs)),1)
        metrics.update({"playerId":pid,"name":name,"team":team,"careerStart":year_first,
            "careerEnd":year_last,
            "qualityInterval90":_bootstrap(rs,"quality",SEED+sum(ord(x) for x in pid)) if bootstraps else None,
            "teamCarryInterval90":_bootstrap(rs,"carry",SEED+len(pid)*11) if bootstraps else None,
            "opponents":opponent_splits,
            "venues":venue_splits,
            "sensitivity":sens})
        official=KNOWN_CAREERS.get(name)
        if official:
            metrics["careerCheck"]={"referenceRuns":official["runs"],
              "referenceInnings":official["innings"],
              "runsMatch":metrics["runs"]==official["runs"],
              "inningsMatch":metrics["innings"]==official["innings"]}
        players.append(metrics)
    players.sort(key=lambda x:-x["quality"])
    rank_by_metric={}
    for metric in ("quality","teamCarry","careerGreatness"):
        ranked=sorted((p for p in players if p.get(metric) is not None),
                      key=lambda p:-p[metric])
        rank_by_metric[metric]=[p["playerId"] for p in ranked]
        for i,p in enumerate(ranked,1):p[metric+"Rank"]=i
    focus=[]
    for name in FOCUS:
        matches=[p for p in players if p["name"]==name]
        if matches:focus.append(matches[0]["playerId"])
    historic=sum(bool(r.get("scorecardOnly")) for r in tests)
    doc={"generatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modelVersion":"test-scorecard-common-denominator-v0.3-experimental",
        "title":"Test Batting Greatness — era, team carry and career/peak",
        "certifiedAllTimeRanking":False,
        "scorecardCommonDenominator":True,
        "modernOnlyFeaturesInPrimaryModel":False,
        "sourceScope":"Existing research-only historical innings plus Cricsheet Test match scorecards.",
        "historicalSourceRights":"Historical innings originate in ESPN-derived 2017 snapshot; independent redistribution permission NOT verified.",
        "publicationPolicy":"Only aggregate player-level analytic scores and grouped nation/venue metrics. No historical source match/innings records.",
        "historicalRawRowsRedistributed":False,
        "historicCoverageCertified":False,
        "rules":{
           "quality":"72% log era/match/opposition/venue-adjusted run production + 28% log dismissal survival; n/(n+35) shrinkage",
           "teamCarry":"Within each innings, run production vs mean teammate runs; equal innings, 20-innings reliability shrinkage",
           "careerGreatness":"Quality premium with sample size + cumulative contextual runs above expected; researcher-defined, not trained",
           "peak":"Best rolling 25-Test-innings same-scorecard quality, no sample-size shrinkage; selection bias acknowledged",
           "era":"Leave-batter-out nearby-year reference (2–30-year adaptive windows)",
           "opposition":"Other batters' runs per appearance vs opponent in ±5 years, excluding rated batter's entire career and evaluated match; shrunken proxy, not individual bowler strength",
           "homeAway":"Observed home/away scoring factor by nearby-year peers; unknown venues unadjusted",
           "conditions":"Other batters' scoring within the same Test excluding the evaluated batter's all innings; proxy, not measured pitch",
           "uncertainty":"90% conditional match-cluster bootstrap, fixed fitted baselines; excludes source missingness and historical structural uncertainty",
           "battingPosition":"NOT controlled: unavailable systematically in historical dataset",
           "seriesContext":"NOT modeled: no consistent historical series identifier",
           "individualBowlers":"NOT controlled in common all-era model: modern-only evidence",
           "matchOutcome":"NOT a core feature; historical match outcomes missing from the source"
        },
        "observedTestInnings":len(tests),
        "historicalTestInnings":historic,
        "observedDistinctMatches":len({r["match_id"] for r in tests}),
        "qualifiedPlayers":len(players),
        "focusPlayerIds":focus,
        "sortedPlayerIds":rank_by_metric,
        "players":players,
        "limitations":[
           "Historical data rights are unverified; confirm use of aggregate model outputs before public commercialization.",
           "Modern match IDs and older date/team signatures are only provisionally reconciled.",
           "No cross-era bowler-by-bowler exposure, consistent batting position or measured pitch.",
           "Opponent quality and same-match difficulty are correlational, imperfect scoring proxies.",
           "The index has not been externally calibrated against outcomes or source-complete scorecards.",
           "Match-block bootstrap does not incorporate model, selection or historical source uncertainty.",
           "Team carry is relative to recorded teammates and can reward playing on a weaker team.",
           "A top rank does not imply a hypothetical head-to-head win between eras."
        ]}
    return doc

def build(input_dir=ROOT/"data/generated", output_dir=ROOT/"site/data"):
    input_dir=Path(input_dir);output_dir=Path(output_dir)
    rows=read_innings(input_dir)
    result=build_from_rows(rows)
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"test-greatness.json").write_text(json.dumps(result,separators=(",",":"),ensure_ascii=False)+"\n")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=ROOT/"data/generated")
    p.add_argument("--output",type=Path,default=ROOT/"site/data")
    args=p.parse_args()
    r=build(args.input,args.output)
    print(json.dumps({
        "model":r["modelVersion"],"testInnings":r["observedTestInnings"],
        "historicInnings":r["historicalTestInnings"],
        "players":r["qualifiedPlayers"],
        "topQuality":[{"name":p["name"],"quality":p["quality"]} for p in r["players"][:10]],
        "referenceCareerChecks":[{"name":p["name"],**p["careerCheck"]}
          for p in r["players"] if "careerCheck" in p]},indent=2))

if __name__=="__main__":
    main()
