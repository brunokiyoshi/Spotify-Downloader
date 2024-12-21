
import pandas as pd
import requests
from spotipy import SpotifyOAuth, Spotify, SpotifyException
from spotipy.oauth2 import SpotifyOauthError
import subprocess
import streamlit as st

def get_sp_oauth(client_id=None, client_secret=None, redirect_uri=None):

    try:
        sp_oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-library-read playlist-read-private playlist-read-collaborative",
        )

    except SpotifyOauthError as e:
        print(f"Spotify OAuth setup error: {e}")
        exit(1)

    return sp_oauth

def test_token(token):
    """
    Checks if the provided access token is valid by making a test API call.
    Returns True if the token is valid, False otherwise.
    """
    # Create a Spotify client with the given token directly
    sp = Spotify(auth=token)
    
    try:
        # Try to fetch the current user's profile as a test
        user_profile = sp.current_user()
        # If we successfully retrieved the user profile, token is valid
        return True
    except SpotifyException as e:
        # If the request fails due to authorization, the token is invalid/expired
        if e.http_status == 401:
            return False
        # For other exceptions, raise them or handle as needed
        raise


# Spotify helper functions
def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def get_user_playlists(token):
    headers = get_auth_header(token)
    response = requests.get("https://api.spotify.com/v1/me/playlists", headers=headers)
    response_json = response.json()
    return {item["name"]: item["id"] for item in response_json["items"]}


def get_playlist_tracks(token, playlist_id):
    sp = Spotify(auth=token)
    tracks = []
    offset = 0
    while True:
        if playlist_id == "Liked":
            limit = 50
            response = sp.current_user_saved_tracks(limit=limit, offset=offset)
        else:
            limit = 100
            response = sp.playlist_tracks(playlist_id, limit=limit, offset=offset)
        tracks.extend(response['items'])
        if len(response['items']) < limit:
            break
        offset += limit
    return tracks

