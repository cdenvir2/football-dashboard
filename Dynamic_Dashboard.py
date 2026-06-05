import html
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from mplsoccer import VerticalPitch
from understatapi import UnderstatClient

# --------------------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------------------

st.set_page_config(
    page_title="Shot Analytics Dashboard",
    layout="wide"
)

# --------------------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading Brighton matches...")
def load_brighton_matches(season: str) -> pd.DataFrame:
    understat = UnderstatClient()
    matches = understat.team("Brighton").get_match_data(season=season)
    return pd.DataFrame(matches)

@st.cache_data(show_spinner="Loading match shot data...")
def load_understat_data(match_id: int):
    understat = UnderstatClient()

    match_data = understat.match(match=str(match_id)).get_match_info()
    match_df = pd.DataFrame([match_data])

    shots = understat.match(match=str(match_id)).get_shot_data()
    home_shots = pd.DataFrame(shots.get("h", []))
    away_shots = pd.DataFrame(shots.get("a", []))

    home_shots["team_side"] = "home"
    away_shots["team_side"] = "away"

    shots_df = pd.concat([home_shots, away_shots], ignore_index=True)

    if shots_df.empty:
        return match_df, shots_df
    
    shots_df["minute"] = pd.to_numeric(shots_df["minute"], errors="coerce")
    shots_df["X"] = pd.to_numeric(shots_df["X"], errors="coerce")
    shots_df["Y"] = pd.to_numeric(shots_df["Y"], errors="coerce")
    shots_df["xG"] = pd.to_numeric(shots_df["xG"], errors="coerce")

    shots_df = shots_df.dropna(subset=["minute", "X", "Y", "xG"]).copy()
    shots_df["minute"] = shots_df["minute"].astype(int)

    #Convert to Pitch co-ords
    shots_df["x"] = shots_df["X"]*120
    shots_df["y"] = shots_df["Y"]*80
    shots_df["size"] = shots_df["xG"]*5000

    if "player" in shots_df.columns:
        shots_df["player"] = shots_df["player"].apply(html.unescape)

    return match_df, shots_df

# --------------------------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------------------------

def clean_team_name(value):
    if isinstance(value, dict):
        return value.get("title", value.get("name", ""))
    
    if isinstance(value, str):
        try:
            value_dict = eval(value)
            if isinstance(value_dict, dict):
                return value_dict.get("title", value_dict.get("name", value))
        except Exception:
            return value

    return str(value) 

def get_match_label(row: pd.Series) -> str:
    date_value = row.get("datetime", row.get("date", ""))

    try:
        date_value = pd.to_datetime(date_value).date()
    except Exception:
        pass

    home = row.get("h_title", row.get("home_team", row.get("h", "Home")))
    away = row.get("a_title", row.get("away_team", row.get("a", "Away")))

    home = clean_team_name(home)
    away = clean_team_name(away)

    return f"{date_value} | {home} vs {away}"

def get_team_names(match_df: pd.DataFrame, selected_match_row: pd.Series):
    home = selected_match_row.get(
        "h_title",
        selected_match_row.get("home_team", selected_match_row.get("h", "Home"))
    )

    away = selected_match_row.get(
        "a_title",
        selected_match_row.get("away_team", selected_match_row.get("a", "Away"))
    )

    home_name = clean_team_name(home)
    away_name = clean_team_name(away)

    return home_name or "Home", away_name or "Away"

def split_shots_by_side(shots_df: pd.DataFrame, start_minute: int):
    h_shots = shots_df[(shots_df["h_a"] == "h") & (shots_df["minute"] >= start_minute)].copy()
    a_shots = shots_df[(shots_df["h_a"] == "a") & (shots_df["minute"] >= start_minute)].copy()
    return h_shots, a_shots

def split_on_target(shots: pd.DataFrame):
    on_target = shots[shots["result"].isin(["Goal", "SavedShot"])]
    off_target = shots[~shots["result"].isin(["Goal", "SavedShot"])]
    return on_target, off_target

def section_title(text: str, colour: str="white"):
    st.markdown(
        f"""
        <h2 style='text-align:center; color:{colour}; margin-bottom:0.2rem;'>
            {text}
        </h2>
        """,
        unsafe_allow_html=True
    )

def plot_xg_timeline(shots: pd.DataFrame, title: str):
    st.subheader(title)

    if shots.empty:
        st.indo("No shots in this period")
        return
    
    xg_timeline = shots.groupby("minute")["xG"].sum().cumsum()

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    ax.step(xg_timeline.index, xg_timeline.values, where="post", linewidth=3, color="#00b4d8")
    ax.scatter(xg_timeline.index, xg_timeline.values, s=70, color="#00b4d8", edgecolor="white", zorder=3)

    goals = shots[shots["result"].str.strip() == "Goal"]
    for _, row in goals.iterrows():
        ax.axvline(row["minute"], color="#ff4d4d", linestyle="--", linewidth=1.5)
        ax.text(row["minute"] + 0.4, ax.get_ylim()[1] * 0.93, "Goal", color="#ff4d4d", fontsize=11, fontweight="bold")

    ax.set_xlabel("Minute", color="#c7d5cc")
    ax.set_ylabel("Cumulative xG", color="#c7d5cc")
    ax.tick_params(colors="#c7d5cc")
    ax.grid(True, linestyle="--", alpha=0.2)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#c7d5cc")
    ax.spines["bottom"].set_color("#c7d5cc")

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

def plot_player_xg(shots: pd.DataFrame, title: str, mirror: bool=False):
    st.subheader(title)

    if shots.empty:
        st.info("No player xG available")
        return
    
    top_5 = (
        shots.groupby("player", as_index=False)["xG"]
        .sum()
        .sort_values("xG", ascending=False)
        .head(5)
    )

    fig, ax = plt.subplots(figsize=(8,5))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    bars = ax.barh(top_5["player"], top_5["xG"], color="#00b4d8")
    ax.invert_yaxis()

    if mirror:
        ax.invert_xaxis()
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")

    for bar in bars:
        width = bar.get_width()
        x_text = width + 0.01
        ha="left"
        if mirror:
            x_text = width + 0.01
            ha = "right"

        ax.text(x_text, bar.get_y() + bar.get_height()/2, f"{width:.2f}", va="center", ha=ha, color="white", fontweight="bold")
    
    ax.set_xlabel("")
    ax.set_xticks([])
    ax.tick_params(colors="#c7d5cc")

    for spine in ax.spines.values():
        spine.set_visible(False)

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

def plot_shot_type(shots: pd.DataFrame, title: str, mirror: bool = False):
    st.subheader(title)

    if shots.empty or "shotType" not in shots.columns:
        st.info("No shot type data available")
        return
    
    shot_type = shots.groupby("shotType")["xG"].sum().sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(8,5))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    bars = ax.barh(shot_type.index, shot_type.values, color="#00b4d8")

    if mirror:
        ax.invert_xaxis()
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")

    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, f"{width:.2f}", va="center", color="white", fontweight="bold")

    ax.set_xticks([])
    ax.tick_params(axis="y", colors="#c7d5cc")

    for spine in ax.spines.values():
        spine.set_visible(False)

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

def plot_shot_map(shots: pd.DataFrame, title: str):
    st.subheader(title)

    pitch = VerticalPitch(
        pitch_type="statsbomb",
        pitch_color="#22312b",
        line_color="#c7d5cc",
        half=True,
        pad_top=2
    )

    fig, ax = pitch.draw(figsize=(16, 11))
    fig.set_facecolor("#22312b")

    if not shots.empty:
        on_target, off_target = split_on_target(shots)

        pitch.scatter(
            off_target["x"],
            off_target["y"],
            color="red",
            s=off_target["size"],
            edgecolors="white",
            linewidth=1.5,
            alpha=0.8,
            label="Off Target",
            ax=ax
        )

        pitch.scatter(
            on_target["x"],
            on_target["y"],
            color="lime",
            s=on_target["size"],
            edgecolors="white",
            linewidth=1.5,
            alpha=0.8,
            label="On Target",
            ax=ax
        )

        ax.legend(markerscale=0.3, loc="upper right", facecolor="white", edgecolor="white")

    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

def show_player_summary(shots: pd.DataFrame):
    st.subheader("Player Summary")

    if shots.empty:
        st.info("No player summary available.")
        return

    players = (
        shots.groupby("player")
        .agg(
            Goals=("result", lambda x: (x == "Goal").sum()),
            Shots=("player", "count")
        )
        .reset_index()
        .sort_values(["Goals", "Shots"], ascending=False)
    )

    st.dataframe(players, hide_index=True, use_container_width=True)

def show_metric_cards(shots:pd.DataFrame):
    m1, m2, m3, m4, m5 = st.columns(5)

    xg = shots["xG"].sum() if not shots.empty else 0
    total_shots = len(shots)
    shots_on_target = len(shots[shots["result"].isin(["Goal", "SavedShot"])]) if not shots.empty else 0
    goals = len(shots[shots["result"] == "Goal"]) if not shots.empty else 0
    xg_per_shot = xg / total_shots if total_shots > 0 else 0

    m1.metric("xG", round(xg, 2))
    m2.metric("Shots", total_shots)
    m3.metric("Shots on Target", shots_on_target)
    m4.metric("Goals", goals)
    m5.metric("xG/Shot", round(xg_per_shot, 2))

def render_team_section(team_name: str, shots: pd.DataFrame, side:str):
    is_brighton = team_name == "Brighton"
    is_home = side == "home"
    colour = "#0057B8" if is_brighton else "white"
    icon = "🔵" if is_brighton else "⚫"

    section_title(f"{icon} {team_name}", colour)

    if is_home:
        left, right = st.columns([2, 3])
        with left:
            plot_xg_timeline(shots, "xG Timeline")
            plot_player_xg(shots, "xG Players")
            plot_shot_type(shots, "xG Shot Type")
        with right:
            plot_shot_map(shots, "Home Shot Map")
            show_player_summary(shots)
    else:
        left, right = st.columns([3, 2])
        with left:
            plot_shot_map(shots, "Away Shot Map")
            show_player_summary(shots)
        with right:
            plot_xg_timeline(shots, "xG Timeline")
            plot_player_xg(shots, "xG Players")
            plot_shot_type(shots, "xG Shot Type")
    show_metric_cards(shots)

# --------------------------------------------------------------------------------------
# Sidebar controls
# --------------------------------------------------------------------------------------

st.sidebar.title("Match Controls")

season = st.sidebar.selectbox(
    "Choose Brighton season",
    options=["2025", "2024", "2023"],
    index=0
)

start_minute = st.sidebar.slider(
    "Show shots from minute",
    min_value=1,
    max_value=90,
    value = 46
)

matches_df = load_brighton_matches(season)

if matches_df.empty:
    st.error("No Brighton matches found for this season")
    st.stop()

matches_df["match_label"] = matches_df.apply(get_match_label, axis=1)

selected_label = st.sidebar.selectbox(
    "Choose Match",
    options=matches_df["match_label"].tolist()
)

selected_match_row = matches_df.loc[matches_df["match_label"] == selected_label].iloc[0]
match_id = int(selected_match_row["id"])


# --------------------------------------------------------------------------------------
# Main dashboard
# --------------------------------------------------------------------------------------

match_df, shots_df = load_understat_data(match_id)
home_name, away_name = get_team_names(match_df, selected_match_row)
home_name = clean_team_name(home_name)
away_name = clean_team_name(away_name)

st.markdown(
    f"""
    <h1 style='text-align: center;'>
        Home vs Away Shot Analytics Dashboard
    </h1>
    <h4 style='text-align: center; color: #B0B0B0;'>
        {home_name} vs {away_name} | From Minute {start_minute} | Understat Data
    </h4>
    <hr>
    """,
    unsafe_allow_html=True
)

if shots_df.empty:
    st.warning("No shot data available for this match.")
    st.stop()

h_shots, a_shots = split_shots_by_side(shots_df, start_minute)

home_col, divider, away_col = st.columns([1, 0.04, 1])

with home_col:
    render_team_section(home_name, h_shots, "home")

with divider:
    st.markdown(
        """
        <div style="
            border-left: 2px solid #444;
            min-height: 1250px;
            margin: 0 auto;
        "></div>
        """,
        unsafe_allow_html=True
    )

with away_col:
    render_team_section(away_name, a_shots, "away")