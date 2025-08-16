import requests
from datetime import datetime
from urllib.parse import quote
import time
import logging
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variable
RIOT_API_KEY = os.environ.get('RIOT_API_KEY')
if not RIOT_API_KEY:
    raise ValueError("RIOT_API_KEY environment variable is not set.\
                      Run 'make set-key' to set it.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server configurations dictionary for lookup
SERVER_CONFIGS = {
    'NA': {'region': 'americas', 'platform': 'na1'},
    'BR': {'region': 'americas', 'platform': 'br1'},
    'LAN': {'region': 'americas', 'platform': 'la1'},
    'LAS': {'region': 'americas', 'platform': 'la2'},
    'EUW': {'region': 'europe', 'platform': 'euw1'},
    'EUNE': {'region': 'europe', 'platform': 'eun1'},
    'TR': {'region': 'europe', 'platform': 'tr1'},
    'KR': {'region': 'asia', 'platform': 'kr'},
    'JP': {'region': 'asia', 'platform': 'jp1'}
}

# Global variables for server configuration
global REGION, PLATFORM

# Trait name dictionary to map from API names to in-game names since Riot Games
# doesn't update them in their API between sets
# SET_13_TRAIT_MAPPING = {
#     'Academy': 'Academy',
#     'Ambassador': 'Emissary',
#     'Ambusher': 'Ambusher',
#     'BloodHunter': 'Blood Hunter',
#     'Bruiser': 'Bruiser',
#     'Cabal': 'Black Rose',
#     'Crime': 'Chem-Baron',
#     'FormSwapper': 'Form Swapper',
#     'Hextech': 'Automata',
#     'HighRoller': 'High Roller',
#     'Infused': 'Dominator',
#     'Invoker': 'Visionary',
#     'JunkerKing': 'Junker King',
#     'MachineHerald': 'Machine Herald',
#     'Martialist': 'Artillerist',
#     'MissMageTrait': 'Banished Mage',
#     'Pugilist': 'Pit Fighter',
#     'Squad': 'Enforcer',
#     'Titan': 'Sentinel',
#     'Watcher': 'Watcher',
#     'Warband': 'Conqueror',
#     'Hoverboard': 'Family',
# }

def make_request(url, params=None):
    """Make a request to the Riot API. If we exceed the rate limit, wait 5
    seconds and try again (code 429). Otherwise return the response or on a
    different error than rate limit, return None. Returns status code too."""

    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 429:
                logger.info(f"Rate limit exceeded. Waiting 5 seconds...")
                time.sleep(5)
                continue
            response.raise_for_status()
            return response.json(), response.status_code
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return None, response.status_code

def get_account_info(game_name, tag_line):
    """Get account info using Riot ID, used to get player's puuid."""
    
    url = (f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/"
           f"by-riot-id/{quote(game_name)}/{quote(tag_line)}")
    logger.info(f"Looking up player: {game_name}#{tag_line}")
    return make_request(url)

def get_summoner_info(puuid):
    """Get summoner info using puuid, used to get summonerId"""

    url = (f"https://{PLATFORM}.api.riotgames.com/tft/summoner/v1/"
           f"summoners/by-puuid/{puuid}")
    logger.info(f"Looking up Summoner Data...")
    return make_request(url)

def get_double_up_rank(summonerId):
    """Get Double Up rank information using summonerId."""

    url = (f"https://{PLATFORM}.api.riotgames.com/tft/league/v1/"
           f"entries/by-summoner/{summonerId}")
    logger.info(f"Looking up TFT League Data...")
    response, status_code = make_request(url)

    if not response:
        if status_code == 404 or status_code == 200:
            return "Unranked"
        else:
            return f"{status_code}: Error getting information about rank"
        
    # Find Double Up queue
    double_up_rank = None
    for queue in response:
        if queue.get('queueType') == 'RANKED_TFT_DOUBLE_UP':
            double_up_rank = queue
            break

    # Extract relevant information about rank        
    if double_up_rank:
        tier = double_up_rank.get('tier', '').title()
        division = double_up_rank.get('rank', '')
        lp = double_up_rank.get('leaguePoints', 0)
        return f"{tier} {division} ({lp} LP)"
    else:
        return "Unranked"

def get_match_history(puuid):
    """Get match IDs for a given puuid from Set 13."""

    url = (f"https://{REGION}.api.riotgames.com/tft/match/v1/"
           f"matches/by-puuid/{puuid}/ids")
    
    # Set startTime to Set 13 start (November 20, 2024)
    startTime = int(datetime(2024, 11, 20).timestamp())
    
    params = {
        "start": 0,
        "count": 9999,
        "startTime": startTime
    }
    logger.info(f"Fetching TFT match history From Set 13...")
    return make_request(url, params)

def get_match_details(match_id):
    """Get match details using its id"""
    
    url = f"https://{REGION}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    logger.info(f"Fetching TFT match details for {match_id}...")
    return make_request(url)

def extract_active_traits(player_match_data):
    """Extract active traits for a player given match data"""

    traits = []
    for trait in player_match_data.get('traits', []):
        # Only include active traits
        if trait.get('tier_current', 0) > 0:
            # Remove TFT13_ prefix and map to correct name
            api_name = trait['name'].replace('TFT14_', '')
            traits.append({
                'name': api_name,
                'num_units': trait['num_units'],
                'tier': trait['tier_current']
            })
    
    # Sort by number of units (descending)
    traits = sorted(traits, key=lambda x: -x['num_units']) if traits else []
    return traits

def format_top_traits(traits):
    """Format top traits for display on dashboard. If no traits are active,
    return 'Built Different'. Tries to return traits with 3 or more units,
    otherwise returns traits with 2 or more units."""

    if not traits:
        return "Built Different"
    
    # Try to get traits with 3 or more units
    top_traits = [t for t in traits if t['num_units'] >= 3]
    
    # If none found, fall back to traits with 2 or more units
    if not top_traits:
        top_traits = [t for t in traits if t['num_units'] >= 2]
    
    return ', '.join(f"{t['num_units']} {t['name']}" for t in top_traits)

def filter_double_up_games_together(puuid1, puuid2):
    """Given a puuid of two players, return all their Double Up games info."""

    # Get TFT match history for player 1
    match_ids, status_code = get_match_history(puuid1)
    if not match_ids:
        if status_code == 404 or status_code == 200:
            logger.error(f"Player 1 has no TFT matches")
            return None, 404
        logger.error(f"{status_code}: Failed to get match history for player 1")
        return None, status_code

    # Filter out Double Up matches played with player 2
    logger.info(f"Analyzing {len(match_ids)} matches for Double Up games...")
    double_up_games = []

    # For each match, check if it's a Double Up game (queue ID 1160) and store
    # data if it is
    for match_id in match_ids:
        match_data, status_code = get_match_details(match_id)

        # No match details found, skip
        if not match_data:
            logger.error(f"{status_code}: Match details fetch err: {match_id}")
            continue

        # If not a Double Up game, skip
        info = match_data['info']
        if info.get('queue_id') != 1160:
            logger.info(f"Match {match_id} is not a Double Up game")
            continue

        # Check if player 2 played in this match, otherwise skip
        metadata = match_data['metadata']    
        participants = metadata.get('participants')
        played_with_player2 = False
        for p in participants:
            if p == puuid2:
                played_with_player2 = True
                break
        if not played_with_player2:
            logger.info(f"Match {match_id} did not feature player 2")
            continue
        
        # Get match details for both players now that the match is filtered
        player1_match_data = None
        player2_match_data = None
        participants_data = info.get('participants', [])
        for p in participants_data:
            if p['puuid'] == puuid1:
                player1_match_data = p
            elif p['puuid'] == puuid2:
                player2_match_data = p
                
        # Get team placement. In Double Up, team placement is (individual
        # placement + 1) // 2.
        # e.g. placement 1 or 2 -> team placement 1
        #      placement 3 or 4 -> team placement 2
        placement = (player1_match_data['placement'] + 1) // 2
        
        # Get top traits for both players and format them properly
        traits1 = format_top_traits(extract_active_traits(player1_match_data))
        traits2 = format_top_traits(extract_active_traits(player2_match_data))

        # Convert game time to YYYY-MM-DD HH:MM
        date_and_time = (datetime.fromtimestamp(info['game_datetime'] / 1000)
                        .strftime('%Y-%m-%d %H:%M'))
        
        # Store game info
        double_up_games.append({
            'match_id': match_id,
            'datetime': date_and_time,
            'placement': placement,
            'player1_traits': traits1,
            'player2_traits': traits2
        })
        logger.info(f"Found Double Up game with player 2: "
                   f"Match {match_id}, Placement {placement}")
    
    # Sort games by time (newest first)
    double_up_games.sort(key=lambda x: x['datetime'], reverse=True)
    num_double_up_games = len(double_up_games)
    logger.info(f"{num_double_up_games} Double Up games with partner found")
    if num_double_up_games == 0:
        return None, 404
    return double_up_games, 200

def calculate_favorite_traits(games, player_num):
    """Calculate most played traits for a player across all games"""

    total_trait_counts = {}
    for game in games:
        current_traits = []
        for trait in game.get(f'player{player_num}_traits', '').split(', '):
            # Extract count and name from format like "4 Sentinel"
            if trait != 'Built Different':
                parts = trait.split(' ', 1)
                count = int(parts[0])
                name = parts[1]
                current_traits.append((count, name))
            else:
                current_traits.append((1, trait))
        
        # Find max count in this game
        max_count = max(t[0] for t in current_traits)

        # Add all traits with max count
        for count, name in current_traits:
            if count == max_count:
                total_trait_counts[name] = total_trait_counts.get(name, 0) + 1
    
    # Sort by count (descending) and take top 3
    sorted_traits = sorted(total_trait_counts.items(),
                           key=lambda x: (-x[1], x[0]))[:3]
    return [{'name': name, 'count': count} for name, count in sorted_traits]

def get_stats(game_name1, tag_line1, game_name2, tag_line2, server):
    """Returns a dictionary with all stats displayed on the dashboard for two
    players and their Double Up games together"""

    # Get server configuration
    global REGION, PLATFORM
    try:
        REGION = SERVER_CONFIGS[server]['region']
        PLATFORM = SERVER_CONFIGS[server]['platform']
    except KeyError:
        return {'error': f"Invalid server: {server}"}

    # Get puuid for both players using their Riot ID.
    account1, status_code1 = get_account_info(game_name1, tag_line1)
    account2, status_code2 = get_account_info(game_name2, tag_line2)
    if not account1:
        if status_code1 == 404 or status_code1 == 400:
            return {'error': f"{game_name1}#{tag_line1} on {server} not found"}
        if status_code1 == 403:
            return {'error': "Expired/Invalid API key."}
        return {'error': f"{status_code1}: Err getting acc info for player 1"}
    if not account2:
        if status_code2 == 404 or status_code2 == 400:
            return {'error': f"{game_name2}#{tag_line2} on {server} not found"}
        if status_code1 == 403:
            return {'error': "Expired/Invalid API key."}
        return {'error': f"{status_code2}: Err getting acc info for player 2"}
    puuid1 = account1.get('puuid')
    puuid2 = account2.get('puuid')

    # Get summonerId for both players using their puuid
    summoner1, status_code1 = get_summoner_info(puuid1)
    summoner2, status_code2 = get_summoner_info(puuid2)
    if not summoner1:
        if status_code1 == 404 or status_code1 == 400:
            return {'error': f"{game_name1}#{tag_line1} on {server} not found"}
        return {'error': f"{status_code1}: Err getting smnr data for player 1"}
    if not summoner2:
        if status_code2 == 404 or status_code2 == 400:
            return {'error': f"{game_name2}#{tag_line2} on {server} not found"}
        return {'error': f"{status_code2}: Err getting smnr data for player 2"}
    summonerId1 = summoner1.get('id')
    summonerId2 = summoner2.get('id')
    
    # Get rank info
    rank1 = get_double_up_rank(summonerId1)
    rank2 = get_double_up_rank(summonerId2)
    
    # Find all Double Up games with partner
    match_history, status_code = filter_double_up_games_together(puuid1, puuid2)
    if not match_history:
        if status_code == 404 or status_code == 200:
            logger.info(f"No Double Up games together found")
            total_games = 0
            wins = 0
            win_rate = 0
            best_streak = 0
            most_played_traits1 = None
            most_played_traits2 = None
        else:
            return {'error': f"{status_code}: Err getting match history"}
    else:
        # Calculate stats for dashboard display
        total_games = len(match_history)
        wins = sum(1 for game in match_history
                    if game['placement'] <= 2) # 1st and 2nd = win
        win_rate = (round((wins / total_games * 100), 1)
                    if total_games > 0 else 0)
    
        # Calculate best win streak
        current_streak = 0
        best_streak = 0
        for game in match_history:  # Games are already sorted newest first
            if game['placement'] <= 2:
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                current_streak = 0
    
        # Get most played traits for both players
        most_played_traits1 = calculate_favorite_traits(match_history, 1)
        most_played_traits2 = calculate_favorite_traits(match_history, 2)
    
    return {
        'player1': {
            'name': game_name1,
            'tag': tag_line1,
            'rank': rank1,
            'favorite_traits': most_played_traits1
        },
        'player2': {
            'name': game_name2,
            'tag': tag_line2,
            'rank': rank2,
            'favorite_traits': most_played_traits2
        },
        'total_games': total_games,
        'wins': wins,
        'win_rate': win_rate,
        'best_streak': best_streak,
        'match_history': match_history
    }