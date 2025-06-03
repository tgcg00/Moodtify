import os
import requests
import json
from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import base64
from urllib.parse import urlencode

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)  # Required for sessions

# Configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Spotify Configuration
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:5000/callback')
SPOTIFY_SCOPE = 'user-read-private user-read-email'

# Initialize Spotify client (for search only - no auth needed)
def get_spotify_search_client():
    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Initialize Spotify OAuth (for user authentication if needed)
def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE,
        cache_path=None,
        show_dialog=True
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_mood', methods=['POST'])
def analyze_mood():
    try:
        data = request.json
        
        # Extract form data
        name = data.get('name', 'Friend')
        mood = data.get('mood', '')
        feelings = data.get('feelings', '')
        time_of_day = data.get('time_of_day', '')
        language = data.get('language', 'English')
        genres = data.get('genres', '')
        artists = data.get('artists', '')
        
        # Create AI prompt
        prompt = f"""
        Analyze this person's mood and music preferences to recommend 10 high-quality songs:
        
        Name: {name}
        Current Mood: {mood}
        Feelings: {feelings}
        Time of Day: {time_of_day}
        Preferred Language: {language}
        Favorite Genres: {genres}
        Favorite Artists: {artists}
        
        Based on this information, recommend exactly 10 songs that match their mood and preferences. 
        Focus on well-known, high-quality tracks from official artists (no remixes or covers).
        
        Respond in this exact JSON format:
        {{
            "playlist_name": "A creative playlist name for {name}",
            "songs": [
                {{"artist": "Artist Name", "track": "Song Title"}},
                {{"artist": "Artist Name", "track": "Song Title"}},
                ...
            ],
            "mood_analysis": "Brief analysis of their mood and why these songs fit"
        }}
        """
        
        # Call OpenRouter API
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        )
        
        if response.status_code != 200:
            return jsonify({"error": "AI analysis failed"}), 500
            
        ai_response = response.json()
        ai_content = ai_response['choices'][0]['message']['content']
        
        # Parse AI response
        try:
            # Extract JSON from AI response
            start_idx = ai_content.find('{')
            end_idx = ai_content.rfind('}') + 1
            json_str = ai_content[start_idx:end_idx]
            ai_recommendations = json.loads(json_str)
        except:
            return jsonify({"error": "Failed to parse AI recommendations"}), 500
        
        # Search for songs on Spotify
        spotify = get_spotify_search_client()
        playlist_tracks = []
        
        for song in ai_recommendations.get('songs', []):
            artist = song.get('artist', '')
            track = song.get('track', '')
            
            if artist and track:
                try:
                    # Search for the track with more specific query
                    query = f'artist:"{artist}" track:"{track}"'
                    results = spotify.search(q=query, type='track', limit=3)
                    
                    if results['tracks']['items']:
                        # Get the best match (first result is usually most relevant)
                        track_data = results['tracks']['items'][0]
                        
                        # Verify it's a good match (not a remix or cover)
                        track_name = track_data['name'].lower()
                        original_track = track.lower()
                        artist_name = track_data['artists'][0]['name'].lower()
                        original_artist = artist.lower()
                        
                        # Simple matching logic to avoid remixes
                        if (original_artist in artist_name or artist_name in original_artist) and \
                           ('remix' not in track_name and 'cover' not in track_name and 'version' not in track_name):
                            
                            playlist_tracks.append({
                                'id': track_data['id'],
                                'name': track_data['name'],
                                'artist': track_data['artists'][0]['name'],
                                'album': track_data['album']['name'],
                                'preview_url': track_data.get('preview_url'),
                                'external_url': track_data['external_urls']['spotify'],
                                'image': track_data['album']['images'][0]['url'] if track_data['album']['images'] else None,
                                'uri': track_data['uri']
                            })
                    else:
                        # If exact search fails, try broader search
                        broader_query = f"{artist} {track}"
                        results = spotify.search(q=broader_query, type='track', limit=1)
                        if results['tracks']['items']:
                            track_data = results['tracks']['items'][0]
                            playlist_tracks.append({
                                'id': track_data['id'],
                                'name': track_data['name'],
                                'artist': track_data['artists'][0]['name'],
                                'album': track_data['album']['name'],
                                'preview_url': track_data.get('preview_url'),
                                'external_url': track_data['external_urls']['spotify'],
                                'image': track_data['album']['images'][0]['url'] if track_data['album']['images'] else None,
                                'uri': track_data['uri']
                            })
                            
                except Exception as search_error:
                    print(f"Error searching for {artist} - {track}: {search_error}")
                    continue
        
        # Limit to 10 tracks maximum
        playlist_tracks = playlist_tracks[:10]
        
        # Generate Spotify embed URLs
        embed_urls = []
        for track in playlist_tracks:
            embed_urls.append(f"https://open.spotify.com/embed/track/{track['id']}")
        
        return jsonify({
            'success': True,
            'playlist_name': ai_recommendations.get('playlist_name', f"{name}'s Mood Playlist"),
            'mood_analysis': ai_recommendations.get('mood_analysis', 'Enjoy your personalized playlist!'),
            'tracks': playlist_tracks,
            'embed_urls': embed_urls,
            'total_tracks': len(playlist_tracks)
        })
        
    except Exception as e:
        print(f"Error in analyze_mood: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Callback route for Spotify OAuth (if needed in future)
@app.route('/callback')
def callback():
    # This route is required for Spotify OAuth setup
    # Currently not used but needed for app registration
    return redirect(url_for('index'))

# Health check route
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'spotify_configured': bool(SPOTIFY_CLIENT_ID)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)