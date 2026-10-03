"""Optional open schedule ingestion with a conservative March 1 feature horizon."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import re
import urllib.request
import pyarrow.parquet as pq
from .data import ROOT, read, dump

BASE = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_mens_college_basketball_schedules/'
# The community archive uses these labels for different universities in these years.
# Resolved against the NCAA-labeled schedule matchups, never by fuzzy name similarity.
SEASON_ALIASES = {2023:{'Lafayette':'Louisiana'},2025:{'SanDiego':'UC San Diego'}}
ALIASES = {
 'SouthernUniv':'Southern', 'NorthwesternLA':'Northwestern State', 'Kent':'Kent State',
 'MonmouthNJ':'Monmouth', 'WIMilwaukee':'Milwaukee', 'AlbanyNY':['UAlbany','Albany'],
 'CentralConn':'Central Connecticut', 'TAMCChristi':'Texas A&M-Corpus Christi',
 'MtStMarys':'Mount St. Mary\'s', 'AmericanUniv':'American', 'StJosephsPA':'Saint Joseph\'s',
 'CSFullerton':'Cal State Fullerton', 'StMarysCA':'Saint Mary\'s', 'MSValleySt':'Mississippi Valley State',
 'WKU':'Western Kentucky', 'CSNorthridge':'Cal State Northridge', 'ArkPineBluff':'Arkansas-Pine Bluff',
 'SamHoustonSt':'Sam Houston', 'Detroit':'Detroit Mercy', 'StLouis':'Saint Louis',
 'FLGulfCoast':'Florida Gulf Coast', 'Mississippi':'Ole Miss', 'CoastalCar':'Coastal Carolina',
 'CalPolySLO':'Cal Poly', 'Massachusetts':'UMass', 'ULL':'Louisiana', 'WIGreenBay':'Green Bay',
 'ColCharleston':'Charleston', 'FDickinson':'Fairleigh Dickinson', 'FLAtlantic':'Florida Atlantic',
 'McNeeseSt':'McNeese',
 'Connecticut':'UConn', 'KansasSt':'Kansas State', 'MichiganSt':'Michigan State',
 'OhioSt':'Ohio State', 'OklahomaSt':'Oklahoma State', 'FloridaSt':'Florida State',
 'OregonSt':'Oregon State', 'SanDiegoSt':'San Diego State', 'IowaSt':'Iowa State',
 'WichitaSt':'Wichita State', 'PennSt':'Penn State', 'ArizonaSt':'Arizona State',
 'ColoradoSt':'Colorado State', 'BoiseSt':'Boise State', 'UtahSt':'Utah State',
 'NewMexicoSt':'New Mexico State', 'NorthDakotaSt':'North Dakota State',
 'SouthDakotaSt':'South Dakota State', 'GeorgiaSt':'Georgia State',
 'ClevelandSt':'Cleveland State', 'NorfolkSt':'Norfolk State', 'MoreheadSt':'Morehead State',
 'WeberSt':'Weber State', 'MurraySt':'Murray State', 'JacksonvilleSt':'Jacksonville State',
 'MontanaSt':'Montana State', 'WrightSt':'Wright State', 'KennesawSt':'Kennesaw State',
 'EWashington':'Eastern Washington', 'ETennesseeSt':'East Tennessee State',
 'MiddleTennesseeSt':'Middle Tennessee', 'MiddleTennessee':'Middle Tennessee',
 'NCState':'NC State', 'NCarolinaSt':'NC State', 'UNCGreensboro':'UNC Greensboro',
 'NCAsheville':'UNC Asheville', 'UNCAsheville':'UNC Asheville', 'NCWilmington':'UNC Wilmington',
 'UNCWilmington':'UNC Wilmington', 'VACommonwealth':'VCU', 'LoyolaChicago':'Loyola Chicago',
 'SaintMarys':'Saint Mary\'s', 'StMarys':'Saint Mary\'s', 'StPeters':'Saint Peter\'s',
 'StJosephs':'Saint Joseph\'s', 'StBonaventure':'St. Bonaventure',
 'TXSouthern':'Texas Southern', 'TexasAM':'Texas A&M', 'TAMUCorpusChristi':'Texas A&M-Corpus Christi',
 'TXAMCorpusChristi':'Texas A&M-Corpus Christi', 'UTSanAntonio':'UTSA', 'UTArlington':'UT Arlington',
 'ArkLittleRock':'Little Rock', 'ARLittleRock':'Little Rock', 'MiamiFL':'Miami',
 'MiamiOhio':'Miami (OH)', 'MiamiOH':'Miami (OH)', 'CalBaptist':'California Baptist',
 'CalStFullerton':'Cal State Fullerton', 'CalStNorthridge':'Cal State Northridge',
 'SantaBarbara':'UC Santa Barbara', 'UCSantaBarbara':'UC Santa Barbara', 'UCIrvine':'UC Irvine',
 'LongBeachSt':'Long Beach State', 'FresnoSt':'Fresno State', 'CSBakersfield':'Cal State Bakersfield',
 'SouthernMiss':'Southern Miss', 'SEMissouriSt':'Southeast Missouri State',
 'SELouisiana':'SE Louisiana', 'NWState':'Northwestern State',
 'NWLouisiana':'Northwestern State', 'AppalachianSt':'App State', 'AppalachianState':'App State',
 'CollCharleston':'Charleston', 'Charleston':'Charleston', 'StFrancisPA':'Saint Francis',
 'SaintFrancisPA':'Saint Francis', 'FairleighDickinson':'Fairleigh Dickinson',
 'Albany':'UAlbany', 'LIUBrooklyn':'Long Island University', 'LIU':'Long Island University',
 'Southern':'Southern', 'SouthernU':'Southern', 'WesternKentucky':'Western Kentucky',
}


def norm(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def download_schedules(years, allow_refresh=False):
    cache = ROOT / 'data/raw'
    cache.mkdir(parents=True, exist_ok=True)
    coverage_path=ROOT/'data/derived/schedule_coverage.json'
    pinned={r['season']:r['sha256'] for r in read(coverage_path)['seasons']} if coverage_path.exists() else {}
    def fetch(year):
        name = f'mbb_schedule_{year}.parquet'
        path = cache / name
        if not path.exists():
            req = urllib.request.Request(BASE + name, headers={'User-Agent':'MarchMadnessPredictor/1.0'})
            with urllib.request.urlopen(req, timeout=90) as response:
                blob = response.read(10_000_001)
            if len(blob) > 10_000_000:
                raise ValueError('Unexpectedly large schedule asset')
            if year in pinned and hashlib.sha256(blob).hexdigest()!=pinned[year] and not allow_refresh:
                raise ValueError(f'Source checksum changed for {year}; preserve the bundled features or explicitly use --refresh-source and reevaluate.')
            path.write_bytes(blob)
        if year in pinned and hashlib.sha256(path.read_bytes()).hexdigest()!=pinned[year] and not allow_refresh:
            raise ValueError(f'Cached source checksum changed for {year}')
        return year
    with ThreadPoolExecutor(max_workers=4) as pool:
        for year in pool.map(fetch, years):
            print(f'cached schedule {year}', flush=True)


def build_features():
    archive = read(ROOT / 'data/derived/archive.json')
    features, coverage = {}, []
    for path in sorted((ROOT / 'data/raw').glob('mbb_schedule_*.parquet')):
        year = int(path.stem.rsplit('_',1)[1])
        columns = ['id','date','home_id','away_id','home_location','away_location',
                   'home_display_name','away_display_name','home_short_display_name','away_short_display_name',
                   'home_score','away_score','neutral_site','status_type_name','status_type_completed']
        rows = pq.read_table(path,columns=columns).to_pylist()
        cutoff = f'{year}-03-01T00:00:00+00:00'
        ids, names = {}, {}
        states, seen, used = {}, set(), 0
        for g in sorted(rows, key=lambda r:(str(r['date']), str(r['id']))):
            dt = datetime.fromisoformat(str(g['date']).replace('Z','+00:00'))
            if dt >= datetime.fromisoformat(cutoff):
                continue
            for side in ('home', 'away'):
                for key in ('location', 'display_name', 'short_display_name'):
                    label = g.get(f'{side}_{key}')
                    if label:
                        ids.setdefault(norm(label), set()).add(str(g[f'{side}_id']))
                names[str(g[f'{side}_id'])] = g.get(f'{side}_location')
            if g.get('status_type_name') != 'STATUS_FINAL' or not g.get('status_type_completed'):
                continue
            h, a = str(g['home_id']), str(g['away_id'])
            hs, aws = g.get('home_score'), g.get('away_score')
            if hs is None or aws is None or hs == aws:
                continue
            game_id = str(g['id'])
            if game_id in seen:
                raise ValueError(f'Duplicate schedule game {game_id}')
            seen.add(game_id)
            for t in (h,a):
                states.setdefault(t, dict(elo=1500., n=0, wins=0, margin_total=0.))
            home, away = states[h], states[a]
            offset = 0 if g.get('neutral_site') else 60
            expected = 1/(1+10**((away['elo']-home['elo']-offset)/400))
            delta = 20*(float(hs>aws)-expected)
            home['elo'] += delta
            away['elo'] -= delta
            for state, margin in ((home,hs-aws),(away,aws-hs)):
                state['n'] += 1
                state['wins'] += int(margin>0)
                state['margin_total'] += margin
            used += 1
        mapped, missing = {}, []
        for t in archive.get(str(year), {}).get('teams', []):
            name = SEASON_ALIASES.get(year,{}).get(t['id'],ALIASES.get(t['id'], t['id']))
            aliases = name if isinstance(name,list) else [name]
            candidates = set().union(*(ids.get(norm(n),set()) for n in aliases))
            if len(candidates)!=1:
                missing.append(dict(team=t['id'], reason='no unambiguous exact name crosswalk'))
                continue
            tid = next(iter(candidates))
            state = states.get(tid)
            if state is None or state['n'] < 10:
                missing.append(dict(team=t['id'], reason='fewer than 10 pre-March completed games'))
                continue
            mapped[t['id']] = dict(espn_id=tid, source_name=names[tid], elo=state['elo'],
                                  games=state['n'], win_rate=state['wins']/state['n'],
                                  margin=state['margin_total']/state['n'], cutoff_utc=cutoff)
        features[str(year)] = mapped
        coverage.append(dict(season=year, source_rows=len(rows), pre_cutoff_games=used,
                             mapped_main_bracket_teams=len(mapped), missing=missing, cutoff_utc=cutoff,
                             source_url=BASE+path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    dump(ROOT / 'data/derived/team_features.json', features)
    cross_checks=[]
    for entry in coverage:
        year=entry['season']
        if str(year) not in archive:
            continue
        path=ROOT/'data/raw'/f'mbb_schedule_{year}.parquet'
        cols=['id','date','home_id','away_id','home_score','away_score','status_type_name','notes_headline','tournament_id']
        schedule=pq.read_table(path,columns=cols).to_pylist()
        checked=0
        for g in archive[str(year)]['games']:
            fa=features[str(year)].get(g['a']);fb=features[str(year)].get(g['b'])
            if not fa or not fb:
                continue
            expected={fa['espn_id'],fb['espn_id']}
            candidates=[r for r in schedule if {str(r['home_id']),str(r['away_id'])}==expected
                        and (r.get('tournament_id')==22 or 'NCAA' in str(r.get('notes_headline')))
                        and str(r['date'])>f'{year}-03-01']
            if len(candidates)!=1:
                continue
            r=candidates[0]
            if g['status']=='no_contest':
                g['date_utc']=r['date']
                continue
            if r['status_type_name']!='STATUS_FINAL' or r['home_score'] is None or r['away_score'] is None:
                continue
            a_home=str(r['home_id'])==fa['espn_id']
            sa,sb=(r['home_score'],r['away_score']) if a_home else (r['away_score'],r['home_score'])
            if (g['a'] if sa>sb else g['b'])!=g['winner'] or sa==sb:
                raise ValueError(f"Independent source winner mismatch: {g['id']}")
            g.update(score_a=sa,score_b=sb,date_utc=r['date'],schedule_game_id=str(r['id']),
                     result_source=BASE+path.name)
            checked+=1
        cross_checks.append(dict(season=year,played_results_cross_checked=checked))
        for team in archive[str(year)]['teams']:
            if team['id'] in features[str(year)]:
                team['name']=features[str(year)][team['id']]['source_name']
    dump(ROOT/'data/derived/archive.json',archive)
    provenance=read(ROOT/'data/derived/provenance.json')
    provenance.update(score_date_enrichment=dict(source='SportsDataverse / ESPN',license='CC BY 4.0',
                      cross_checks=cross_checks,results_with_scores=sum(r['played_results_cross_checked'] for r in cross_checks)),
                      missing_fields=['scores/dates before 2006 and any unmatched later games',
                                      'venues','geographic region names','preliminary-round games','preliminary-round losers'])
    dump(ROOT/'data/derived/provenance.json',provenance)
    dump(ROOT / 'data/derived/schedule_coverage.json', dict(
        publisher='SportsDataverse hoopR-mbb-data authors', upstream='ESPN', license='CC BY 4.0',
        license_url='https://creativecommons.org/licenses/by/4.0/',
        publisher_license_url='https://github.com/sportsdataverse/hoopR-mbb-data/blob/main/LICENSE.md',
        changes='Extracted completed games before March 1; derived within-season Elo, win rate and mean margin.',
        retrieval_date='2026-10-03', seasons=coverage,
        caveat='Historical schedules are retrieved retrospectively. Source corrections may postdate games. No claim of complete NCAA regular-season coverage.'))
    return coverage
