"""Unit tests for backend.py

Note: The functions get_stats and filter_double_up_games_together are not tested
as they are integration functions that primarily aggregate results from other
helper functions that are tested
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import requests
import logging

# Add parent directory to path so we can import backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                '..')))
from backend import (make_request, get_account_info,
                    get_summoner_info, get_double_up_rank, get_match_history,
                    get_match_details, extract_active_traits,
                    format_top_traits, calculate_favorite_traits)

# Set default server configuration for tests (North America)
import backend
backend.REGION = 'NA1'
backend.PLATFORM = 'AMERICAS'

class TestMakeRequest(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)
        
    def test_success(self):
        """Test that a successful request returns the JSON response"""

        # Mock the requests.get function to return a successful response
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'test_data'}
            mock_get.return_value = mock_response
            
            response, status = make_request('http://test.com')
            
            # Verify the result and request were made correctly
            self.assertEqual(response, {'data': 'test_data'})
            self.assertEqual(status, 200)
            mock_get.assert_called_once()
    
    def test_rate_limit(self):
        """Test that rate limit (429) triggers retry after sleep"""

        # Mock the requests.get function to return a rate limit response,
        # then a successful response
        with (patch('requests.get') as mock_get,
             patch('time.sleep') as mock_sleep):
            rate_limit_response = MagicMock()
            rate_limit_response.status_code = 429
            rate_limit_response.json.side_effect = (requests.exceptions.
                                                   RequestException)
            
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {'data': 'test_data'}
            mock_get.side_effect = [rate_limit_response, success_response]
            
            response, status = make_request('http://test.com')
            
            # Verify results and that we made the correct number of requests
            self.assertEqual(response, {'data': 'test_data'})
            self.assertEqual(status, 200)
            self.assertEqual(mock_get.call_count, 2)

            # Verify we slept between retries
            mock_sleep.assert_called_once_with(5)
    
    def test_error(self):
        """Test that non-rate-limit errors return None"""

        # Mock the requests.get function to return an error response
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.json.side_effect = (requests.exceptions.
                                              RequestException)
            mock_get.return_value = mock_response
            
            response, status = make_request('http://test.com')
            
            # Verify we get None on error and no retries
            self.assertIsNone(response)
            self.assertEqual(status, 404)
            mock_get.assert_called_once()

# For functions that return make_request, it is enough to check for a successful
# response since the make_request function is tested above and either returns
# the response or None
class TestGetAccountInfo(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_success(self):
        """Test account lookup with valid name returns data with puuid"""
        
        # Mock the make_request function to return a successful response
        with patch('backend.make_request') as mock_request:
            expected_data = {'puuid': 'test-id'}
            mock_request.return_value = (expected_data, 200)
            
            response, status = get_account_info('TestPlayer', 'NA1')
            
            # Verify we can access puuid and got correct status
            self.assertEqual(response.get('puuid'), 'test-id')
            self.assertEqual(status, 200)
            mock_request.assert_called_once()

class TestGetSummonerInfo(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_success(self):
        """Test summoner lookup with valid puuid returns data with summonerId"""
        
        # Mock the make_request function to return a successful response
        with patch('backend.make_request') as mock_request:
            expected_data = {'id': 'summoner-id'}
            mock_request.return_value = (expected_data, 200)
            
            response, status = get_summoner_info('test-puuid')
            
            # Verify we can access id and got correct status
            self.assertEqual(response.get('id'), 'summoner-id')
            self.assertEqual(status, 200)
            mock_request.assert_called_once()

class TestGetDoubleUpRank(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_success(self):
        """Test successful rank lookup returns formatted rank string"""
        
        # Mock the make_request function to return a successful response
        with patch('backend.make_request') as mock_request:
            response = [{
                'queueType': 'RANKED_TFT_DOUBLE_UP',
                'tier': 'DIAMOND',
                'rank': 'II',
                'leaguePoints': 75
            }]
            mock_request.return_value = (response, 200)
            
            result = get_double_up_rank('test-summoner-id')
            
            # Verify rank string format
            self.assertEqual(result, "Diamond II (75 LP)")
            mock_request.assert_called_once()
    
    def test_no_double_up_queue(self):
        """Test response without Double Up queue returns error message"""
        
        # Mock response with other queue data but no Double Up
        with patch('backend.make_request') as mock_request:
            response = [{
                'queueType': 'RANKED_TFT',
                'tier': 'GOLD',
                'rank': 'I',
                'leaguePoints': 75
            }]
            mock_request.return_value = (response, 200)
            
            result = get_double_up_rank('test-summoner-id')
            
            # Should return error message for no Double Up queue found
            self.assertEqual(result, "Unranked")
            mock_request.assert_called_once()
    
    def test_no_double_up_data(self):
        """Test empty response returns error message"""
        
        # Mock empty response (no ranked data)
        with patch('backend.make_request') as mock_request:
            mock_request.return_value = (None, 404)
            
            result = get_double_up_rank('test-summoner-id')
            
            # Should return error message for empty response
            self.assertEqual(result, "Unranked")
            mock_request.assert_called_once()

    def test_error(self):
        """Test non-200/404 status code returns error message"""
        
        # Mock the make_request function to return a non-200/404 response
        with patch('backend.make_request') as mock_request:
            mock_request.return_value = (None, 403)
            
            result = get_double_up_rank('test-summoner-id')
            
            # Should return error message for non-200/404 status code
            self.assertEqual(result,
                             "403: Error getting information about rank")
            mock_request.assert_called_once()

class TestGetMatchHistory(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_success(self):
        """Test match history lookup returns list of match IDs"""
        
        with patch('backend.make_request') as mock_request:
            # Mock response with list of match IDs
            response = [
                "NA1_1234",
                "NA1_5678",
                "NA1_9012"
            ]
            mock_request.return_value = response, 200
            
            result, status = get_match_history('test-puuid')
            
            # Verify we get the match IDs and correct parameters were passed
            self.assertEqual(result, response)
            self.assertEqual(status, 200)
            mock_request.assert_called_once()

class TestGetMatchDetails(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_success(self):
        """Test match details lookup returns match data"""
        
        with patch('backend.make_request') as mock_request:
            # Mock response with match details
            response = {
                'info': {
                    'queue_id': 1160
                }
            }
            mock_request.return_value = (response, 200)
            
            result, status = get_match_details('NA1_1234')
            
            # Verify we get the match details
            self.assertEqual(result, response)
            self.assertEqual(status, 200)
            mock_request.assert_called_once()

class TestExtractActiveTraits(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_extract_active_traits(self):
        """Test extracting active traits from match data"""
        
        # Mock player match data with both active and inactive traits
        player_data = {
            'traits': [
                {
                    'name': 'TFT13_Ambassador',
                    'num_units': 2,
                    'tier_current': 1  # Active trait
                },
                {
                    'name': 'TFT13_Cabal',
                    'num_units': 4,
                    'tier_current': 2  # Active trait
                },
                {
                    'name': 'TFT13_Invoker',
                    'num_units': 1,
                    'tier_current': 0  # Inactive trait
                }
            ]
        }
        
        result = extract_active_traits(player_data)
        
        # Should only include active traits and mapped to correct names,
        # sorted by num_units
        expected = [
            {
                'name': 'Black Rose',
                'num_units': 4,
                'tier': 2
            },
            {
                'name': 'Emissary',
                'num_units': 2,
                'tier': 1
            }
        ]
        
        self.assertEqual(result, expected)
    
    def test_no_active_traits(self):
        """Test handling player data with no active traits"""
        
        no_active = {'traits': [
                {
                    'name': 'TFT13_Invoker',
                    'num_units': 1,
                    'tier_current': 0  # Inactive trait
                }
            ]
        }
        result = extract_active_traits(no_active)
        self.assertEqual(result, [])
        
        # Test with empty traits field
        result = extract_active_traits({'traits': []})
        self.assertEqual(result, [])

class TestFormatTopTraits(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_three_plus_units(self):
        """Test formatting traits with 3 or more units"""
        
        traits = [
            {
                'name': 'Black Rose',
                'num_units': 4,
                'tier': 2
            },
            {
                'name': 'Emissary',
                'num_units': 3,
                'tier': 1
            },
            {
                'name': 'Strategist',
                'num_units': 2,
                'tier': 1
            }
        ]
        
        result = format_top_traits(traits)
        expected = "4 Black Rose, 3 Emissary"
        self.assertEqual(result, expected)
    
    def test_two_plus_units(self):
        """Test formatting traits with only 2 or more units"""
        
        traits = [
            {
                'name': 'Emissary',
                'num_units': 2,
                'tier': 1
            },
            {
                'name': 'Strategist',
                'num_units': 2,
                'tier': 1
            },
            {
                'name': 'Invoker',
                'num_units': 1,
                'tier': 1
            }
        ]
        
        result = format_top_traits(traits)
        expected = "2 Emissary, 2 Strategist"
        self.assertEqual(result, expected)
    
    def test_built_different(self):
        """Test formatting with no traits returns 'Built Different'"""
        
        result = format_top_traits([])
        self.assertEqual(result, "Built Different")

class TestCalculateFavoriteTraits(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
    
    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_calculate_favorite_traits(self):
        """Test calculating favorite traits across games"""
        
        games = [
            {
                'player1_traits': '6 Black Rose, 4 Sorcerer',  # Black Rose
                'player2_traits': '6 Sorcerer, 3 Black Rose'   # Sorcerer
            },
            {
                'player1_traits': '4 Black Rose, 4 Sentinel',  # Black/Senti
                'player2_traits': 'Built Different'            # Counts as 1
            },
            {
                'player1_traits': '6 Sentinel, 4 Black Rose',  # Sentinel
                'player2_traits': '4 Sorcerer, 3 Black Rose'   # Sorcerer
            }
        ]
        
        # Test player 1's traits
        result = calculate_favorite_traits(games, 1)
        expected = [
            {'name': 'Black Rose', 'count': 2},
            {'name': 'Sentinel', 'count': 2},  
        ]
        self.assertEqual(result, expected)
        
        # Test player 2's traits
        result = calculate_favorite_traits(games, 2)
        expected = [
            {'name': 'Sorcerer', 'count': 2},
            {'name': 'Built Different', 'count': 1}
        ]
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
