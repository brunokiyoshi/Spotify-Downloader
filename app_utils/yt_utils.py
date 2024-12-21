import urllib
import re
import requests

def find_video_in_youtube(query):
    search_query = urllib.parse.quote(query)
    html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={search_query}")
    video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
    if video_ids:
        first_result_url = f"https://www.youtube.com/watch?v={video_ids[0]}"
        # get video title from url
        first_result_title = requests.get(first_result_url).text
        title = re.search(r'<title>(.*?)</title>', first_result_title).group(1)
        print(title, first_result_url)
        return first_result_url, title
    return None