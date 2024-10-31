import os
from flask import Flask, render_template, request, jsonify
import numpy as np
import random
import matplotlib.pyplot as plt
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Use the non-GUI Agg backend

app = Flask(__name__)

# Driver ratings and information
driver_ratings = {
    'VER': {'Pace': 95, 'Racecraft': 95, 'Awareness': 94, 'Experience': 92},
    'HAM': {'Pace': 93, 'Racecraft': 96, 'Awareness': 93, 'Experience': 97},
    'LEC': {'Pace': 92, 'Racecraft': 88, 'Awareness': 86, 'Experience': 72},
    'SAI': {'Pace': 89, 'Racecraft': 90, 'Awareness': 91, 'Experience': 75},
    'NOR': {'Pace': 87, 'Racecraft': 85, 'Awareness': 84, 'Experience': 65},
    'GAS': {'Pace': 84, 'Racecraft': 86, 'Awareness': 83, 'Experience': 70},
    'STR': {'Pace': 83, 'Racecraft': 80, 'Awareness': 82, 'Experience': 66},
    'OCO': {'Pace': 82, 'Racecraft': 85, 'Awareness': 81, 'Experience': 68},
    'ZHO': {'Pace': 79, 'Racecraft': 78, 'Awareness': 80, 'Experience': 60},
    'TSU': {'Pace': 80, 'Racecraft': 89, 'Awareness': 79, 'Experience': 62},
    'PIA': {'Pace': 81, 'Racecraft': 79, 'Awareness': 81, 'Experience': 61},
    'DEV': {'Pace': 78, 'Racecraft': 76, 'Awareness': 78, 'Experience': 59},
    'HUL': {'Pace': 82, 'Racecraft': 83, 'Awareness': 80, 'Experience': 72},
    'ALB': {'Pace': 80, 'Racecraft': 82, 'Awareness': 79, 'Experience': 64},
    'MAG': {'Pace': 81, 'Racecraft': 81, 'Awareness': 82, 'Experience': 69},
    'BOT': {'Pace': 85, 'Racecraft': 84, 'Awareness': 85, 'Experience': 75},
    'SAR': {'Pace': 77, 'Racecraft': 75, 'Awareness': 77, 'Experience': 58},
    'PER': {'Pace': 89, 'Racecraft': 91, 'Awareness': 87, 'Experience': 83},
    'ALO': {'Pace': 88, 'Racecraft': 94, 'Awareness': 89, 'Experience': 98},
    'RUS': {'Pace': 90, 'Racecraft': 92, 'Awareness': 90, 'Experience': 70},
}

driver_info = {
    '1': 'VER',
    '44': 'HAM',
    '63': 'RUS',
    '11': 'PER',
    '55': 'SAI',
    '18': 'STR',
    '14': 'ALO',
    '31': 'OCO',
    '24': 'ZHO',
    '10': 'GAS',
    '16': 'LEC',
    '22': 'TSU',
    '81': 'PIA',
    '21': 'DEV',
    '27': 'HUL',
    '23': 'ALB',
    '4': 'NOR',
    '20': 'MAG',
    '77': 'BOT',
    '2': 'SAR'
}

# Prime lap times based on perfect conditions
driver_prime_times = {
    'VER': 73.79,
    'SAI': 74.25,
    'NOR': 74.49,
    'GAS': 74.74,
    'HAM': 74.32,
    'STR': 74.70,
    'OCO': 74.63,
    'HUL': 74.66,
    'ALO': 74.39,
    'PIA': 74.71,
    'PER': 74.46,
    'RUS': 74.59,
    'ZHO': 74.83,
    'DEV': 74.92,
    'TSU': 75.06,
    'BOT': 74.95,
    'MAG': 75.34,
    'ALB': 75.51,
    'LEC': 74.46,
    'SAR': 76.09
}


@app.route('/')
def index():
    return render_template('index.html', drivers=driver_info)

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    driver = data['driver']
    num_simulations = int(data['num_simulations'])
    initial_position = int(data['initial_position'])

    results = run_simulation(driver, num_simulations, initial_position)
    img = plot_histogram(results)

    return jsonify({'image': img})

def run_simulation(driver, num_simulations, initial_position):
    driver_abbr = driver_info[driver]
    num_laps = 66
    driver_stddev = {d: 0.05 for d in driver_info.keys()}
    positions = []

    for _ in range(num_simulations):
        race_lap_times = {d: [] for d in driver_info.keys()}
        for lap in range(1, num_laps + 1):
            for d in driver_info.keys():
                ratings = driver_ratings[driver_info[d]]
                prime_time = driver_prime_times[driver_info[d]]
                random_variation = np.random.normal(0, driver_stddev[d] * (100 - ratings['Experience']) / 100)

                # Adjusting penalties to prevent reversal effect
                starting_position_penalty = -1 * (initial_position - 1)
                traffic_penalty = -2.5 * (initial_position - 1) * (1 / (lap ** 0.3))
                dirty_air_penalty = -2.5 * (initial_position - 1) * (1 / (lap ** 0.3))
                
                total_penalty = starting_position_penalty + traffic_penalty + dirty_air_penalty
                skill_influence = (100 - ratings['Racecraft']) / 100 * 0.2

                lap_time = prime_time + random_variation + total_penalty * (1 + skill_influence)

                # Correcting maximum possible position logic
                max_possible_position = max(21 - initial_position, 10)

                if lap == num_laps:
                    final_positions = sorted(race_lap_times.keys(), key=lambda d: sum(race_lap_times[d]))
                    driver_final_position = final_positions.index(driver) + 1
                    if driver_final_position < max_possible_position:
                        lap_time += (max_possible_position - driver_final_position) * 0.5

                if lap in [random.randint(15, 25), random.randint(45, 55)]:
                    pit_stop_time = generate_pit_stop_time()
                    lap_time += pit_stop_time

                race_lap_times[d].append(lap_time)

        total_race_times = {d: sum(race_lap_times[d]) for d in race_lap_times}
        sorted_drivers_final = sorted(total_race_times.keys(), key=lambda d: total_race_times[d])
        final_positions = {d: idx + 1 for idx, d in enumerate(sorted_drivers_final)}
        positions.append(final_positions[driver])

    return positions

def generate_pit_stop_time():
    return np.random.choice(range(23, 30))

def plot_histogram(positions):
    plt.figure(figsize=(10, 6))
    
    # Calculate statistics
    avg_position = np.mean(positions)
    median_position = np.median(positions)
    mode_position = max(set(positions), key=positions.count)
    stddev_position = np.std(positions)
    best_position = min(positions)
    worst_position = max(positions)
    num_simulations = len(positions)
    
    # Calculate win chance (finishing 1st)
    win_chance = positions.count(1) / num_simulations * 100
    
    # Calculate top 3 chance (finishing 1st, 2nd, or 3rd)
    top3_chance = sum(1 for pos in positions if pos <= 3) / num_simulations * 100
    
    # Plot the histogram
    plt.hist(positions, bins=np.arange(1, 22) - 0.5, edgecolor='black', alpha=0.7)
    plt.xlabel('Finishing Position')
    plt.ylabel('Frequency')
    
    # Display all relevant statistics in the title or as a text box
    title = (f'Finishing Positions Histogram\n'
             f'Average: {avg_position:.2f}, Simulations: {num_simulations}\n'
             f'Win Chance: {win_chance:.2f}%, Top 3 Chance: {top3_chance:.2f}%')
    
    plt.title(title)
    
    plt.xticks(np.arange(1, 22))

    # Save the plot to a BytesIO object and convert to a base64 string
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()

    return 'data:image/png;base64,{}'.format(img_url)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',  # Bind to all IP addresses
        port=port,       # Use the port specified by Heroku
        debug=True,      # Enable debug mode
        use_reloader=False  # Disable the automatic reloading of the server
    )