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

swe.set_ephe_path('.')

def get_geo_and_tz(city_name):
    geo = Nominatim(user_agent="astro_gpt").geocode(city_name)
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=geo.longitude, lat=geo.latitude)
    return geo.latitude, geo.longitude, tz_name

def get_moon_phase(julian_day):
    sun_long = swe.calc_ut(julian_day, swe.SUN)[0][0]
    moon_long = swe.calc_ut(julian_day, swe.MOON)[0][0]
    diff = moon_long - sun_long
    if diff < 0:
        diff += 360
    phase = (1 - math.cos(math.radians(diff))) / 2
    return phase, diff

def generate_chart(name, birth_date, birth_time, birth_place):
    lat, lon, tz_name = get_geo_and_tz(birth_place)
    tz = pytz.timezone(tz_name)
    dt_naive = datetime.datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
    dt_local = tz.localize(dt_naive)
    date_str = dt_local.strftime("%Y/%m/%d")
    time_str = dt_local.strftime("%H:%M")
    pos = GeoPos(str(lat), str(lon))
    date_obj = Datetime(date_str, time_str, tz_name)
    chart = Chart(date_obj, pos)
    planets = [const.SUN, const.MOON, const.MERCURY, const.VENUS, const.MARS,
               const.JUPITER, const.SATURN, const.URANUS, const.NEPTUNE, const.PLUTO]
    birth_data = {planet: chart.get(planet).sign for planet in planets}
    julian_day = swe.julday(dt_local.year, dt_local.month, dt_local.day,
                            dt_local.hour + dt_local.minute / 60.0)
    moon_phase_fraction, moon_angle = get_moon_phase(julian_day)
    if moon_angle < 45:
        moon_phase_name = "New Moon"
    elif moon_angle < 90:
        moon_phase_name = "First Quarter"
    elif moon_angle < 135:
        moon_phase_name = "Waxing Gibbous"
    elif moon_angle < 180:
        moon_phase_name = "Full Moon"
    elif moon_angle < 225:
        moon_phase_name = "Waning Gibbous"
    elif moon_angle < 270:
        moon_phase_name = "Last Quarter"
    else:
        moon_phase_name = "Waning Crescent"
    return {
        "name": name,
        "birth_place": birth_place,
        "birth_time": birth_time,
        "chart": birth_data,
        "moon_phase": moon_phase_name,
        "moon_phase_angle": round(moon_angle, 2),
        "moon_phase_fraction": round(moon_phase_fraction, 3)
    }

def interpret_chart_with_gpt(chart_data, api_key):
    openai.api_key = api_key
    chart_text = "\n".join([f"{planet}: {sign}" for planet, sign in chart_data['chart'].items()])
    prompt = f"""
    Name: {chart_data['name']}
    Birthplace: {chart_data['birth_place']}
    Birth Time: {chart_data['birth_time']}
    Birth Chart:
    {chart_text}
    Moon Phase: {chart_data['moon_phase']}
    Write a friendly astrological interpretation in 2 paragraphs.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content
