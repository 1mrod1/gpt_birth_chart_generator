from flask import Flask, render_template, request, make_response
import traceback
import os

from chart_engine import generate_chart, interpret_chart_with_gpt

app = Flask(__name__)

# Global error handler to display full Python tracebacks in the browser
@app.errorhandler(Exception)
def show_traceback(exc):
    tb = traceback.format_exc()
    return make_response(f"<pre>{tb}</pre>", 500)

@app.route("/", methods=["GET", "POST"])
def index():
    full_name = ""
    chart = {}
    moon_phase = ""
    moon_phase_angle = ""
    interpretation = ""
    error = ""

    if request.method == "POST":
        full_name = request.form.get("name", "")
        birth_date = request.form.get("birth_date", "")
        birth_time = request.form.get("birth_time", "")
        birth_place = request.form.get("birth_place", "")

        try:
            raw = generate_chart(full_name, birth_date, birth_time, birth_place)
            chart = raw.get("chart", {})
            moon_phase = raw.get("moon_phase", "")
            moon_phase_angle = raw.get("moon_phase_angle", "")
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                interpretation = interpret_chart_with_gpt(raw, api_key)
        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        full_name=full_name,
        chart=chart,
        moon_phase=moon_phase,
        moon_phase_angle=moon_phase_angle,
        interpretation=interpretation,
        error=error
    )

if __name__ == "__main__":
    from os import environ
    # Use 0.0.0.0 so Render (or any host) can route traffic in
    app.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))