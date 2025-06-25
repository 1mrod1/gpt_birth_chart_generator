from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const
from geopy.geocoders import Nominatim
import requests, pytz, datetime, swisseph as swe, math, openai

swe.set_ephe_path('.')  # Ensure ephemeris data is here

def get_geo_and_tz(city):
    geo = Nominatim(user_agent='astro').geocode(city)
    if not geo:
        raise ValueError('Location not found')
    r = requests.get('https://timeapi.io/api/TimeZone/coordinate',
                     params={'latitude': geo.latitude, 'longitude': geo.longitude})
    r.raise_for_status()
    tz = r.json().get('timeZone')
    if not tz:
        raise ValueError('Timezone error')
    return geo.latitude, geo.longitude, tz

def get_moon_phase(jd):
    s = swe.calc_ut(jd, swe.SUN)[0][0]
    m = swe.calc_ut(jd, swe.MOON)[0][0]
    d = (m - s) % 360
    return (1 - math.cos(math.radians(d))) / 2, d

def generate_chart(name, bd, bt, bp):
    lat, lon, tzname = get_geo_and_tz(bp)
    tz = pytz.timezone(tzname)
    dt = datetime.datetime.strptime(f"{bd} {bt}", '%Y-%m-%d %H:%M')
    loc = tz.localize(dt)
    date, time = loc.strftime('%Y/%m/%d'), loc.strftime('%H:%M')
    off = loc.strftime('%z'); off = f"{off[:3]}:{off[3:]}"
    pos = GeoPos(lat, lon)
    dobj = Datetime(date, time, off)
    chart = Chart(dobj, pos)
    planets = [const.SUN,const.MOON,const.MERCURY,const.VENUS,const.MARS,
               const.JUPITER,const.SATURN,const.URANUS,const.NEPTUNE,const.PLUTO]
    data = {p: chart.get(p).sign for p in planets}
    jd = swe.julday(loc.year, loc.month, loc.day, loc.hour + loc.minute/60)
    frac, ang = get_moon_phase(jd)
    phases = ["New Moon","First Quarter","Waxing Gibbous","Full Moon",
              "Waning Gibbous","Last Quarter","Waning Crescent"]
    idx = int((ang % 360)//45)
    return {'chart':data, 'moon_phase':phases[idx], 'moon_phase_angle':round(ang,2), 'name':name}

def interpret_chart_with_gpt(data, key):
    openai.api_key = key
    lines = '\\n'.join([f\"{k}: {v}\" for k,v in data['chart'].items()])
    prompt = f\"Name: {data['name']}\\nBirth Chart:\\n{lines}\\nMoon: {data['moon_phase']}\\nInterpret in 2 paragraphs.\"
    res = openai.ChatCompletion.create(model='gpt-4',
        messages=[{'role':'user','content':prompt}], temperature=0.7)
    return res.choices[0].message.content