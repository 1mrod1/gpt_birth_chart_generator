# chart_engine.py

from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib import const
from geopy.geocoders import Nominatim
import requests
import pytz
import datetime
import swisseph as swe
import math
import openai

swe.set_ephe_path('.')  # Ephemeris data folder

def get_geo_and_tz(city_name):
    geo = Nominatim(user_agent="astro_gpt").geocode(city_name)
    if not geo:
        raise ValueError(f"Location not found for: {city_name}")
    resp = requests.get(
        "https://timeapi.io/api/TimeZone/coordinate",
        params={"latitude": geo.latitude, "longitude": geo.longitude}
    )
    resp.raise_for_status()
    tz_name = resp.json().get("timeZone")
    if not tz_name:
        raise ValueError("Timezone not found in API response")
    return geo.latitude, geo.longitude, tz_name

def get_moon_phase(jd):
    sun_lon = swe.calc_ut(jd, swe.SUN)[0][0]
    moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
    diff = (moon_lon - sun_lon) % 360
    fraction = (1 - math.cos(math.radians(diff))) / 2
    return fraction, diff

def generate_chart(name, birth_date, birth_time, birth_place):
    # Geocode and lookup timezone
    lat, lon, tz_name = get_geo_and_tz(birth_place)
    tz = pytz.timezone(tz_name)
    # Parse and localize birth datetime
    dt = datetime.datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_local = tz.localize(dt)

    # Prepare Flatlib Datetime with UTC offset (±HH:MM)
    date_str = dt_local.strftime("%Y/%m/%d")
    time_str = dt_local.strftime("%H:%M")
    offset_raw = dt_local.strftime("%z")         # e.g. "-0700"
    tz_offset = f"{offset_raw[:3]}:{offset_raw[3:]}"  # "-07:00"

    pos = GeoPos(lat, lon)
    date_obj = Datetime(date_str, time_str, tz_offset)
    chart = Chart(date_obj, pos)

    # Collect planetary signs
    planets = [
        const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS,
        const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO
    ]
    birth_data = {p: chart.get(p).sign for p in planets}

    # Moon phase
    jd = swe.julday(
        dt_local.year, dt_local.month, dt_local.day,
        dt_local.hour + dt_local.minute / 60.0
    )
    frac, angle = get_moon_phase(jd)
    if angle < 45:
        phase_name = "New Moon"
    elif angle < 90:
        phase_name = "First Quarter"
    elif angle < 135:
        phase_name = "Waxing Gibbous"
    elif angle < 180:
        phase_name = "Full Moon"
    elif angle < 225:
        phase_name = "Waning Gibbous"
    elif angle < 270:
        phase_name = "Last Quarter"
    else:
        phase_name = "Waning Crescent"

    return {
        "chart": birth_data,
        "moon_phase": phase_name,
        "moon_phase_angle": round(angle, 2),
        "moon_phase_fraction": round(frac, 3),
        "name": name
    }

def interpret_chart_with_gpt(chart_data, api_key):
    openai.api_key = api_key
    lines = [f"{pl}: {sg}" for pl, sg in chart_data["chart"].items()]
    prompt = (
        f"Name: {chart_data['name']}\n"
        "Birth Chart:\n" + "\n".join(lines) + "\n"
        f"Moon Phase: {chart_data['moon_phase']}\n\n"
        "Write a friendly 2-paragraph astrological interpretation."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return resp.choices[0].message.content