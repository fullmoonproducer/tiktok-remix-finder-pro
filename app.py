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
# Suggest Remix Direction
# ----------------------------
def recommend_remix_target(original_genre):
    mapping = {
        "Pop": "House / Techno",
        "Hip-Hop": "Trap / Techno",
        "Rap": "Trap / Techno",
        "Rock": "Drum & Bass / Dubstep",
        "Country": "House / Techno",
        "Electronic": "Trap / Trance",
        "R&B": "Deep House / Trance",
        "Latin": "Tech House / DnB",
    }
    for key, val in mapping.items():
        if key.lower() in original_genre.lower():
            return val
    return "Any EDM style"


# ----------------------------
# Sidebar Filters
# ----------------------------
st.sidebar.header("Filters")
region = st.sidebar.selectbox("Region", ["US", "UK", "DE", "FR", "Global"])
keyword = st.sidebar.text_input("Search by artist or title", "")

# ----------------------------
# Data Fetch + Update Button
# ----------------------------
if "df" not in st.session_state:
    st.session_state.df = fetch_kworb_tiktok_top(region, 25)

if st.sidebar.button("🔄 Update Song List"):
    with st.spinner("Updating song list..."):
        st.session_state.df = fetch_kworb_tiktok_top(region, 25)
        st.success("✅ Song list updated!")

df = st.session_state.df.copy()

# ----------------------------
# Genre & BPM Buttons
# ----------------------------
st.subheader("🎚️ Quick Genre BPM Ranges")

genres = {
    "House (120–128 BPM)": (120, 128),
    "Techno (125–135 BPM)": (125, 135),
    "Trap / Drill (130–150 BPM)": (130, 150),
    "Drum & Bass (160–180 BPM)": (160, 180),
    "Dubstep (138–142 BPM)": (138, 142),
    "Trance (130–140 BPM)": (130, 140),
}

cols = st.columns(len(genres))
for i, (genre, bpm_range) in enumerate(genres.items()):
    if cols[i].button(genre):
        st.session_state.selected_bpm_range = bpm_range
        st.info(f"🎵 Songs that could fit or be remixed into **{genre}** ({bpm_range[0]}–{bpm_range[1]} BPM)")

# ----------------------------
# Fetch Real Genres
# ----------------------------
if not df.empty:
    with st.spinner("Fetching real genres..."):
        df["genre"] = df.apply(lambda r: fetch_genre_from_itunes(r["artist"], r["title"]), axis=1)
        df["Remix suggestion"] = df["genre"].apply(recommend_remix_target)
    st.success("✅ Genres loaded!")

# Apply keyword filter
if keyword:
    df = df[df.apply(lambda r: keyword.lower() in (r["artist"] + r["title"]).lower(), axis=1)]

# ----------------------------
# Display Table
# ----------------------------
st.markdown("### 🔊 Current Trending Songs + Remix Ideas")
st.dataframe(df[["rank", "artist", "title", "genre", "Remix suggestion"]])

# ----------------------------
# Random Song Remix Challenge
# ----------------------------
st.markdown("### 🎲 Random Song to Remix")
if st.button("Give me a random remix idea"):
    if len(df) > 0:
        song = df.sample(1).iloc[0]
        st.success(
            f"🎧 **{song['title']}** — {song['artist']} ({song['genre']}) → Try remixing into **{song['Remix suggestion']}!**"
        )
        st.markdown(
            f"[🎵 YouTube Search]({f'https://www.youtube.com/results?search_query={quote(song['artist'] + ' ' + song['title'])}})"
        )
    else:
        st.warning("No songs available. Try updating or changing filters.")

st.caption("Data from Kworb + Apple Music API • Built with ❤️ for EDM producers using Streamlit")

