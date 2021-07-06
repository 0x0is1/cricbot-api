import requests
#from bs4 import BeautifulSoup as bs
import io
import matplotlib.pyplot as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from math import cos, sin, radians

def urlprov(ids: str, urlindex: int, ptype: str, inning_index: int, mformat: str, dtype: str):
    base_url = 'https://cricket.yahoo.net/sifeeds/cricket/live/json/'
    url = {
        0: base_url + ids + '.json',
        1: base_url + ids + '_' + ptype + '_splits_'+str(inning_index)+'.json',
        2: 'https://cricket.yahoo.net/sifeeds/cricket/static/json/iccranking-' + mformat+'-'+dtype+'.json',
    }[urlindex]
    return url

def fetch(url):
    return requests.get(url).json()

def schedule(limit: int, raw_data: dict):
    data = []
    team_names: str = lambda item_type, match_index, inning_id: raw_data[
        'matches'][match_index]['participants'][inning_id][item_type]
    event_fetch: str = lambda match_index, item_type: raw_data['matches'][match_index][item_type]
    for i in range(limit):
        try:
            team_names('name', i, 0)
        except(IndexError, KeyError):
            break
        data.append((
            team_names('name', i, 0),
            team_names('name', i, 1),
            team_names('id', i, 0),
            team_names('id', i, 1),
            event_fetch(i, 'series_name'),
            event_fetch(i, 'start_date').split('T')[1],
            event_fetch(i, 'event_sub_status'),
            event_fetch(i, 'start_date').split('T')[0],
            event_fetch(i, 'venue_name'),
            event_fetch(i, 'game_id')
            )
        )
    return data

def miniscore(inning_id: int, data: dict):
    inning = data['Innings'][inning_id]
    teams = data['Teams']
    md = data['Matchdetail']
    try:
        a=md['Result']
    except Exception:
        a=md['Status']
    return (
        md['Match']['Date'],
        md['Match']['Offset'].replace('+', ''),
        md['Series']['Series_short_display_name'],
        md['Venue']['Name'],
        inning['Total'],
        inning['Wickets'],
        inning['Overs'],
        teams[inning['Battingteam']]['Name_Short'],
        teams[inning['Bowlingteam']]['Name_Short'],
        a
    )

def fetch_team(team_id: str):
    return requests.get('https://cricket.yahoo.net/sifeeds/cricket/static/json/' + str(team_id) + '_team.json').json()


def playercard(team_id: str, player_id: str, raw_data: dict, data_id: int):
    player = raw_data['Teams'][team_id]['Players'][player_id]
    bt, bl = player['Batting'], player['Bowling']
    en = [('Style', 'Average', 'Strikerate', 'Runs'),('Style', 'Average', 'Economyrate', 'Wickets')][data_id]
    dta = [(bt['Style'], bt['Average'], bt['Strikerate'], bt['Runs']),
           (bl['Style'], bl['Average'], bl['Economyrate'], bl['Wickets'])][data_id]

    return player['Name_Full'], player['Matches'], en, dta


def scorecard(inning_id: int, data: dict):
    btsb, blsb = [], []
    inning = data['Innings'][inning_id]
    batsmen = inning['Batsmen']
    bowler = inning['Bowlers']
    btteam_id = inning['Battingteam']
    blteam_id = inning['Bowlingteam']
    btplayer = data['Teams'][btteam_id]['Players']
    blplayer = data['Teams'][blteam_id]['Players']
    btteam_name = data['Teams'][btteam_id]['Name_Short']
    blteam_name = data['Teams'][blteam_id]['Name_Short']

    for i in batsmen:
        name=(btplayer[i['Batsman']]['Name_Full']).split(' ')[-1]
        if i['Howout'] == 'Batting':
            name += '*'
        btsb.append((name,i['Runs'], i['Balls'], i['Fours'],
                     i['Sixes'], i['Dots'], i['Strikerate']))
    for i in bowler:
        blsb.append(((blplayer[i['Bowler']]['Name_Full']).split(' ')[-1], i['Runs'],i['Overs'],
                     i['Maidens'], i['Wickets'], i['Noballs'], i['Wides'], i['Dots'], i['Economyrate']))
    return btsb, blsb, btteam_name, blteam_name


def team_pl(team_id: str, raw_data: dict):
    players, pls = raw_data['Teams'][team_id]['Players'], []
    for i in players:
        try:
            players[str(i)]['Iscaptain']
            c = ' (c)'
        except KeyError:
            c = ''
        try:
            players[str(i)]['Iskeeper']
            k = ' (k)'
        except KeyError:
            k = ''
        pls.append((players[str(i)]['Name_Full'], c, k))
    return pls


def fow(inning_id: int, raw_data: dict):
    sc = raw_data['Innings'][inning_id]
    fw = sc['FallofWickets']
    team_id = sc['Battingteam']
    team_name = raw_data['Teams'][team_id]['Name_Full']
    score = str(sc['Total'])+'/'+str(sc['Wickets'])+' '+str(sc['Overs'])
    o, s = [], []
    for i in fw:
        o.append(float(i['Overs']))
        s.append(int(i['Score']))
    mp.xticks(np.arange(0, int(o[len(o)-1]+100), step=5))
    mp.yticks(np.arange(0, int(s[len(s)-1]+100), step=15))
    mp.title('Fall of wicket: '+team_name+' ('+score+')', fontsize=14)
    mp.xlabel('Overs', fontsize=14)
    mp.ylabel('Runs', fontsize=14)
    mp.plot(o, s, color='red', marker='o', linewidth=3,
            markerfacecolor='red', markersize=8, label='Wickets')
    for i in range(len(o)):
        mp.annotate('('+str(s[i])+'-'+str(o[i])+')',
                    (o[i]+0.1, s[i]-2), fontsize=7)
    s.append(int(sc['Total']))
    o.append(float(sc['Overs']))
    mp.plot(o, s, color='blue', label='Runs')
    mp.legend(loc='lower right')
    fig = mp.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    mp.cla()
    return buf


def powerplay(inning_id: int, raw_data: dict):
    a, pwp = [], raw_data['Innings'][inning_id]['PowerPlayDetails']
    for i in pwp:
        a.append((i['Name'], i['Overs'], i['Runs'], i['Wickets']))
    return a


def lastovers(inning_id: int, raw_data: dict):
    lsov, a = raw_data['Innings'][inning_id]['LastOvers'], []
    for i in lsov:a.append((i, lsov[i]['Score'],
    lsov[i]['Wicket'], lsov[i]['Runrate']))
    return a


def partnership(inning_id: int, raw_data: dict):
    sc = raw_data['Innings'][inning_id]
    x, runs, balls = [], [], []
    team_id = sc['Battingteam']
    plr = raw_data['Teams'][team_id]['Players']
    psp = sc['Partnerships']
    team_name = raw_data['Teams'][team_id]['Name_Full']
    score = str(sc['Total'])+'/'+str(sc['Wickets'])+' '+str(sc['Overs'])
    for i in psp:
        def b(a): return plr[i['Batsmen'][a]
                             ['Batsman']]['Name_Full'].split(' ')[-1]
        x.append(b(0)+'\n'+b(1))
        runs.append(int(i['Runs']))
        balls.append(int(i['Balls']))
    x_pos = [i for i, _ in enumerate(x)]
    mp.bar(x_pos, runs, color='blue', width=0.7)
    mp.xlabel("Partners")
    mp.ylabel("Runs")
    mp.title("Partnerships: "+team_name+' '+str(score))
    mp.xticks(x_pos, x, fontsize=7)
    r = sorted(runs)
    highest_score = int(r[len(runs)-1])
    mp.yticks(np.arange(0, highest_score+10, step=15))
    for i in range(len(runs)):
        mp.annotate(str(runs[i])+' in ' +
                    str(balls[i]), (x_pos[i]-0.3, runs[i]+1), fontsize=8)
    fig = mp.gcf()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    mp.cla()
    return buf


def player_againstcard(player_index: int, raw_data: dict, is_batsman: bool):
    if is_batsman:
        c, d, e, f = 'Strikerate', 'Batsmen', 'Bowler', 'Batsman'
    else:
        c, d, e, f = 'Economyrate', 'Bowlers', 'Batsman', 'Bowler'
    team=list(raw_data[d])
    pl = raw_data[d][team[player_index]]
    ag, a = pl['Against'], []
    for i in ag:
        k = ag[i]
        a.append((str(k[e]).split(' ')[1], k['Runs'],
                  k['Balls'], k['Fours'], k['Sixes'], k['Dots'], k[c]))
    return pl[f], a

def get_color(index: str):
    return {'0':'white', '1': 'orange', '2': 'purple', '3': 'brown',
            '4': 'green', '6': 'blue', 'wicket': 'red'}[index]

def shotsfig_bt(player_index: int, raw_data: dict):
    psid = list(raw_data['Batsmen'])
    name= raw_data['Batsmen'][psid[player_index-1]]['Batsman']
    shots = raw_data['Batsmen'][psid[player_index-1]]['Shots']
    BATS_POS = (496, 470)
    UNIT_DIS = 110
    distance= lambda k: int(k['Distance'])*UNIT_DIS
    im = Image.open("./res/field.jpg")
    legend_image =Image.open("./res/legend-1.png")
    d = ImageDraw.Draw(im)
    for i in shots:
        X = (distance(i)*cos(radians(int(i['Angle'])+90)))+BATS_POS[0]
        Y = (distance(i)*sin(radians(int(i['Angle'])+90)))+BATS_POS[1]
        d.line([(X, Y), BATS_POS], fill=get_color(i['Runs']), width=4)
        d.text((X, Y), i['Runs'], fill='black')
    im.paste(legend_image, (0,0))
    buf = io.BytesIO()
    im.save(buf, format='jpeg')
    buf.seek(0)
    return name, buf

def shotsfig_bl(player_index:int, raw_data):
    psid = list(raw_data['Bowlers'])
    pitch = raw_data['Bowlers'][psid[player_index]]['Pitches']
    name= raw_data['Bowlers'][psid[player_index-1]]['Bowler']
    UNIT_DIS = 2
    pseudo_originX, pseudo_originY=75,20
    ball_len, ball_wid = 18,10
    im=Image.open('./res/pitchmap.png')
    legend_image =Image.open("./res/legend-2.png")
    d = ImageDraw.Draw(im)
    #75,20,250,310
    for i in pitch:
        a=i['XY'].split(',')
        try: 
            i['Iswicket']
            iswicket=True
        except Exception:
            iswicket=False
        X1=(pseudo_originX+int(a[1]))*UNIT_DIS-20
        Y1=(pseudo_originY+int(a[0]))*UNIT_DIS
        if iswicket:
            runs='wicket'
        else:
            runs=i['Runs']
        d.ellipse(((X1, Y1), (X1+ball_len, Y1+ball_wid)), fill=get_color(runs), outline='yellow')
    im.paste(legend_image, (0,0))    
    buf = io.BytesIO()
    im.save(buf, format='png')
    buf.seek(0)
    return name, buf
        
def leaderboard(raw_data: dict, count:int):
    r, a = raw_data['bat-rank']['rank'], []
    for i in range(count):
        a.append((r[i]['no'],r[i]['Player-name'],r[i]['Country'], r[i]['Points'], r[i]['careerbest']))
    return a

def curr_partnership(raw_data, inning_id):
    btteam_id = raw_data['Innings'][inning_id]['Battingteam']
    pshipc = raw_data['Innings'][inning_id]['Partnership_Current']
    btplayer = raw_data['Teams'][btteam_id]['Players']
    name1=(btplayer[pshipc['Batsmen'][0]['Batsman']]['Name_Full']).split(' ')[-1]
    name2=(btplayer[pshipc['Batsmen'][1]['Batsman']]['Name_Full']).split(' ')[-1]
    return (
        pshipc['Runs'],
        pshipc['Balls'],
        name1,
        pshipc['Batsmen'][0]['Runs'],
        pshipc['Batsmen'][0]['Balls'],
        name2,
        pshipc['Batsmen'][1]['Runs'],
        pshipc['Batsmen'][1]['Balls'],
    )

def stamp_generator(player_name, team_name):
    im = Image.open("./res/stamp.png")
    font_path='./res/DejaVuSansCondensed-Bold.ttf'
    d=ImageDraw.Draw(im)
    d.text((26,12), player_name, font=ImageFont.truetype(font_path, 12))
    d.text((50,37), team_name, font=ImageFont.truetype(font_path, 12))
    return im

def fi_image_generator(raw_data, fantasy_type):
    store={1:[], 2:[], 3:[], 4:[]}
    ic={1:'BAT', 2:'BOWL', 3:'AR', 4:'WK'}
    cap, vice_cap='', ''
    for i in raw_data['players']:
        if i['is_'+fantasy_type]:
            if i['skill_id'] in (1, 2, 3, 4) :
                if i['is_'+fantasy_type+'_captain']:cap=' [C] '
                else:cap=''
                if i['is_'+fantasy_type+'_vice_captain']:vice_cap=' [VC] '
                else:vice_cap=''
                im=stamp_generator(i['player_name'], str(i['team_short_name']+' ['+ic[i['skill_id']]+']'+cap+vice_cap).upper())
                con=requests.get('https://cricket.yahoo.net/static-assets/players/min/{}.png?v=1.22&w=50'.format(str(i['player_id']))).content
                buf= io.BytesIO(con)
                icon=Image.open(buf)
                store[i['skill_id']].append((im, icon))
    return store

def fantasy_insight(raw_data, fantasy_type):
    base=Image.open("./res/fantasy-field.jpg")
    coords11 = [(220, 80), (40, 120), (390, 120), (90, 240), (330, 240), (40, 360), (220, 400), (390, 360), (40, 500), (220, 550), (390, 500)]
    it=0
    ims=fi_image_generator(raw_data, fantasy_type)
    for j in (4,1,3,2):
        for i in ims[j]:
            x=coords11[it][0]
            y=coords11[it][1]
            base.paste(i[0], (x, y))
            base.paste(i[1], (x+50, y-50))
            it+=1
    buf = io.BytesIO()
    base.save(buf, format='png')
    buf.seek(0)
    return buf

def name_parser(string):
    string=string.replace('(', '')
    t=string.split(' ')
    name=''
    for i in t:
        try:
            name+=i[0]
        except Exception:
            pass
    if name=='CPoI(':
        name='CPI(M)'
    return name
