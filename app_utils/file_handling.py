import eyed3
from eyed3.id3.frames import ImageFrame
from typing import Optional
import string
import os
import requests
import unicodedata
import re
from mutagen.mp4 import MP4, MP4Cover

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def download_album_image(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as file:
        file.write(requests.get(url).content)

def sanitize_filename(filename):
    
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    return ''.join(c for c in filename if c in valid_chars).replace("#", "").replace(".", "")

def set_metadata(
    mp3_file_path: str,
    *,
    artist_name: Optional[str] = None,
    album_name: Optional[str] = None,
    album_artist: Optional[str] = None,
    track_number: Optional[int] = None,
    track_name: Optional[str] = None,
    track_artist: Optional[str] = None,
    release_year: Optional[int] = None,
    artwork_path: Optional[str] = None,
    description: Optional[str] = None
) -> None:
    """
    Writes metadata to an MP3 file. All metadata parameters are optional except the MP3 file path.

    Args:
        mp3_file_path (str): Path to the MP3 file.
        artist_name (Optional[str]): Name of the main artist. Defaults to None.
        album_name (Optional[str]): Album name. Defaults to None.
        album_artist (Optional[str]): Album artist name. Defaults to None.
        track_number (Optional[int]): Track number. Defaults to None.
        track_name (Optional[str]): Track name. Defaults to None.
        track_artist (Optional[str]): Track artist name. Defaults to None.
        release_year (Optional[int]): Release year. Defaults to None.
        artwork_path (Optional[str]): Path to the artwork file. Defaults to None.
        description (Optional[str]): Additional description. Defaults to None.

    Raises:
        FileNotFoundError: If the MP3 file or artwork is not found.
        eyed3.Error: If there is an error in loading or saving metadata.
    """
    try:
        # Load MP3 file
        audio_file = eyed3.load(mp3_file_path)
        if audio_file is None:
            raise ValueError(f"Unable to load the MP3 file: {mp3_file_path}")

        # Set metadata if provided
        if artist_name:
            audio_file.tag.artist = artist_name
        if album_name:
            audio_file.tag.album = album_name
        if album_artist:
            audio_file.tag.album_artist = album_artist
        if track_number:
            audio_file.tag.track_num = track_number
        if track_name:
            audio_file.tag.title = track_name
        if track_artist:
            audio_file.tag.artist = track_artist
        if release_year:
            audio_file.tag.release_date = release_year
        if description:
            audio_file.tag.comments.set(description)
        if artwork_path:
            with open(artwork_path, 'rb') as artwork_file:
                audio_file.tag.images.set(
                    ImageFrame.FRONT_COVER,
                    artwork_file.read(),
                    'image/jpeg'
                )

        # Save metadata
        audio_file.tag.save()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {e.filename}") from e
    except eyed3.Error as e:
        raise eyed3.Error(f"Error processing MP3 metadata: {e}") from e


def set_m4a_metadata(
    m4a_file_path: str,
    *,
    artist_name: Optional[str] = None,
    album_name: Optional[str] = None,
    album_artist: Optional[str] = None,
    track_number: Optional[int] = None,
    track_name: Optional[str] = None,
    track_artist: Optional[str] = None,
    release_year: Optional[int] = None,
    artwork_path: Optional[str] = None,
    description: Optional[str] = None
) -> None:
    """
    Writes metadata to an M4A file. All metadata parameters are optional except the M4A file path.

    Args:
        m4a_file_path (str): Path to the M4A file.
        artist_name (Optional[str]): Name of the main artist. Defaults to None.
        album_name (Optional[str]): Album name. Defaults to None.
        album_artist (Optional[str]): Album artist name. Defaults to None.
        track_number (Optional[int]): Track number. Defaults to None.
        track_name (Optional[str]): Track name. Defaults to None.
        track_artist (Optional[str]): Track artist name. Defaults to None.
        release_year (Optional[int]): Release year. Defaults to None.
        artwork_path (Optional[str]): Path to the artwork file. Defaults to None.
        description (Optional[str]): Additional description. Defaults to None.

    Raises:
        FileNotFoundError: If the M4A file or artwork is not found.
        mutagen.MutagenError: If there is an error in processing metadata.
    """
    if not os.path.isfile(m4a_file_path):
        raise FileNotFoundError(f"The M4A file was not found: {m4a_file_path}")

    audio = MP4(m4a_file_path)

    # Set metadata if provided
    if artist_name:
        audio['©ART'] = [artist_name]
    if album_name:
        audio['©alb'] = [album_name]
    if album_artist:
        audio['aART'] = [album_artist]
    if track_name:
        audio['©nam'] = [track_name]
    if track_artist:
        # Typically, '©ART' is the track artist. If distinct from album artist, set it here.
        audio['©ART'] = [track_artist]

    if track_number:
        # 'trkn' expects a tuple in the form (track_number, total_tracks)
        # If total number of tracks is unknown, use 0
        audio['trkn'] = [(track_number, 0)]

    if release_year:
        # M4A/MP4 files typically store year as a string
        audio['©day'] = [str(release_year)]

    if description:
        audio['©cmt'] = [description]

    if artwork_path:
        if not os.path.isfile(artwork_path):
            raise FileNotFoundError(f"The artwork file was not found: {artwork_path}")
        with open(artwork_path, 'rb') as f:
            cover_data = f.read()
        # MP4Cover art types: MP4Cover.FORMAT_JPEG or MP4Cover.FORMAT_PNG
        # We'll assume JPEG; detect if needed.
        audio['covr'] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]

    # Save the changes
    try:
        audio.save()
    except Exception as e:
        raise e
