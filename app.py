import os
import urllib.parse
import requests
import re
import json
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
import datetime
import pandas as pd
import logging
import eyed3
from eyed3.id3.frames import ImageFrame
import streamlit as st
import spotdl 
import subprocess
from app_utils import file_handling, spotify_utils, yt_utils

st.set_page_config(page_title="Spotify Downloader", page_icon="🎵", layout="wide")

# Logging setup
logging.basicConfig(filename="downloader.log", level=logging.INFO, format='%(asctime)s - %(message)s')

# Load environment variables
load_dotenv(dotenv_path='.env')

download_path = os.path.join(os.getcwd(), "downloads_yt_dlp")
os.makedirs(download_path, exist_ok=True)
def get_access_token():
    # Spotify API setup - load defaults from environment if available
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    redirect_uri = os.getenv("REDIRECT_URL")

    st.title("Spotify Access Token")

    # Let the user override the environment variables via input fields
    client_id = st.text_input("Client ID", client_id)
    client_secret = st.text_input("Client Secret", client_secret)
    redirect_uri = st.text_input("Redirect URI", redirect_uri)

    # Initialize the OAuth client once
    sp_oauth = spotify_utils.get_sp_oauth(client_id, client_secret, redirect_uri)

    # Try to get cached token first
    token_info = sp_oauth.get_cached_token()

    if token_info:
        access_token = token_info["access_token"]
        if spotify_utils.test_token(access_token):
            st.success("Valid token found in cache.")
            st.session_state.access_token = access_token
    else:
        st.error("No valid token found in cache.")
        
    # If the user wants to get a new access token or didn't have one
    with st.expander("Get new access token"):
        auth_url = sp_oauth.get_authorize_url()
        st.write(f"[Authorize App Here]({auth_url})")

        auth_code = st.text_input("Enter the authorization code from link above")
        st.info(f"The authorization code will be in the address bar: {redirect_uri}?code=<AUTHORIZATION CODE>")
        if auth_code:
            token_info = sp_oauth.get_access_token(auth_code)
            st.session_state.access_token = token_info["access_token"]
            st.success("Access token retrieved and stored in session state.")


with st.sidebar:
    
    get_access_token()

def download_track_ydl(track_obj, download_path=download_path, file_extension="mp3", ydl_opts=None):
    track_name = track_obj["track"]["name"]
    track_artists = ", ".join([x["name"] for x in track_obj["track"]["artists"]])
    track_album = track_obj["track"]["album"]["name"]
    track_number = str(track_obj["track"]["track_number"]).zfill(2)

    file_name_no_extension = file_handling.sanitize_filename(f"{track_artists}-{track_album}-{track_number}-{track_name}")
    file_name = f"{file_name_no_extension}.{file_extension}"
    final_file_path = os.path.join(download_path, file_name)

    if not os.path.exists(final_file_path):
        query = f"{track_name} {track_artists} {track_album}"
        video_url, video_title = yt_utils.find_video_in_youtube(query)
        if not video_url:
            logging.error(f"Could not find video for {query}")
            return None
        else:
            logging.info(f"Found video for {query}: {video_url} - {video_title}")

            if not ydl_opts:
                ydl_opts = {
                    'cookies': 'cookies.txt',
                    'format': 'm4a/bestaudio/best',
                    'outtmpl': os.path.join(download_path, f'{file_name_no_extension}.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'm4a',
                    }],
                }
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                return final_file_path
            except Exception as e:
                logging.error(f"Error downloading {query}: {e}")
                return None

def download_multiple_tracks(download_path, tracks=None, playlist_id=None):
    if playlist_id:
        tracks = spotify_utils.get_playlist_tracks(st.session_state.access_token, playlist_id)

    total_tracks = len(tracks)
    progress_bar = st.progress(0)

    for track_num, track in enumerate(tracks, start=1):
        downloaded_file_path = download_track_ydl(track, download_path, file_extension="m4a")
        if downloaded_file_path:
            download_artwork_path = os.path.join(download_path, "artwork", f"{track['track']['album']['id']}.jpg")
            file_handling.download_album_image(track["track"]["album"]["images"][0]["url"], download_artwork_path)

            file_handling.set_m4a_metadata(
                downloaded_file_path,
                artist_name=track["track"]["artists"][0]["name"],
                album_name=track["track"]["album"]["name"],
                album_artist=track["track"]["album"]["artists"][0]["name"],
                track_number=track["track"]["track_number"],
                track_name=track["track"]["name"],
                track_artist=track["track"]["artists"][0]["name"],
                release_year=track["track"]["album"]["release_date"][:4],
                artwork_path=download_artwork_path,
                description=track["track"]["external_urls"]["spotify"]
            )

        progress_bar.progress(track_num / total_tracks)

st.title("Spotify Downloader")

if st.session_state.access_token:
    playlists = {"Liked": "Liked"}
    playlists.update(spotify_utils.get_user_playlists(st.session_state.access_token))
    selected_playlist = st.selectbox("Select Playlist:", options=playlists.keys())

    def get_playlist_as_df(playlist_tracks):
        df = pd.DataFrame(
            [
                {   
                    "Download": True,
                    "Track": track["track"]["name"],
                    "Artists": [x["name"] for x in track["track"]["artists"]],
                    "Album": track["track"]["album"]["name"],
                    "Track Number": track["track"]["track_number"],
                    "Release Date": track["track"]["album"]["release_date"],
                    "Added At": track["added_at"],
                    "Artwork URL": track["track"]["album"]["images"][0]["url"],
                    "Track ISRC": track["track"]["external_ids"]["isrc"],
                    "Artist ID": track["track"]["artists"][0]["id"],
                    "Album ID": track["track"]["album"]["id"],
                    "Track ID": track["track"]["id"],
                    "Spotify URL": track["track"]["external_urls"]["spotify"],
                    "Popularity": track["track"]["popularity"],
                    "track_obj": track
                }
                for track in playlist_tracks
            ]
        )

        return df

    playlist_tracks = spotify_utils.get_playlist_tracks(st.session_state.access_token, playlists[selected_playlist])

    df_playlist_tracks = st.data_editor(
        get_playlist_as_df(playlist_tracks),
        column_config = (colconfig := {
            "Download": st.column_config.CheckboxColumn("Download", pinned=True),
            "Track": st.column_config.TextColumn("Track", pinned=True, disabled=True),
            "Artists": st.column_config.ListColumn("Artists",pinned=True),
            "Artwork URL": st.column_config.ImageColumn("Artwork", pinned=True),
            "Album": st.column_config.TextColumn("Album", disabled=True, pinned=True),
            "Track Number": st.column_config.NumberColumn("Track Number", disabled=True),
            "Release Date": st.column_config.TextColumn("Release Date", disabled=True),
            "Popularity": st.column_config.NumberColumn("Popularity", disabled=True),
            "Spotify URL": st.column_config.LinkColumn("Spotify URL", disabled=True, display_text="Spotify"),
            "Added At": st.column_config.TextColumn("Added At", disabled=True),
            "Artist ID": st.column_config.TextColumn("Artist ID", disabled=True),
            "Album ID": st.column_config.TextColumn("Album ID", disabled=True),
            "Track ID": st.column_config.TextColumn("Track ID", disabled=True),
            "Track ISRC": st.column_config.TextColumn("ISRC", disabled=True),
            "track_obj": st.column_config.TextColumn("track_obj", disabled=True),
        }),
        column_order=colconfig.keys(),
        hide_index=True,
        key="playlist_tracks"
    )

    selected_tracks = [eval(x) for x in df_playlist_tracks[df_playlist_tracks["Download"] == True]["track_obj"].tolist()] # I know.

    if st.button("Download selected"):
        print(selected_tracks)
        download_multiple_tracks(download_path, tracks=selected_tracks)
        st.success("Download completed!")
