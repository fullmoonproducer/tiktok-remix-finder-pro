import streamlit as st
import pandas as pd
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

st.set_page_config(page_title="TikTok Remix Finder PRO", layout="wide")
st.title("🎧 TikTok Remix Finder PRO — Find Trending Songs to Remix")

# ------------------------------------------------------------------
#  Deezer Top 50 (Global, no token required)
# ------------------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_deezer_top_tracks(top_n=50):
    try:
        r = requests.get("https://api.deezer.com/chart/0/tracks", timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])[:top_n]
        songs = []
        for i, tr in enumerate(data):
            songs.append({
                "rank": i + 1,
                "artist": tr["artist"]["name"],
                "title": tr["title"],
                "link": tr["link"]
            })
        return pd.DataFrame(songs)
    except Exception as e:
        st.warning(f"⚠️ Deezer error: {e}")
        return pd.DataFrame()

# ------------------------------------------------------------------
#  Kworb TikTok Chart
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_kworb_tiktok_top(country="US", top_n=25):
    url = f"https://kworb.net/charts/tiktok/{country.lower()}.html"
    try:
        soup = BeautifulSoup(requests.get(url, timeout=10).text, "html.parser")
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

# ------------------------------------------------------------------
#  Tokchart (TikTok Trending)
# ------------------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_tokchart_songs(top_n=50):
    """Scrape tokchart.com trending songs"""
    url = "https://tokchart.com/"
    try:
        soup = BeautifulSoup(requests.get(url, timeout=10).text, "html.parser")
        items = soup.select("div.table-container tr")[1:top_n+1]
        songs = []
        for i, row in enumerate(items):
            cols = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cols) >= 3:
                rank, title, artist = cols[:3]
                songs.append({"rank": rank, "artist": artist, "title": title})
        return pd.DataFrame(songs)
    except Exception as e:
        st.warning(f"⚠️ Tokchart error: {e}")
        return pd.DataFrame()

# ------------------------------------------------------------------
#  Apple Music playlist scrape (TikTok Songs 2025)
# ------------------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_apple_tiktok_playlist():
    url = "https://music.apple.com/gb/playlist/tiktok-songs-2025-trending-tracks/pl.d9dcaa71eae146549c216c6fc81640bd"
    try:
        soup = BeautifulSoup(requests.get(url, timeout=10).text, "html.parser")
        rows = soup.select("div.songs-list-row")
        songs = []
        for i, row in enumerate(rows, 1):
            title = row.get("aria-label", "")
            artist = row.select_one(".songs-list__col--artist").get_text(strip=True) if row.select_one(".songs-list__col--artist") else ""
            songs.append({"rank": i, "artist": artist, "title": title})
        return pd.DataFrame(songs)
    except Exception as e:
        st.warning(f"⚠️ Apple Music error: {e}")
        return pd.DataFrame()

# ------------------------------------------------------------------
#  iTunes Genre Lookup
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_genre(artist, title):
    try:
        q = quote(f"{artist} {title}")
        res = requests.get(f"https://itunes.apple.com/search?term={q}&limit=1", timeout=5).json()
        if res.get("results"):
            return res["results"][0].get("primaryGenreName", "Unknown")
    except Exception:
        pass
    return "Unknown"

# ------------------------------------------------------------------
#  Sidebar & Data Selection
# ------------------------------------------------------------------
st.sidebar.header("Filters")
region = st.sidebar.selectbox("Region", ["US","UK","DE","FR","Global"])
keyword = st.sidebar.text_input("Search by artist or title", "")
source = st.sidebar.radio("Data Source", [
    "TikTok (Kworb)",
    "TikTok (Tokchart)",
    "Apple Music TikTok Playlist",
    "Deezer Top 50 (Global)"
])

# ------------------------------------------------------------------
#  Data fetch logic
# ------------------------------------------------------------------
if "df" not in st.session_state:
    if "Tokchart" in source:
        st.session_state.df = fetch_tokchart_songs()
    elif "Apple" in source:
        st.session_state.df = fetch_apple_tiktok_playlist()
    elif "Deezer" in source:
        st.session_state.df = fetch_deezer_top_tracks()
    else:
        st.session_state.df = fetch_kworb_tiktok_top(region)

if st.sidebar.button("🔄 Update Song List"):
    with st.spinner("Updating…"):
        if "Tokchart" in source:
            st.session_state.df = fetch_tokchart_songs()
        elif "Apple" in source:
            st.session_state.df = fetch_apple_tiktok_playlist()
        elif "Deezer" in source:
            st.session_state.df = fetch_deezer_top_tracks()
        else:
            st.session_state.df = fetch_kworb_tiktok_top(region)
        st.success("✅ Updated!")

df = st.session_state.df.copy()

# ------------------------------------------------------------------
#  Quick Genre Filters (BPM ranges)
# ------------------------------------------------------------------
st.subheader("🎚️ Quick Genre Filters")
genres = {
    "House (120–128 BPM)":(120,128),
    "Techno (125–135 BPM)":(125,135),
    "Trap/Drill (130–150 BPM)":(130,150),
    "Drum & Bass (160–180 BPM)":(160,180),
    "Dubstep (138–142 BPM)":(138,142),
    "Trance (130–140 BPM)":(130,140)
}
cols = st.columns(len(genres))
selected_genre=None
for i,(g,b) in enumerate(genres.items()):
    if cols[i].button(g):
        selected_genre=g
        st.info(f"🎵 Showing songs for **{g}** ({b[0]}–{b[1]} BPM)")

# ------------------------------------------------------------------
#  Genre lookup + Remix ideas + Links
# ------------------------------------------------------------------
if not df.empty:
    with st.spinner("Fetching genres & suggestions…"):
        df["genre"]=df.apply(lambda r:fetch_genre(r["artist"],r["title"]),axis=1)
        df["Remix suggestion"]=df["genre"].apply(lambda _:random.choice(list(genres.keys())))
        df["YouTube Link"]=df.apply(lambda r:f"https://www.youtube.com/results?search_query={quote(r['artist']+' '+r['title'])}",axis=1)
        df["Stream Link"]=df.get("link", None)

if keyword:
    df=df[df.apply(lambda r:keyword.lower() in (r["artist"]+r["title"]).lower(),axis=1)]
if selected_genre:
    df["match"]=df["Remix suggestion"].apply(lambda g:g==selected_genre)
    df=df.sort_values(by="match",ascending=False).drop(columns="match")

# ------------------------------------------------------------------
#  Tabs (Remix Finder & YouTube Links)
# ------------------------------------------------------------------
tab1,tab2=st.tabs(["🎧 Remix Finder","📺 YouTube Links"])
with tab1:
    st.markdown("### 🔊 Trending Songs & Remix Ideas")
    st.dataframe(df[["rank","artist","title","genre","Remix suggestion"]])
    st.markdown("### 🎲 Random Song to Remix")
    if st.button("Give me a random remix idea"):
        if len(df)>0:
            song=df.sample(1).iloc[0]
            st.success(f"🎧 **{song['title']}** — {song['artist']} ({song['genre']}) → Remix into **{song['Remix suggestion']}!**")
            link=song.get("Stream Link") or "#"
            st.markdown(f"[🎵 YouTube]({song['YouTube Link']}) | [🎧 Stream]({link})")
        else:
            st.warning("No songs available.")
with tab2:
    st.markdown("### 📺 YouTube Search Links for All Songs")
    for _,r in df.iterrows():
        st.markdown(f"- [{r['artist']} — {r['title']}]({r['YouTube Link']})")

st.caption("Sources: Kworb TikTok Charts • Tokchart • Apple Music TikTok Playlist • Deezer Global Top 50 • iTunes Genres • Built with ❤️ using Streamlit")







