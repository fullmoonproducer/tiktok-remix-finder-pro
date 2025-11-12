import streamlit as st
import pandas as pd
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# ----------------------------
# Page setup
# ----------------------------
st.set_page_config(page_title="TikTok Remix Finder PRO", layout="wide")
st.title("🎧 TikTok Remix Finder PRO — Find Trending Songs to Remix")

# ----------------------------
# Fetch TikTok Trending Songs
# ----------------------------
@st.cache_data(ttl=3600)
def fetch_kworb_tiktok_top(country_code="US", top_n=25):
    url = f"https://kworb.net/charts/tiktok/{country_code.lower()}.html"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as e:
        st.warning(f"⚠️ Could not fetch data ({e})")
        return pd.DataFrame()

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    songs = []
    if table:
        for row in table.find_all("tr")[1:top_n+1]:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                rank, artist, title = cols[:3]
                songs.append({"rank": rank, "artist": artist, "title": title})
    df = pd.DataFrame(songs)
    return df


# ----------------------------
# Fetch Real Genre via iTunes
# ----------------------------
@st.cache_data(ttl=3600)
def fetch_genre_from_itunes(artist, title):
    """Fetch real genre from iTunes API"""
    try:
        q = quote(f"{artist} {title}")
        url = f"https://itunes.apple.com/search?term={q}&limit=1"
        data = requests.get(url, timeout=5).json()
        if data.get("results"):
            return data["results"][0].get("primaryGenreName", "Unknown")
    except:
        return "Unknown"
    return "Unknown"


# ----------------------------
# EDM Remix Target Mapping
# ----------------------------
def recommend_remix_target(original_genre):
    mapping = {
        "Pop": "House (120–128 BPM)",
        "Hip-Hop": "Techno (125–135 BPM)",
        "Rap": "Trap / Drill (130–150 BPM)",
        "Rock": "Drum & Bass (160–180 BPM)",
        "Country": "House (120–128 BPM)",
        "Electronic": "Trance (130–140 BPM)",
        "R&B": "House (120–128 BPM)",
        "Latin": "Techno (125–135 BPM)",
        "Dance": "House (120–128 BPM)",
    }
    for key, val in mapping.items():
        if key.lower() in original_genre.lower():
            return val
    return "House (120–128 BPM)"  # default fallback to a re


