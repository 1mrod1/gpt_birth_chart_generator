from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const
from geopy.geocoders import Nominatim
import requests, pytz, datetime, swisseph as swe, math, openai

swe.set_ephe_path('.')  # Ensure ephemeris data is available here

def get_geo_and_tz(city):
    geo = Nominatim(user_agent='astro_gpt').geocode(city)
    if not geo:
        raise ValueError(f'Location not found: {city}')
    resp = requests.get(
        'https://timeapi.io/api/TimeZone/coordinate',
        params={'latitude': geo.latitude, 'longitude': geo.longitude}
    )
    resp.raise_for_status()
    tz = resp.json().get('timeZone')
    if not tz:
        raise ValueError('Timezone lookup failed')
    return geo.latitude, geo.longitude, tz

def get_moon_phase(jd):
    sun = swe.calc_ut(jd, swe.SUN)[0][0]
    moon = swe.calc_ut(jd, swe.MOON)[0][0]
    diff = (moon - sun) % 360
    frac = (1 - math.cos(math.radians(diff))) / 2
    return frac, diff

def generate_chart(name, bd, bt, bp):
    lat, lon, tzname = get_geo_and_tz(bp)
    tz = pytz.timezone(tzname)
    dt = datetime.datetime.strptime(f"{bd} {bt}", "%Y-%m-%d %H:%M")
    loc = tz.localize(dt)

    date = loc.strftime("%Y/%m/%d")
    time = loc.strftime("%H:%M")
    off = loc.strftime("%z")  # e.g. "-0700"
    off = f"{off[:3]}:{off[3:]}"  # "-07:00"

    pos = GeoPos(lat, lon)
    dobj = Datetime(date, time, off)
    chart_obj = Chart(dobj, pos)

    planets = [
        const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS,
        const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO
    ]
    data = {p: chart_obj.get(p).sign for p in planets}

    jd = swe.julday(loc.year, loc.month, loc.day,
                    loc.hour + loc.minute / 60.0)
    frac, ang = get_moon_phase(jd)
    phases = [
        "New Moon", "First Quarter", "Waxing Gibbous", "Full Moon",
        "Waning Gibbous", "Last Quarter", "Waning Crescent"
    ]
    idx = int((ang % 360) // 45)
    phase = phases[idx]

    return {
        "chart": data,
        "moon_phase": phase,
        "moon_phase_angle": round(ang, 2),
        "name": name
    }

def interpret_chart_with_gpt(chart_data, api_key):
    openai.api_key = api_key
    lines = "\n".join(f"{k}: {v}" for k, v in chart_data["chart"].items())
    prompt = (
        f"Name: {chart_data['name']}\n"
        "Birth Chart:\n" + lines + "\n"
        f"Moon Phase: {chart_data['moon_phase']}\n\n"
        "Write a friendly 2-paragraph astro interpretation."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return resp.choices[0].message.content