from flask import Flask, render_template, request, session, redirect, url_for
import numpy as np
from scipy import stats
import plotly.graph_objs as go
import plotly.io as pio
import json

app = Flask(__name__)
app.secret_key = 'a_very_secure_random_key_12345'

# Game constants
BASE_CONVERSION_RATE = 0.05
DAILY_TRAFFIC = 1000
TEST_COST_PER_DAY = 100
IMPLEMENTATION_COST = 500
REVENUE_PER_CONVERSION = 10
TOTAL_DAYS = 30
BUDGET = 1000

ELEMENTS = {
    'button_color': {'red': 0.01, 'green': -0.005},
    'headline': {'Limited Offer': 0.02, 'Exclusive Deal': 0.015},
    'image': {'image2': 0.005, 'image3': -0.01}
}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    session['day'] = 0
    session['budget'] = BUDGET
    session['current_conversion_rate'] = BASE_CONVERSION_RATE
    session['implemented_changes'] = {}
    session['total_revenue'] = 0
    session['tests'] = []
    return redirect(url_for('game'))

@app.route('/game')
def game():
    if 'day' not in session:
        return redirect(url_for('home'))
    return render_template('game.html', day=session['day'], budget=session['budget'],
                           conversion_rate=session['current_conversion_rate']*100,
                           total_revenue=session['total_revenue'])

@app.route('/run_test', methods=['GET', 'POST'])
def run_test():
    print(f"Received {request.method} request to /run_test")
    elements = ELEMENTS
    if request.method == 'POST':
        element = request.form['element']
        variant = request.form['variant']
        days = int(request.form['days'])
        cost = days * TEST_COST_PER_DAY

        if session['budget'] < cost or session['day'] + days > TOTAL_DAYS:
            return render_template('error.html', message="Insufficient budget or time.")

        control_rate = session['current_conversion_rate']
        variant_rate = control_rate + ELEMENTS[element][variant]
        control_conversions = np.random.binomial(DAILY_TRAFFIC // 2, control_rate, days).sum()
        variant_conversions = np.random.binomial(DAILY_TRAFFIC // 2, variant_rate, days).sum()
        control_visitors = (DAILY_TRAFFIC // 2) * days
        variant_visitors = (DAILY_TRAFFIC // 2) * days

        contingency_table = [[control_conversions, control_visitors - control_conversions],
                             [variant_conversions, variant_visitors - variant_conversions]]
        chi2, p_value, _, _ = stats.chi2_contingency(contingency_table)

        test_result = {
            'element': element,
            'variant': variant,
            'days': days,
            'control_conversions': control_conversions,
            'variant_conversions': variant_conversions,
            'control_visitors': control_visitors,
            'variant_visitors': variant_visitors,
            'p_value': p_value
        }
        session['tests'].append(test_result)
        session['budget'] -= cost
        session['day'] += days
        revenue_during_test = (control_conversions + variant_conversions) * REVENUE_PER_CONVERSION
        session['total_revenue'] += revenue_during_test

        return redirect(url_for('results', test_id=len(session['tests']) - 1))
    return render_template('run_test.html', elements=ELEMENTS)

# Other routes (results, implement_change) omitted for brevity...

if __name__ == '__main__':
    app.run(debug=True)