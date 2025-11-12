import streamlit as st
import pandas as pd
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# --------------------------------------------------------
# CONFIG
# --------------------------------------------------------
st.set_page_config(page_title="TikTok Remix Finder PRO", layout="wide")
st.title("🎧 TikTok Remix Finder PRO — Find Trending Songs to Remix")

# --------------------------------------------------------
# 1. Deezer Global Top 50
# --------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_deezer_top_tracks(top_n=50):
    url = "https://api.deezer.com/chart/0/tracks"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])[:top_n]
        return pd.DataFrame([{
            "rank": i + 1,
            "artist": t["artist"]["name"],
            "title": t["title"],
            "source": "Deezer"
        } for i, t in enumerate(data)])
    except Exception as e:
        st.warning(f"⚠️ Deezer error: {e}")
        return pd.DataFrame()

# --------------------------------------------------------
# 2. iTunes Top Songs (RSS)
# --------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_itunes_top_songs(country="us", top_n=25):
    url = f"https://rss.applemarketingtools.com/api/v2/{country}/music/most-played/50/songs.json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("feed", {}).get("results", [])[:top_n]
        return pd.DataFrame([{
            "rank": i + 1,
            "artist": s["artistName"],
            "title": s["name"],
            "source": "iTunes"
        } for i, s in enumerate(data)])
    except Exception as e:
        st.warning(f"⚠️ iTunes error: {e}")
        return pd.DataFrame()

# --------------------------------------------------------
# 3. Kworb TikTok Chart
# --------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_kworb_tiktok_top(country="US", top_n=25):
    url = f"https://kworb.net/charts/tiktok/{country.lower()}.html"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("table tr")[1:top_n + 1]
        out = []
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                out.append({"rank": cols[0], "artist": cols[1], "title": cols[2], "source": "TikTok"})
        return pd.DataFrame(out)
    except Exception as e:
        st.warning(f"⚠️ Kworb error: {e}")
        return pd.DataFrame()

# --------------------------------------------------------
# 4. MUSICO Dataset (sample)
# --------------------------------------------------------
@st.cache_data
def load_musico_sample():
    url = "https://zenodo.org/record/4277311/files/musico-sample.csv"
    try:
        df = pd.read_csv(url)
        df = df.rename(columns=str.lower)
        df = df[["title", "artist", "genre", "bpm"]].dropna()
        return df
    except Exception as e:
        st.warning(f"⚠️ MUSICO dataset unavailable: {e}")
        return pd.DataFrame()

musico_df = load_musico_sample()

# --------------------------------------------------------
# Sidebar Controls
# --------------------------------------------------------
st.sidebar.header("Filters")
region = st.sidebar.selectbox("Region", ["US", "UK", "DE", "FR", "Global"])
keyword = st.sidebar.text_input("Search artist or song", "")
source = st.sidebar.radio("Data Source", [
    "All Sources (Combined)",
    "TikTok (Kworb)",
    "Deezer Global Top 50",
    "iTunes Top Songs"
])

# --------------------------------------------------------
# Data Fetching Logic
# --------------------------------------------------------
if "df" not in st.session_state:
    if "TikTok" in source:
        st.session_state.df = fetch_kworb_tiktok_top(region)
    elif "iTunes" in source:
        st.session_state.df = fetch_itunes_top_songs(region.lower())
    elif "Deezer" in source:
        st.session_state.df = fetch_deezer_top_tracks()
    else:
        combined = pd.concat([
            fetch_kworb_tiktok_top(region),
            fetch_deezer_top_tracks(),
            fetch_itunes_top_songs(region.lower())
        ], ignore_index=True)
        st.session_state.df = combined.drop_duplicates(subset=["title", "artist"])

if st.sidebar.button("🔄 Refresh All Data"):
    st.session_state.df = pd.DataFrame()  # clears cache
    st.experimental_rerun()

df = st.session_state.df.copy()

# --------------------------------------------------------
# Merge with MUSICO Data (for real genres & BPM)
# --------------------------------------------------------
if not df.empty and not musico_df.empty:
    df["title_lower"] = df["title"].str.lower()
    df["artist_lower"] = df["artist"].str.lower()
    musico_df["title_lower"] = musico_df["title"].str.lower()
    musico_df["artist_lower"] = musico_df["artist"].str.lower()
    df = pd.merge(df, musico_df, on=["title_lower", "artist_lower"], how="left", suffixes=("", "_musico"))
    df["genre"] = df["genre"].fillna("Unknown")
    df["bpm"] = df["bpm"].fillna("–")

# --------------------------------------------------------
# Add YouTube links & Remix Suggestions
# --------------------------------------------------------
df["YouTube Link"] = df.apply(
    lambda r: f"https://www.youtube.com/results?search_query={quote(r['artist'] + ' ' + r['title'])}", axis=1)
df["Remix suggestion"] = df.apply(lambda _: random.choice([
    "House (120–128 BPM)",
    "Techno (125–135 BPM)",
    "Trap/Drill (130–150 BPM)",
    "Drum & Bass (160–180 BPM)",
    "Dubstep (138–142 BPM)",
    "Trance (130–140 BPM)"
]), axis=1)

# --------------------------------------------------------
# Filters and Sorting
# --------------------------------------------------------
if keyword:
    df = df[df.apply(lambda r: keyword.lower() in (r["artist"] + r["title"]).lower(), axis=1)]

# --------------------------------------------------------
# Quick Genre Buttons (EDM)
# --------------------------------------------------------
st.subheader("🎚️ Quick Genre Filters")
genres = {
    "House (120–128 BPM)": (120, 128),
    "Techno (125–135 BPM)": (125, 135),
    "Trap/Drill (130–150 BPM)": (130, 150),
    "Drum & Bass (160–180 BPM)": (160, 180),
    "Dubstep (138–142 BPM)": (138, 142),
    "Trance (130–140 BPM)": (130, 140)
}
cols = st.columns(len(genres))
selected_genre = None
for i, (g, bpm) in enumerate(genres.items()):
    if cols[i].button(g):
        selected_genre = g
        st.info(f"🎵 Showing songs suited for **{g}** ({bpm[0]}–{bpm[1]} BPM)")

if selected_genre:
    df["match"] = df["Remix suggestion"].apply(lambda g: g == selected_genre)
    df = df.sort_values(by="match", ascending=False).drop(columns="match")

# --------------------------------------------------------
# Tabs
# --------------------------------------------------------
tab1, tab2 = st.tabs(["🎧 Remix Finder", "📺 YouTube Links"])

with tab1:
    st.markdown("### 🔊 Trending Songs & Remix Ideas (with MUSICO Data)")
    st.dataframe(df[["rank", "artist", "title", "genre", "bpm", "Remix suggestion", "source"]])

    st.markdown("### 🎲 Random Song to Remix")
    if st.button("Give me a random remix idea"):
        if len(df) > 0:
            song = df.sample(1).iloc[0]
            st.success(
                f"🎧 **{song['title']}** — {song['artist']} ({song['genre']} / {song['bpm']} BPM) → Try remixing into **{song['Remix suggestion']}!**"
            )
            st.markdown(f"[🎵 YouTube Search]({song['YouTube Link']})")
        else:
            st.warning("No songs available.")

with tab2:
    st.markdown("### 📺 YouTube Search Links for All Songs")
    for _, r in df.iterrows():
        st.markdown(f"- [{r['artist']} — {r['title']}]({r['YouTube Link']})")

st.caption("Data from Deezer • iTunes RSS • Kworb TikTok • MUSICO Dataset • Built with ❤️ using Streamlit")

