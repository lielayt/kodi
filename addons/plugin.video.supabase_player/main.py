import sys
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib.request
import json

# ---------- CONFIG ----------
ADDON = xbmcaddon.Addon()
BASE_URL = "https://myhuovhvodgvqilsyvwg.supabase.co/rest/v1"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15aHVvdmh2b2RndnFpbHN5dndnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIxODQ1MDcsImV4cCI6MjA3Nzc2MDUwN30.zIVLAwMHVPj57MsN4nIGDq1XpvMMuf6YsO-kNJkdh4E"
HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])

# ---------- HELPER FUNCTIONS ----------
def log(msg):
    xbmc.log(f"[Supabase Player] {msg}", xbmc.LOGINFO)

def show_error(message):
    xbmcgui.Dialog().notification('Supabase Player', message, xbmcgui.NOTIFICATION_ERROR, 5000)
    log(f"ERROR: {message}")

def make_request(endpoint, params=None):
    try:
        url = f"{BASE_URL}/{endpoint}"
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
            return json.loads(data)
    except Exception as e:
        show_error(f"Network or parsing error: {str(e)}")
        return None

def fetch_all(endpoint, params=None, batch_size=1000):
    """Fetch all rows from a Supabase table using range headers"""
    all_data = []
    offset = 0
    
    while True:
        headers = HEADERS.copy()
        headers["Range-Unit"] = "items"
        headers["Range"] = f"{offset}-{offset + batch_size - 1}"
        
        try:
            url = f"{BASE_URL}/{endpoint}"
            if params:
                query_string = urllib.parse.urlencode(params)
                url = f"{url}?{query_string}"
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                
                if not data:
                    break  # no more data
                
                all_data.extend(data)
                if len(data) < batch_size:
                    break  # last batch
                
                offset += batch_size
        except Exception as e:
            show_error(f"Error fetching data: {str(e)}")
            break

    return all_data



# ---------- MAIN FUNCTIONS ----------
def list_categories():
    log("Listing categories")
    data = make_request("categories")
    if not data:
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    for cat in data:
        label = cat.get('name', f"Category {cat.get('id', '?')}")
        url = f"{sys.argv[0]}?action=list_items&category_id={cat.get('id')}"
        li = xbmcgui.ListItem(label=label)
        li.setInfo('video', {'title': label, 'mediatype': 'video'})
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
    
    xbmcplugin.endOfDirectory(handle)

def list_items(category_id):
    log(f"Listing items for category: {category_id}")
    data = fetch_all("items", params={"category_id": f"eq.{category_id}"})
    if not data:
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    for item in data:
        item_type = item.get('type', 'movie')
        action = "play_movie" if item_type == "movie" else "list_seasons"
        url = f"{sys.argv[0]}?action={action}&item_id={item.get('id')}"
        label = item.get('name', f"Item {item.get('id', '?')}")
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': item.get('image_url', ''), 'poster': item.get('image_url', '')})
        li.setInfo('video', {'title': label, 'mediatype': 'movie' if item_type=="movie" else 'tvshow'})
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=(item_type=="show"))
    
    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.endOfDirectory(handle)

def list_seasons(item_id):
    log(f"Listing seasons for show: {item_id}")
    data = fetch_all("seasons", params={"show_id": f"eq.{item_id}"})
    if not data:
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    for season in data:
        season_number = season.get('season_number', '?')
        season_label = f"Season {season_number}"
        url = f"{sys.argv[0]}?action=list_episodes&season_id={season.get('id')}"
        li = xbmcgui.ListItem(label=season_label)
        li.setInfo('video', {'title': season_label, 'mediatype': 'season'})
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)

    xbmcplugin.setContent(handle, 'seasons')
    xbmcplugin.endOfDirectory(handle)

def list_episodes(season_id):
    log(f"Listing episodes for season: {season_id}")
    data = fetch_all("episodes", params={"season_id": f"eq.{season_id}"})
    if not data:
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    for ep in data:
        label = ep.get('name', f"Episode {ep.get('id', '?')}")
        url = f"{sys.argv[0]}?action=play_episode&episode_id={ep.get('id')}"
        li = xbmcgui.ListItem(label=label)
        li.setArt({'thumb': ep.get('image_url', '')})
        li.setInfo('video', {'title': label, 'mediatype': 'episode'})
        li.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    xbmcplugin.setContent(handle, 'episodes')
    xbmcplugin.endOfDirectory(handle)

def play_movie(item_id):
    log(f"Playing movie: {item_id}")
    data = make_request("items", params={"id": f"eq.{item_id}"})
    if not data or len(data) == 0:
        show_error("Movie not found")
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return
    
    movie = data[0]
    video_url = movie.get('video_url')
    if not video_url:
        show_error("No video URL found")
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return

    label = movie.get('name', 'Unknown')
    play_item = xbmcgui.ListItem(path=video_url)
    play_item.setInfo('video', {'title': label})
    play_item.setArt({'thumb': movie.get('image_url', '')})
    xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)

def play_episode(episode_id):
    log(f"Playing episode: {episode_id}")
    data = make_request("episodes", params={"id": f"eq.{episode_id}"})
    if not data or len(data) == 0:
        show_error("Episode not found")
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return
    
    ep = data[0]
    video_url = ep.get('video_url')
    if not video_url:
        show_error("No video URL found")
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return

    label = ep.get('name', 'Unknown')
    play_item = xbmcgui.ListItem(path=video_url)
    play_item.setInfo('video', {'title': label})
    play_item.setArt({'thumb': ep.get('image_url', '')})
    xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)

# ---------- ROUTER ----------
def router():
    action = args.get('action', [None])[0]
    log(f"Action: {action}")

    if action is None:
        list_categories()
    elif action == "list_items":
        list_items(args.get('category_id', [''])[0])
    elif action == "list_seasons":
        list_seasons(args.get('item_id', [''])[0])
    elif action == "list_episodes":
        list_episodes(args.get('season_id', [''])[0])
    elif action == "play_movie":
        play_movie(args.get('item_id', [''])[0])
    elif action == "play_episode":
        play_episode(args.get('episode_id', [''])[0])
    else:
        log(f"Unknown action: {action}")

if __name__ == '__main__':
    router()
