import streamlit as st
import pandas as pd
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# --------------------------------------------------------
# APP CONFIG
# --------------------------------------------------------
st.set_page_config(page_title="TikTok Remix Finder PRO", layout="wide")
st.title("🎧 TikTok Remix Finder PRO — Find Trending Songs to Remix")

# --------------------------------------------------------
# Deezer Global Top 50 (no token required)
# --------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_deezer_top_tracks(top_n=50):
    """Fetch Deezer Global Top Tracks"""
    try:
        url = "https://api.deezer.com/chart/0/tracks"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])[:top_n]
        songs = []
        for i, tr in enumerate(data):
            songs.append({
                "rank": i + 1,
                "artist": tr["artist"]["name"],
                "title": tr["title"],
                "deezer_link": tr["link"],
            })
        return pd.DataFrame(songs)
    except Exception as e:
        st.warning(f"⚠️ Deezer fetch error: {e}")
        return pd.DataFrame()

# --------------------------------------------------------
# iTunes RSS Charts (official, open, no auth)
# --------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_itunes_top_songs(country="us", top_n=25):
    """Fetch Apple iTunes Top Songs RSS"""
    url = f"https://rss.applemarketingtools.com/api/v2/{country}/music/most-played/50/songs.json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("feed", {}).get("results", [])[:top_n]
        songs = []
        for i, s in enumerate(data):
            songs.append({
                "rank": i + 1,
                "artist": s["artistName"],
                "title": s["name"],
                "itunes_link": s["url"]
            })
        return pd.DataFrame(songs)
    except Exception as e:
        st.warning(f"⚠️ iTunes fetch error: {e}")
        return pd.DataFrame()

# --------------------------------------------------------
# Kworb TikTok Trending Chart
# --------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_kworb_tiktok_top(country="US", top_n=25):
    """Fetch TikTok trending songs from Kworb"""
    url = f"https://kworb.net/charts/tiktok/{country.lower()}.html"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tr")[1:top_n+1]
        out = []
        for r in rows:
            cols = [c.get_text(strip=True) for c in r.find_all("td")]
            if len(cols) >= 3:
                out.append({"rank": cols[0], "artist": cols[1], "title": cols[2]})
        return pd.DataFrame(out)
    except Exception as e:
        st.warning(f"⚠️ Kworb error: {e}")
        return pd.DataFrame()

# --------------------------------------------------------
# Sidebar Filters
# --------------------------------------------------------
st.sidebar.header("Filters")
region = st.sidebar.selectbox("Region", ["US", "UK", "DE", "FR", "Global"])
keyword = st.sidebar.text_input("Search by artist or title", "")
source = st.sidebar.radio("Data Source", [
    "TikTok (Kworb)",
    "Deezer Global Top 50",
    "iTunes Top Songs"
])

# --------------------------------------------------------
# Fetch Data
# --------------------------------------------------------
if "df" not in st.session_state:
    if "iTunes" in source:
        st.session_state.df = fetch_itunes_top_songs(region.lower())
    elif "Deezer" in source:
        st.session_state.df = fetch_deezer_top_tracks()
    else:
        st.session_state.df = fetch_kworb_tiktok_top(region)

if st.sidebar.button("🔄 Update Song List"):
    with st.spinner("Fetching latest charts..."):
        if "iTunes" in source:
            st.session_state.df = fetch_itunes_top_songs(region.lower())
        elif "Deezer" in source:
            st.session_state.df = fetch_deezer_top_tracks()
        else:
            st.session_state.df = fetch_kworb_tiktok_top(region)
        st.success("✅ Chart updated!")

df = st.session_state.df.copy()

# --------------------------------------------------------
# Add YouTube Links & Random Remix Suggestions
# --------------------------------------------------------
if not df.empty:
    df["YouTube Link"] = df.apply(
        lambda r: f"https://www.youtube.com/results?search_query={quote(r['artist'] + ' ' + r['title'])}",
        axis=1,
    )
    df["Remix suggestion"] = df.apply(
        lambda _: random.choice([
            "House (120–128 BPM)",
            "Techno (125–135 BPM)",
            "Trap/Drill (130–150 BPM)",
            "Drum & Bass (160–180 BPM)",
            "Dubstep (138–142 BPM)",
            "Trance (130–140 BPM)"
        ]),
        axis=1,
    )

# --------------------------------------------------------
# Quick Genre Filter Buttons (EDM)
# --------------------------------------------------------
st.subheader("🎚️ Quick Genre Filters")
genres = {
    "House (120–128 BPM)": (120, 128),
    "Techno (125–135 BPM)": (125, 135),
    "Trap/Drill (130–150 BPM)": (130, 150),
    "Drum & Bass (160–180 BPM)": (160, 180),
    "Dubstep (138–142 BPM)": (138, 142),
    "Trance (130–140 BPM)": (130, 140),
}
cols = st.columns(len(genres))
selected_genre = None
for i, (g, bpm) in enumerate(genres.items()):
    if cols[i].button(g):
        selected_genre = g
        st.info(f"🎵 Showing songs suited for **{g}** ({bpm[0]}–{bpm[1]} BPM)")

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
    display_cols = ["rank", "artist", "title", "Remix suggestion"]
    st.dataframe(df[display_cols])

    st.markdown("### 🎲 Random Song to Remix")
    if st.button("Give me a random remix idea"):
        if len(df) > 0:
            song = df.sample(1).iloc[0]
            st.success(
                f"🎧 **{song['title']}** — {song['artist']} → Try remixing into **{song['Remix suggestion']}!**"
            )
            st.markdown(
                f"[🎵 YouTube Search]({song['YouTube Link']})"
            )
        else:
            st.warning("No songs available. Try updating or changing filters.")

with tab2:
    st.markdown("### 📺 YouTube Search Links for All Songs")
    for _, r in df.iterrows():
        st.markdown(f"- [{r['artist']} — {r['title']}]({r['YouTube Link']})")

st.caption("Data from Deezer Charts • iTunes RSS • Kworb TikTok • Built with ❤️ using Streamlit")
