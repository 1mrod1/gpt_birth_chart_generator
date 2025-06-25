from flask import Flask, render_template, request, make_response
import traceback, os
from chart_engine import generate_chart, interpret_chart_with_gpt

app = Flask(__name__)

@app.errorhandler(Exception)
def show_traceback(exc):
    return make_response(f"<pre>{traceback.format_exc()}</pre>", 500)

@app.route('/', methods=['GET','POST'])
def index():
    full_name = chart = moon_phase = moon_phase_angle = interpretation = error = ""
    if request.method == 'POST':
        full_name = request.form.get('name','')
        bd = request.form.get('birth_date','')
        bt = request.form.get('birth_time','')
        bp = request.form.get('birth_place','')
        try:
            raw = generate_chart(full_name, bd, bt, bp)
            chart = raw.get('chart',{})
            moon_phase = raw.get('moon_phase','')
            moon_phase_angle = raw.get('moon_phase_angle','')
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                interpretation = interpret_chart_with_gpt(raw, api_key)
        except Exception as e:
            error = str(e)
    return render_template('index.html',
        full_name=full_name,
        chart=chart,
        moon_phase=moon_phase,
        moon_phase_angle=moon_phase_angle,
        interpretation=interpretation,
        error=error
    )

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))