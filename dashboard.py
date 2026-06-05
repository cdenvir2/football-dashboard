import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from matplotlib import rcParams
from mplsoccer import Pitch, VerticalPitch, FontManager
from understatapi import UnderstatClient
import html

#Importing Data ------------------------------------------------------------------------------

st.set_page_config(
    page_title="Shot Analytics Dashboard",
    layout="wide"
)


st.markdown(
        """
        <h1 style='text-align: center;'>
            Home vs Away Shot Analytics Dashboard
        </h1>
        <h4 style='text-align: center; color: #B0B0B0;'>
            Brighton vs Fulham | Second Half Analysis | Understat Data
        </h4>
        <hr>
        """,
        unsafe_allow_html=True
)
match_id = 28780

@st.cache_data
def load_understat_data(match_id):
    understat = UnderstatClient()

    match_data = understat.match(match=str(match_id)).get_match_info()
    match_df = pd.DataFrame([match_data])

    shots = understat.match(match=str(match_id)).get_shot_data()

    home_shots = pd.DataFrame(shots['h'])
    away_shots = pd.DataFrame(shots['a'])

    home_shots['team_side'] = 'home'
    away_shots['team_side'] = 'away'

    shots_df = pd.concat(
        [home_shots, away_shots],
        ignore_index=True
    )

    shots_df['minute'] = pd.to_numeric(shots_df['minute'], errors='coerce')
    shots_df['X'] = pd.to_numeric(shots_df['X'], errors='coerce')
    shots_df['Y'] = pd.to_numeric(shots_df['Y'], errors='coerce')
    shots_df['xG'] = pd.to_numeric(shots_df['xG'], errors='coerce')

    shots_df = shots_df.dropna(subset=['minute', 'X', 'Y', 'xG'])

    shots_df['x'] = shots_df['X'] * 120
    shots_df['y'] = shots_df['Y'] * 80
    shots_df['size'] = shots_df['xG'] * 5000

    return match_df, shots_df

match_df, shots_df = load_understat_data(match_id)

shots_df['minute'] = shots_df['minute'].astype(int)
h_shots = shots_df[(shots_df['h_a'] == 'h') & (shots_df['minute'] >= 46)].copy()
a_shots = shots_df[(shots_df['h_a'] == 'a') & (shots_df['minute'] >= 46)].copy()

#Transform to plot on pitches
h_shots['X'] = pd.to_numeric(h_shots['X'], errors='coerce')
h_shots['Y'] = pd.to_numeric(h_shots['Y'], errors='coerce')
h_shots['xG'] = pd.to_numeric(h_shots['xG'], errors='coerce')
h_shots = h_shots.dropna(subset=['X', 'Y', 'xG'])
h_shots['x'] = h_shots['X'] * 120
h_shots['y'] = h_shots['Y'] * 80
h_shots['size'] = h_shots['xG']*5000
h_shots.head()

h_shots_on_target = h_shots[h_shots['result'].isin(['Goal', 'SavedShot'])]
h_shots_off_target = h_shots[~h_shots['result'].isin(['Goal', 'SavedShot'])]

#Transform to plot on pitches
a_shots['X'] = pd.to_numeric(a_shots['X'], errors='coerce')
a_shots['Y'] = pd.to_numeric(a_shots['Y'], errors='coerce')
a_shots['xG'] = pd.to_numeric(a_shots['xG'], errors='coerce')
a_shots = a_shots.dropna(subset=['X', 'Y', 'xG'])
a_shots['x'] = a_shots['X'] * 120
a_shots['y'] = a_shots['Y'] * 80
a_shots['size'] = a_shots['xG']*5000
a_shots.head()

a_shots_on_target = a_shots[a_shots['result'].isin(['Goal', 'SavedShot'])]
a_shots_off_target = a_shots[~a_shots['result'].isin(['Goal', 'SavedShot'])]

#Setup Page -----------------------------------------------------------------------------------
home_name = "Brighton"
away_name = "Fulham"
home_col, divider, away_col = st.columns([1, 0.05, 1])

#Main Shot Map -----------------------------------------------------------------------------------

with home_col:
    st.markdown(
        f"""
        <h2 style='
            text-align:center;
            color:#0057B8;
            margin-bottom:0px;
        '>
        🔵 {home_name}
        </h2>
        """,
        unsafe_allow_html=True
    )
    left, right = st.columns([2,3])

    with left:
        st.subheader("xG Timeline")
        h_shots['minute'] = h_shots['minute'].astype(int)
        h_shots['xG'] = pd.to_numeric(h_shots['xG'])

        xg_timeline = (
            h_shots.groupby('minute')['xG'].sum().cumsum()
        )

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')

        # Plot cumulative xG as a step chart
        ax.step(
            xg_timeline.index,
            xg_timeline.values,
            where='post',
            linewidth=3,
            color='#00b4d8'
        )  

        ax.scatter(
            xg_timeline.index,
            xg_timeline.values,
            s=70,
            color='#00b4d8',
            edgecolor='white',
            zorder=3
        )

        # Goal markers
        goals = h_shots[h_shots['result'].str.strip() == 'Goal']

        for _, row in goals.iterrows():
            ax.axvline(row['minute'], color='#ff4d4d', linestyle='--', linewidth=1.5)

            ax.text(
                row['minute'] + 0.4,
                ax.get_ylim()[1] * 0.93,
                'Goal',
                color='#ff4d4d',
                fontsize=11,
                fontweight='bold'
            )

        # Labels and title
        ax.set_xlabel('Minute', color='#c7d5cc')
        ax.set_ylabel('Cumulative xG', color='#c7d5cc')

        ax.tick_params(colors='#c7d5cc')

        # Grid
        ax.grid(True, linestyle='--', alpha=0.2)

        # Remove top/right borders
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        ax.spines['left'].set_color('#c7d5cc')
        ax.spines['bottom'].set_color('#c7d5cc')

        home_xg_fig = plt.gcf()
        st.pyplot(home_xg_fig, use_container_width=True)
        plt.close(home_xg_fig)

    #Player xG Charts & xG by Shot Type -----------------------------------------------------------------------------------

        st.subheader("xG Players")
        # Group and convert to normal DataFrame
        h_top_5 = (
            h_shots
            .groupby('player', as_index=False)['xG']
            .sum()
            .sort_values('xG', ascending=False)
            .head(5)
        )
        h_top_5['player'] = h_top_5['player'].apply(html.unescape)

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')

        bars = ax.barh(
            h_top_5['player'],
            h_top_5['xG'],
            color='#00b4d8'
        )

        ax.invert_yaxis()

        for bar in bars:
            width = bar.get_width()
            ax.text(
            width + 0.01,                    
            bar.get_y() + bar.get_height()/2,
            f'{width:.2f}',
            va='center',
            ha='left',
            color='white',
            fontweight='bold'
        )

        
        ax.set_xlabel('')
        ax.set_xticks([])
        ax.tick_params(colors='#c7d5cc')

        for spine in ax.spines.values():
            spine.set_visible(False)

        home_players_fig = plt.gcf()
        st.pyplot(home_players_fig, use_container_width=True)
        plt.close(home_players_fig)


        st.subheader("xG Shot Type")
        h_shot_type = (
            h_shots.groupby('shotType')['xG'].sum().sort_values(ascending=True)
        )

        fig, ax = plt.subplots(figsize=(8,5))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')

        bars = ax.barh(h_shot_type.index, h_shot_type.values, color='#00b4d8')

        for bar in bars:
            width = bar.get_width()
            ax.text(width+0.01, bar.get_y()+bar.get_height()/2,
                    f'{width:.2f}', va='center', color='white', fontweight='bold')

    
        ax.set_xticks([])
        ax.tick_params(axis='y', colors='#c7d5cc')

        for spine in ax.spines.values():
            spine.set_visible(False)

        home_shot_type_fig = plt.gcf()
        st.pyplot(home_shot_type_fig, use_container_width=True)
        plt.close(home_shot_type_fig)


    with right:
        st.subheader("Home Shot Map")
        #Setup Pitch
        pitch = VerticalPitch(
            pitch_type='statsbomb',
            pitch_color="#22312b",
            line_color="#c7d5cc",
            half=True,
            pad_top=2
        )   
        fig, ax = pitch.draw(figsize=(16,11))
        fig.set_facecolor("#22312b")

        pitch.scatter(
            h_shots_off_target['x'],
            h_shots_off_target['y'],
            color='red',
            s=h_shots_off_target['size'],
            edgecolors='white',
            linewidth=1.5,
            alpha=0.8,
            label='Off Target',
            ax=ax
        )

        pitch.scatter(
            h_shots_on_target['x'],
            h_shots_on_target['y'],
            color='lime',
            s=h_shots_on_target['size'],
            edgecolors='white',
            linewidth=1.5,
            alpha=0.8,
            label='On Target',
            ax=ax
        )

        legend = ax.legend(
            markerscale=0.3,
            loc='upper right',
            facecolor='white',
            edgecolor='white'
        )
        home_shots_fig = plt.gcf()
        st.pyplot(home_shots_fig, use_container_width=True)
        plt.close(home_shots_fig)

        st.subheader("Player Summary")
        h_players = (
            h_shots.groupby('player').agg(
                Goals = ('result', lambda x: (x == 'Goal').sum()), Shots=('player', 'count')
            ).reset_index().sort_values('Goals', ascending=False)
        )
        h_players['player'] = h_players['player'].apply(html.unescape)
        st.dataframe(
            h_players,
            hide_index=True,
            use_container_width=True
        )
    
    m1, m2, m3, m4, m5 = st.columns(5)
    h_shots['X'] = pd.to_numeric(h_shots['X'], errors='coerce')
    h_shots['Y'] = pd.to_numeric(h_shots['Y'], errors='coerce')
    h_shots['xG'] = pd.to_numeric(h_shots['xG'], errors='coerce')

    h_shots = h_shots.dropna(subset=['X', 'Y', 'xG'])

    h_shots['x'] = h_shots['X'] * 120
    h_shots['y'] = h_shots['Y'] * 80

    xg = h_shots['xG'].astype(float).sum()
    shots = len(h_shots)
    shots_on_target = len(h_shots[h_shots['result'].isin(['Goal','SavedShot'])])
    goals = len(h_shots[h_shots['result']=='Goal'])
    avg_shot_distance = (((120-h_shots['x'])**2+(40-h_shots['y'])**2)**0.5).mean()
    xg_per_shot = xg/shots if shots > 0 else 0
    m1.metric("xG", round(xg, 2))
    m2.metric("Shots", shots)
    m3.metric("Shots on Target", shots_on_target)
    m4.metric("Goals", goals)
    m5.metric("xG/Shot", round(xg_per_shot, 2))

with divider:
    st.markdown(
        """
        <div style="
            border-left: 2px solid #444;
            height: 100%;
            min-height: 1200px;
            margin: auto;
        "></div>
        """,
        unsafe_allow_html=True
    )

with away_col:
    st.markdown(
        f"""
        <h2 style='
            text-align:center;
            color:white;
            margin-bottom:0px;
        '>
        ⚫ {away_name}
        </h2>
        """,
        unsafe_allow_html=True
    )
    left, right = st.columns([3,2])

    with left:
        #Setup Pitch
        pitch = VerticalPitch(
            pitch_type='statsbomb',
            pitch_color="#22312b",
            line_color="#c7d5cc",
            half=True,
            pad_top=2
        )
        fig, ax = pitch.draw(figsize=(16,11))
        fig.set_facecolor("#22312b")

        pitch.scatter(
            a_shots_off_target['x'],
            a_shots_off_target['y'],
            color='red',
            s=a_shots_off_target['size'],
            edgecolors='white',
            linewidth=1.5,
            alpha=0.8,
            label='Off Target',
            ax=ax
        )

        pitch.scatter(
            a_shots_on_target['x'],
            a_shots_on_target['y'],
            color='lime',
            s=a_shots_on_target['size'],
            edgecolors='white',
            linewidth=1.5,
            alpha=0.8,
            label='On Target',
            ax=ax
        )

        legend = ax.legend(
            markerscale=0.3,
            loc='upper right',
            facecolor='white',
            edgecolor='white'
        )
        st.subheader("Away Shot Map")
        away_shots_fig = plt.gcf()
        st.pyplot(away_shots_fig)
        plt.close(away_shots_fig)

        st.subheader("Player Summary")
        a_players = (
            a_shots.groupby('player').agg(
                Goals = ('result', lambda x: (x == 'Goal').sum()), Shots=('player', 'count')
            ).reset_index().sort_values('Goals', ascending=False)
        )
        a_players['player'] = a_players['player'].apply(html.unescape)
        st.dataframe(
            a_players,
            hide_index=True,
            use_container_width=True
        )

    with right:
        st.subheader("xG Timeline")
        a_shots['minute'] = a_shots['minute'].astype(int)
        a_shots['xG'] = pd.to_numeric(a_shots['xG'])

        xg_timeline = (
            a_shots.groupby('minute')['xG'].sum().cumsum()
        )

        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')

        # Plot cumulative xG as a step chart
        ax.step(
            xg_timeline.index,
            xg_timeline.values,
            where='post',
            linewidth=3,
            color='#00b4d8'
        )

        ax.scatter(
            xg_timeline.index,
            xg_timeline.values,
            s=70,
            color='#00b4d8',
            edgecolor='white',
            zorder=3
        )

        # Goal markers
        goals = a_shots[a_shots['result'].str.strip() == 'Goal']

        for _, row in goals.iterrows():
            ax.axvline(row['minute'], color='#ff4d4d', linestyle='--', linewidth=1.5)

            ax.text(
                row['minute'] + 0.4,
                ax.get_ylim()[1] * 0.93,
                'Goal',
                color='#ff4d4d',
                fontsize=11,
                fontweight='bold'
            )

        # Labels and title
        ax.set_xlabel('Minute', color='#c7d5cc')
        ax.set_ylabel('Cumulative xG', color='#c7d5cc')

        ax.tick_params(colors='#c7d5cc')

        # Grid
        ax.grid(True, linestyle='--', alpha=0.2)

        # Remove top/right borders
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        ax.spines['left'].set_color('#c7d5cc')
        ax.spines['bottom'].set_color('#c7d5cc')

        away_xg_fig = plt.gcf()
        st.pyplot(away_xg_fig, use_container_width=True)
        plt.close(away_xg_fig)

        st.subheader("xG Players")
        # Group and convert to normal DataFrame
        a_top_5 = (
            a_shots
            .groupby('player', as_index=False)['xG']
            .sum()
            .sort_values('xG', ascending=False)
            .head(5)
        )
        a_top_5['player'] = a_top_5['player'].apply(html.unescape)

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')

        bars = ax.barh(
            a_top_5['player'],
            a_top_5['xG'],
            color='#00b4d8'
        )

        ax.invert_yaxis()
        ax.invert_xaxis()
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")

        for bar in bars:
            width = bar.get_width()
            ax.text(
            width + 0.01,                    
            bar.get_y() + bar.get_height()/2,
            f'{width:.2f}',
            va='center',
            ha='right',
            color='white',
            fontweight='bold'
        )

        ax.set_xlabel('')
        ax.set_xticks([])
        ax.tick_params(colors='#c7d5cc')

        for spine in ax.spines.values():
            spine.set_visible(False)

        away_players_fig = plt.gcf()
        st.pyplot(away_players_fig, use_container_width=True)
        plt.close(away_players_fig)

        st.subheader("xG Shot Type")
        a_shot_type = (
            a_shots.groupby('shotType')['xG'].sum().sort_values(ascending=True)
        )

        fig, ax = plt.subplots(figsize=(8,5))
        fig.patch.set_alpha(0)
        ax.set_facecolor('none')

        bars = ax.barh(a_shot_type.index, a_shot_type.values, color='#00b4d8')
        ax.invert_xaxis()
        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")

        for bar in bars:
            width = bar.get_width()
            ax.text(width+0.04, bar.get_y()+bar.get_height()/2,
                    f'{width:.2f}', va='center', color='white', fontweight='bold')

        ax.set_xticks([])
        ax.tick_params(axis='y', colors='#c7d5cc')

        for spine in ax.spines.values():
            spine.set_visible(False)

        away_shot_type_fig = plt.gcf()
        st.pyplot(away_shot_type_fig, use_container_width=True)
        plt.close(away_shot_type_fig)

    m1, m2, m3, m4, m5 = st.columns(5)
    a_shots['X'] = pd.to_numeric(a_shots['X'], errors='coerce')
    a_shots['Y'] = pd.to_numeric(a_shots['Y'], errors='coerce')
    a_shots['xG'] = pd.to_numeric(a_shots['xG'], errors='coerce')

    a_shots = a_shots.dropna(subset=['X', 'Y', 'xG'])

    a_shots['x'] = a_shots['X'] * 120
    a_shots['y'] = a_shots['Y'] * 80

    xg = a_shots['xG'].astype(float).sum()
    shots = len(a_shots)
    shots_on_target = len(a_shots[a_shots['result'].isin(['Goal','SavedShot'])])
    goals = len(a_shots[a_shots['result']=='Goal'])
    avg_shot_distance = (((120-a_shots['x'])**2+(40-a_shots['y'])**2)**0.5).mean()
    xg_per_shot = xg/shots if shots > 0 else 0
    m1.metric("xG", round(xg, 2))
    m2.metric("Shots", shots)
    m3.metric("Shots on Target", shots_on_target)
    m4.metric("Goals", goals)
    m5.metric("xG/Shot", round(xg_per_shot, 2))