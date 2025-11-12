import streamlit as st
import pandas as pd
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# --------------------------------------------------------
# CONFIG
# --------------------------------------------------------
SPOTIFY_TOKEN = "BQAsPdUpxXPcr8vlYUyCARNi2hLmLqLFgcCGEbpXgnJgxlpMTlqAkvjj53_suQ4qtcF4ffJS-gZHeog3CFr1L7XThiGSLe9jfk4lVLgppAswBsXB1u9vaRwjyXsNuxZ5mQh3fp3sZ-lBVgL5KL6Pf6zUcqcyVcttjpjrx36_N69Xh-yfWa172t6Gphid4lSpFSZWV9lJi-n09gK0G58qGJbDBRPFTQRtZiiW6MgDEh1aWVxsfS-OHw72WEeTFYpE4rAqFN5Ccom2iJI0xoC1fvImARxxiHPufymYXAQbTfqcExEyv1Y9WKkMOZ26JQMQAdqx"
SPOTIFY_VIRAL_50_ID = "37i9dQZEVXbLiRSasKsNU9"

st.set_page_config(page_title="TikTok & Spotify Remix Finder PRO", layout="wide")
st.title("🎧 TikTok & Spotify Remix Finder PRO — Find Trending Songs to Remix")

# --------------------------------------------------------
# Spotify playlist fetch using your existing token
# --------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_spotify_playlist_tracks(playlist_id, token, top_n=50):
    """Fetch tracks from Spotify playlist using existing bearer token"""
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit={top_n}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        st.error(f"Spotify API error: {resp.status_code} — {resp.text}")
        return pd.DataFrame()
    data = resp.json()
    songs = []
    for i, item in enumerate(data.get("items", [])):
        track = item.get("track")
        if track:
            artist = ", ".join([a["name"] for a in track["artists"]])
            title = track["name"]
            songs.append({"rank": i + 1, "artist": artist, "title": title})
    return pd.DataFrame(songs)

# --------------------------------------------------------
# TikTok trending fetch
# --------------------------------------------------------
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
        for row in table.find_all("tr")[1:top_n + 1]:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                rank, artist, title = cols[:3]
                songs.append({"rank": rank, "artist": artist, "title": title})
    return pd.DataFrame(songs)

# --------------------------------------------------------
# Genre detection via iTunes
# --------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_genre_from_itunes(artist, title):
    try:
        q = quote(f"{artist} {title}")
        url = f"https://itunes.apple.com/search?term={q}&limit=1"
        data = requests.get(url, timeout=5).json()
        if data.get("results"):
            return data["results"][0].get("primaryGenreName", "Unknown")
    except:
        return "Unknown"
    return "Unknown"

# --------------------------------------------------------
# Sidebar filters
# --------------------------------------------------------
st.sidebar.header("Filters")
region = st.sidebar.selectbox("Region", ["US", "UK", "DE", "FR", "Global"])
keyword = st.sidebar.text_input("Search by artist or title", "")
source = st.sidebar.radio("Data Source", ["TikTok", "Spotify (Viral Global 50)"])

# --------------------------------------------------------
# Fetch data depending on source
# --------------------------------------------------------
if "df" not in st.session_state:
    if source == "Spotify (Viral Global 50)":
        st.session_state.df = fetch_spotify_playlist_tracks(SPOTIFY_VIRAL_50_ID, SPOTIFY_TOKEN)
    else:
        st.session_state.df = fetch_kworb_tiktok_top(region, 25)

if st.sidebar.button("🔄 Update Song List"):
    with st.spinner("Updating song list..."):
        if source == "Spotify (Viral Global 50)":
            st.session_state.df = fetch_spotify_playlist_tracks(SPOTIFY_VIRAL_50_ID, SPOTIFY_TOKEN)
        else:
            st.session_state.df = fetch_kworb_tiktok_top(region, 25)
        st.success("✅ Song list updated!")

df = st.session_state.df.copy()

# --------------------------------------------------------
# Genre + BPM Filters
# --------------------------------------------------------
st.subheader("🎚️ Quick Genre Filters")

genres = {
    "House (120–128 BPM)": (120, 128),
    "Techno (125–135 BPM)": (125, 135),
    "Trap / Drill (130–150 BPM)": (130, 150),
    "Drum & Bass (160–180 BPM)": (160, 180),
    "Dubstep (138–142 BPM)": (138, 142),
    "Trance (130–140 BPM)": (130, 140),
}

cols = st.columns(len(genres))
selected_genre = None
for i, (genre, bpm_range) in enumerate(genres.items()):
    if cols[i].button(genre):
        selected_genre = genre
        st.info(f"🎵 Showing songs suited for **{genre}** ({bpm_range[0]}–{bpm_range[1]} BPM)")

# --------------------------------------------------------
# Add genre, remix suggestion, links
# --------------------------------------------------------
if not df.empty:
    with st.spinner("Fetching genres & remix ideas..."):
        df["genre"] = df.apply(lambda r: fetch_genre_from_itunes(r["artist"], r["title"]), axis=1)
        df["Remix suggestion"] = df["genre"].apply(lambda _: random.choice(list(genres.keys())))
        df["YouTube Link"] = df.apply(
            lambda r: f"https://www.youtube.com/results?search_query={quote(r['artist'] + ' ' + r['title'])}",
            axis=1,
        )
        df["Spotify Link"] = df.apply(
            lambda r: f"https://open.spotify.com/search/{quote(r['artist'] + ' ' + r['title'])}",
            axis=1,
        )

if keyword:
    df = df[df.apply(lambda r: keyword.lower() in (r["artist"] + r["title"]).lower(), axis=1)]

if selected_genre:
    df["match"] = df["Remix suggestion"].apply(lambda g: g == selected_genre)
    df = df.sort_values(by="match", ascending=False).drop(columns="match")

# --------------------------------------------------------
# Tabs
# --------------------------------------------------------
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
                f"[🎵 YouTube]({song['YouTube Link']}) | [🎧 Spotify]({song['Spotify Link']})"
            )
        else:
            st.warning("No songs available. Try updating or changing filters.")

with tab2:
    st.markdown("### 📺 YouTube Search Links for All Songs")
    for _, row in df.iterrows():
        st.markdown(f"- [{row['artist']} — {row['title']}]({row['YouTube Link']})")

st.caption(
    "Data from TikTok (Kworb), Spotify Viral Global 50, and iTunes Genres • Built with ❤️ using Streamlit"
)






