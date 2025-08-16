from flask import Flask, render_template, jsonify, request
import os
from backend import get_stats
import logging
import json
import time

# Setup
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
app = Flask(__name__)
CACHE_FILE = 'stats_cache.json'
cooldown_end_time = 0
update_status = ""
cooldown_in_minutes = 2

def load_cached_data():
    """Load stats from CACHE_FILE."""
    logger.debug("Loading cached data...")
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading cache file: {str(e)}")
    return None

def save_cached_data(stats):
    """Save stats to CACHE_FILE."""
    logger.debug("Saving cached data...")
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(stats, f)
    except Exception as e:
        logger.error(f"Error saving to cache file: {str(e)}")

def fetch_fresh_stats(player1_name, player1_tag, player2_name, player2_tag,
                      server):
    """Fetch fresh stats from the API."""
    logger.debug("Fetching fresh stats from API")
    try:
        stats = get_stats(player1_name, player1_tag, player2_name, player2_tag,
                          server)
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise

@app.route('/')
def index():
    # If update in progress, wait for its completion
    while (update_status == "Be Patient :)"):
        time.sleep(1)

    # Load stats from cache
    stats = load_cached_data()
    if not stats:
        # If no cache exists, return empty stats
        stats = {
            'player1': {
                'name': "Player 1",
                'tag': "",
                'rank': None,
                'favorite_traits': None
            },
            'player2': {
                'name': "Player 2",
                'tag': "",
                'rank': None,
                'favorite_traits': None
            },
            'total_games': 0,
            'wins': 0,
            'win_rate': 0,
            'best_streak': 0,
            'match_history': []
        }
    
    return render_template('index.html', stats=stats,
                         cooldown_end_time=cooldown_end_time,
                         update_status=update_status)

@app.route('/update')
def update_stats():
    global cooldown_end_time, update_status
    update_status = "Be Patient :)"

    try:
        # Get player info from request parameters
        player1_name = request.args.get('player1Name')
        player1_tag = request.args.get('player1Tag')
        player2_name = request.args.get('player2Name')
        player2_tag = request.args.get('player2Tag')
        server = request.args.get('server')

        if not all([player1_name, player1_tag, player2_name, player2_tag,
                    server]):
            update_status = "Missing player information"
            return jsonify({})

        # Get current cached data
        old_stats = load_cached_data()
        
        # Fetch new data
        new_stats = fetch_fresh_stats(player1_name, player1_tag, 
                                      player2_name, player2_tag, server)

        # Delete existing cache
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

        cooldown_end_time = time.time() + (cooldown_in_minutes * 60)

        if 'error' in new_stats:
            update_status = new_stats['error']
            return jsonify({})
        
        # Check if data has changed
        if old_stats and old_stats == new_stats:
            update_status = "Stats are already up to date!"
            return jsonify({})
        
        # Save new data
        save_cached_data(new_stats)
        update_status = "Stats successfully updated!"
        return jsonify({})
        
    except Exception as e:
        update_status = "Error updating: " + str(e)
        return jsonify({})

if __name__ == '__main__':
    logger.info("Starting Flask app...")
    app.run(debug=True, port=5001, host='0.0.0.0')
