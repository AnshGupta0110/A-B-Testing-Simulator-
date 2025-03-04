from flask import Flask, render_template, request, session, redirect, url_for
import numpy as np
from scipy import stats
import plotly.graph_objs as go
import plotly.io as pio
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'a_very_secure_random_key_12345')

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
    session.modified = True
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
    if 'day' not in session:  # Initialize session if missing
        session['day'] = 0
        session['budget'] = BUDGET
        session['current_conversion_rate'] = BASE_CONVERSION_RATE
        session['implemented_changes'] = {}
        session['total_revenue'] = 0
        session['tests'] = []
        session.modified = True

    if request.method == 'POST':
        element = request.form['element']
        variant = request.form['variant']
        days = int(request.form['days'])
        cost = days * TEST_COST_PER_DAY

        if session['budget'] < cost or session['day'] + days > TOTAL_DAYS:
            return render_template('error.html', message="Insufficient budget or time.")

        control_rate = session['current_conversion_rate']
        variant_rate = control_rate + ELEMENTS[element][variant]
        control_conversions = int(np.random.binomial(DAILY_TRAFFIC // 2, control_rate, days).sum())
        variant_conversions = int(np.random.binomial(DAILY_TRAFFIC // 2, variant_rate, days).sum())
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
            'p_value': float(p_value)
        }
        session['tests'].append(test_result)
        session['budget'] -= cost
        session['day'] += days
        revenue_during_test = (control_conversions + variant_conversions) * REVENUE_PER_CONVERSION
        session['total_revenue'] += revenue_during_test
        session.modified = True

        return redirect(url_for('results', test_id=len(session['tests']) - 1))
    return render_template('run_test.html', elements=ELEMENTS)

@app.route('/results/<int:test_id>')
def results(test_id):
    test = session['tests'][test_id]
    control_rate = (test['control_conversions'] / test['control_visitors']) * 100
    variant_rate = (test['variant_conversions'] / test['variant_visitors']) * 100
    
    fig = go.Figure(data=[
        go.Bar(name='Control', x=['Control'], y=[control_rate]),
        go.Bar(name='Variant', x=['Variant'], y=[variant_rate])
    ])
    fig.update_layout(barmode='group')
    graph_json = pio.to_json(fig)  # Keep as string, no json.loads
    
    return render_template('results.html', test=test, control_rate=control_rate,
                          variant_rate=variant_rate, test_id=test_id, graph_json=graph_json)

@app.route('/implement_change', methods=['POST'])
def implement_change():
    test_id = int(request.form['test_id'])
    test = session['tests'][test_id]
    
    if session['budget'] < IMPLEMENTATION_COST:
        return render_template('error.html', message="Insufficient budget to implement change.")
    
    session['current_conversion_rate'] += ELEMENTS[test['element']][test['variant']]
    session['budget'] -= IMPLEMENTATION_COST
    session['implemented_changes'][test['element']] = test['variant']
    session.modified = True
    return redirect(url_for('game'))

if __name__ == '__main__':
    app.run(debug=False)
