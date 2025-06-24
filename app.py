from flask import Flask, render_template, request
from chart_engine import generate_chart, interpret_chart_with_gpt
import os

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    chart_data = None
    if request.method == "POST":
        name = request.form["name"]
        birth_date = request.form["birth_date"]
        birth_time = request.form["birth_time"]
        birth_place = request.form["birth_place"]

        try:
            chart_data = generate_chart(name, birth_date, birth_time, birth_place)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                chart_data["interpretation"] = interpret_chart_with_gpt(chart_data, api_key)
        except Exception as e:
            chart_data = {"error": str(e)}

    return render_template("index.html", chart=chart_data)

if __name__ == "__main__":
    from os import environ
    app.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))
