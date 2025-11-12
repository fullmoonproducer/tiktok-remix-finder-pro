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
    return pd.DataFrame(songs)


# ----------------------------
# Fetch Spotify Trending Songs
# ----------------------------
@st.cache_data(ttl=3600)
def fetch_spotify_top50():
    """Fetch top tracks from Spotify Charts (via Kworb proxy)"""
    url = "https://kworb.net/spotify/country/global_weekly.html"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        songs = []
        if table:
            for row in table.find_all("tr")[1:26]:
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 3:
                    rank, artist, title = cols[:3]
                    songs.append({"rank": rank, "artist": artist, "title": title})
        return pd.DataFrame(songs)
    except Exception as e:
        st.warning(f"⚠️ Could not fetch Spotify data ({e})")
        return pd.DataFrame()


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
# Sidebar Filters
# ----------------------------
st.sidebar.header("Filters")
region = st.sidebar.selectbox("Region", ["US", "UK", "DE", "FR", "Global"])
keyword = st.sidebar.text_input("Search by artist or title", "")
source = st.sidebar.radio("Data Source", ["TikTok", "Spotify (Top 50)"])

# ----------------------------
# Data Fetch + Update Button
# ----------------------------
if "df" not in st.session_state:
    st.session_state.df = fetch_kworb_tiktok_top(region, 25)

if st.sidebar.button("🔄 Update Song List"):
    with st.spinner("Updating song list..."):
        if source == "Spotify (Top 50)":
            st.session_state.df = fetch_spotify_top50()
        else:
            st.session_state.df = fetch_kworb_tiktok_top(region, 25)
        st.success("✅ Song list updated!")

df = st.session_state.df.copy()

# ----------------------------
# Quick Genre BPM Buttons
# ----------------------------
st.subheader("🎚️ Quick Genre Filters")

genres = {
    "House (120–128 BPM)": (120, 128),
    "Techno (125–135 BPM)": (125, 135),
    "Trap / Drill (130–150 BPM)": (130, 150),
    "Drum & Bass (160–180 BPM)": (160, 180),
    "Dubstep (138–142 BPM)": (138, 142),
    "Trance (130–140 BPM)": (130, 140),
}

selected_genre = None
cols = st.columns(len(genres))
for i, (genre, bpm_range) in enumerate(genres.items()):
    if cols[i].button(genre):
        selected_genre = genre
        st.info(f"🎵 Showing songs suited for **{genre}** ({bpm_range[0]}–{bpm_range[1]} BPM)")

# ----------------------------
# Fetch Real Genres + Remix Suggestions
# ----------------------------
if not df.empty:
    with st.spinner("Fetching genres & remix ideas..."):
        df["genre"] = df.apply(lambda r: fetch_genre_from_itunes(r["artist"], r["title"]), axis=1)
        df["Remix suggestion"] = df["genre"].apply(lambda _: random.choice(list(genres.keys())))
        df["YouTube Link"] = df.apply(
            lambda r: f"https://www.youtube.com/results?search_query={quote(r['artist']+' '+r['title'])}", axis=1
        )
        df["Spotify Link"] = df.apply(
            lambda r: f"https://open.spotify.com/search/{quote(r['artist']+' '+r['title'])}", axis=1
        )
    st.success("✅ Genres and remix suggestions added!")

# Apply keyword filter
if keyword:
    df = df[df.apply(lambda r: keyword.lower() in (r["artist"] + r["title"]).lower(), axis=1)]

# ----------------------------
# Reorder list based on selected quick genre
# ----------------------------
if selected_genre:
    df["is_match"] = df["Remix suggestion"].apply(lambda x: x == selected_genre)
    df = df.sort_values(by="is_match", ascending=False).drop(columns="is_match")

# ----------------------------
# Create Tabs
# ----------------------------
tab1, tab2 = st.tabs(["🎧 Remix Finder", "📺 YouTube Links"])

with tab1:
    st.markdown("### 🔊 Trending Songs & Remix Ideas")
    st.dataframe(df[["rank", "artist", "title", "genre", "Remix suggestion"]])

    st.markdown("### 🎲 Random Song to Remix")
    if st.button("Give me a random remix idea"):
        if len(df) > 0:
            song = df.sample(1).iloc[0]
            st.success(
                f"🎧 **{song['title']}** — {song['artist']} ({song['genre']}) → Try remixing into **{song['Remix suggestion']}!**"
            )
            st.markdown(
                f"[🎵 YouTube Search]({song['YouTube Link']}) | [🎧 Spotify]({song['Spotify Link']})"
            )
        else:
            st.warning("No songs available. Try updating or changing filters.")

with tab2:
    st.markdown("### 📺 YouTube Search Links for All Songs")
    for _, row in df.iterrows():
        st.markdown(f"- [{row['artist']} – {row['title']}]({row['YouTube Link']})")

st.caption(
    "Data from TikTok (Kworb), Spotify, and Apple Music API • Built with ❤️ for EDM producers using Streamlit"
)





