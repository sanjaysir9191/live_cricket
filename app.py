import os
import requests
import json
import traceback
from flask import Flask, jsonify, render_template
from datetime import datetime
import time # Added for potential future use or caching experiments

# --- Flask App Initialization ---
app = Flask(__name__)

# --- API Configuration ---
# Replace "your_actual_key_here" with your valid RapidAPI key if not using environment variables
API_KEY = os.getenv("RAPIDAPI_KEY", "0b37a9c650mshc04fcdd5e92ba66p1ca895jsn5ea3d38fc653")
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
}

# --- Data Storage Configuration (JSON Files) ---
# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define the subdirectory for storing data
DATA_DIR = os.path.join(BASE_DIR, 'api_data')
# Create the data directory if it doesn't exist
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"--- Data directory ensured at: {DATA_DIR} ---")
except OSError as e:
    print(f"!!! Error creating data directory {DATA_DIR}: {e}. Data saving might fail.")
    # Depending on requirements, you might want to exit or handle this differently
    DATA_DIR = None # Set to None if creation failed

# --- Helper Function to Save JSON Data ---
def save_json_data(filename, data):
    if DATA_DIR is None:
        print("!!! Cannot save data: DATA_DIR is not configured due to creation error.")
        return

    # Sanitize filename slightly (replace potential path separators if match_id contains them)
    safe_filename = filename.replace('/', '_').replace('\\', '_')
    filepath = os.path.join(DATA_DIR, safe_filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"--- Data saved to {filepath} ---")
    except IOError as e:
        print(f"!!! Error saving data to {filepath}: {e}")
    except TypeError as e:
        print(f"!!! Error saving JSON (likely non-serializable data): {e} in file {filepath}")
    except Exception as e:
        print(f"!!! Unexpected error saving JSON to {filepath}: {e}")
        print(traceback.format_exc()) # Log full traceback for unexpected errors

# --- Route for Listing Live Matches ---
@app.route('/')
def index():
    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    endpoint_name = "live_matches"
    print(f"--- Requesting Live Matches: {url} ---")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"--- Live Matches API Status: {response.status_code} ---")
        response.raise_for_status()
        data = response.json() # Raw data from API

        # <<< SAVE RAW API RESPONSE >>>
        save_json_data(f"{endpoint_name}_{datetime.now():%Y%m%d_%H%M%S}.json", data)

        # --- Process data AFTER saving (or before, depending on need) ---
        matches = []
        for match_type in data.get("typeMatches", []):
            for series in match_type.get("seriesMatches", []):
                series_wrapper = series.get("seriesAdWrapper", {})
                if series_wrapper and "matches" in series_wrapper:
                    for game in series_wrapper.get("matches", []):
                        info = game.get("matchInfo", {})
                        if info and info.get("matchId"):
                            matches.append({
                                "match_id": info["matchId"],
                                "team1": info.get("team1", {}).get("teamName", "TBD"),
                                "team2": info.get("team2", {}).get("teamName", "TBD"),
                                "status": info.get("status", "Status unavailable")
                            })

        print(f"--- Found {len(matches)} live matches ---")
        return render_template("index.html", matches=matches)

    except requests.exceptions.HTTPError as http_err:
        print(f"!!! HTTP error occurred in / route: {http_err} - Status Code: {http_err.response.status_code if http_err.response else 'N/A'}")
        error_msg = f"API Error fetching live matches: Status {http_err.response.status_code if http_err.response else 'N/A'}. Check API key/plan."
        return render_template("error.html", error=error_msg), http_err.response.status_code if http_err.response else 500
    except requests.exceptions.RequestException as e:
        print(f"!!! RequestException occurred in / route: {str(e)}")
        return render_template("error.html", error=f"Network Error fetching live matches: {str(e)}"), 500
    except json.JSONDecodeError as e:
        print(f"!!! JSONDecodeError in / route: Failed to parse API response - {str(e)}")
        # Log raw text if possible and desired for debugging non-JSON responses
        # print(f"--- Raw text causing error (first 500 chars): {response.text[:500]} ... ---")
        return render_template("error.html", error="Failed to parse live match API response (invalid JSON)."), 500
    except Exception as e:
        print(f"!!! Unexpected error in / route: {str(e)}")
        print(traceback.format_exc())
        return render_template("error.html", error=f"An unexpected error occurred while fetching matches: {str(e)}"), 500


# --- Route for Scorecard ---
@app.route('/scorecard/<match_id>')
def scorecard(match_id):
    url = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{match_id}/scard"
    endpoint_name = "scorecard"
    print(f"--- Request for Scorecard: match_id={match_id}, url={url} ---")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"--- Scorecard API Status: {response.status_code} ---")
        response.raise_for_status()
        data = response.json() # Raw data from API

        # <<< SAVE RAW API RESPONSE >>>
        save_json_data(f"{endpoint_name}_{match_id}_{datetime.now():%Y%m%d_%H%M%S}.json", data)

        # --- Process data AFTER saving ---
        innings_data = []
        score_card_list = data.get("scoreCard", [])
        # ...(rest of your existing scorecard processing logic)...
        if not isinstance(score_card_list, list):
             print(f"!!! Warning: Expected 'scoreCard' to be a list, but got {type(score_card_list)}")
             # Decide how to handle - return empty or error? Returning empty for robustness.
             score_card_list = []

        for index, innings in enumerate(score_card_list):
            if not isinstance(innings, dict):
                print(f"!!! Warning: Skipping innings at index {index}, not a dict.")
                continue
            # ... (parse bat_team_details, score_details, bowl_team_details) ...
            bat_team_details = innings.get("batTeamDetails", {})
            bat_team = bat_team_details.get("batTeamName", "Unknown Team")
            score_details = innings.get("scoreDetails", {})
            bowl_team_details = innings.get("bowlTeamDetails", {})
            entry = { # ... (populate entry dict) ...
                "team": bat_team,
                "score": f"{score_details.get('runs', 0)}/{score_details.get('wickets', 0)}",
                "overs": score_details.get('overs', '0.0'),
                "batsmen": [], "bowlers": []
            }
            # ... (process batsmen_list, checking types as before) ...
            batsmen_list = bat_team_details.get("batsmenData", [])
            if isinstance(batsmen_list, list):
                 for player in batsmen_list:
                     if isinstance(player, dict): entry["batsmen"].append({ ... }) # Your mapping
            elif isinstance(batsmen_list, dict): # Fallback
                 for player_id, player in batsmen_list.items():
                      if isinstance(player, dict): entry["batsmen"].append({ ... }) # Your mapping
            # ... (process bowlers_list, checking types as before) ...
            bowlers_list = bowl_team_details.get("bowlersData", [])
            if isinstance(bowlers_list, list):
                 for player in bowlers_list:
                     if isinstance(player, dict): entry["bowlers"].append({ ... }) # Your mapping
            elif isinstance(bowlers_list, dict): # Fallback
                 for player_id, player in bowlers_list.items():
                      if isinstance(player, dict): entry["bowlers"].append({ ... }) # Your mapping

            innings_data.append(entry)

        print(f"--- Prepared innings_data count: {len(innings_data)} for match {match_id} ---")
        return jsonify(innings_data) # Return processed data

    # --- Keep Error Handling Consistent ---
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if http_err.response else 500
        print(f"!!! HTTP error occurred in /scorecard: {http_err} - Status Code: {status_code}")
        error_msg = f"API Error fetching scorecard: Status {status_code}. Check API key/endpoint/plan or match ID."
        try: error_detail = http_err.response.json(); error_msg = error_detail.get("message", error_msg)
        except ValueError: pass
        return jsonify({"error": error_msg}), status_code
    except requests.exceptions.RequestException as e:
        print(f"!!! RequestException occurred in /scorecard: {str(e)}")
        return jsonify({"error": f"Network Error connecting to API for scorecard: {str(e)}"}), 500
    except json.JSONDecodeError as e:
        print(f"!!! JSONDecodeError in /scorecard: Failed to parse API response - {str(e)}")
        return jsonify({"error": "Failed to parse scorecard API response (invalid JSON)."}), 500
    except Exception as e:
        print(f"!!! An unexpected error occurred in /scorecard route: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"An internal server error occurred processing scorecard."}), 500


# --- Route for Commentary ---
@app.route('/commentary/<match_id>')
def commentary(match_id):
    url = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{match_id}/comm"
    endpoint_name = "commentary"
    print(f"--- Request for Commentary: match_id={match_id}, url={url} ---")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        print(f"--- Commentary API Status: {response.status_code} ---")
        response.raise_for_status()
        data = response.json() # Raw data from API

        # <<< SAVE RAW API RESPONSE >>>
        save_json_data(f"{endpoint_name}_{match_id}_{datetime.now():%Y%m%d_%H%M%S}.json", data)

        # --- Process data AFTER saving ---
        commentary_items = data.get("commentaryList", [])
        if not isinstance(commentary_items, list):
             print(f"!!! Warning: Expected 'commentaryList' to be a list, got {type(commentary_items)}")
             commentary_items = []

        commentary_list = [ # Process last 15 valid items
            {
                "over": item.get("overNumber"), "ball": item.get("ballNumber"),
                "text": item.get("commText", "...")
            }
            for item in reversed(commentary_items[-15:]) if isinstance(item, dict)
        ]

        print(f"--- Prepared commentary_list count: {len(commentary_list)} for match {match_id} ---")
        return jsonify(commentary_list) # Return processed data

    # --- Keep Error Handling Consistent ---
    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if http_err.response else 500
        print(f"!!! HTTP error occurred in /commentary: {http_err} - Status Code: {status_code}")
        error_msg = f"API Error fetching commentary: Status {status_code}. Check API key/endpoint/plan or match ID."
        try: error_detail = http_err.response.json(); error_msg = error_detail.get("message", error_msg)
        except ValueError: pass
        return jsonify({"error": error_msg}), status_code
    except requests.exceptions.RequestException as e:
        print(f"!!! RequestException occurred in /commentary: {str(e)}")
        return jsonify({"error": f"Network Error connecting to API for commentary: {str(e)}"}), 500
    except json.JSONDecodeError as e:
        print(f"!!! JSONDecodeError in /commentary: Failed to parse API response - {str(e)}")
        return jsonify({"error": "Failed to parse commentary API response (invalid JSON)."}), 500
    except Exception as e:
        print(f"!!! An unexpected error occurred in /commentary route: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"An internal server error occurred processing commentary."}), 500


# --- Main Execution ---
if __name__ == '__main__':
    print("--- Starting Flask App ---")
    # Set debug=True for development ONLY (auto-reload, browser errors)
    # Set debug=False for production deployment
    # Use host='0.0.0.0' to make accessible on your network (if firewall allows)
    app.run(debug=True, host='0.0.0.0', port=5000)

