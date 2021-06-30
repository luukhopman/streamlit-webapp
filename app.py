import base64
import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib.patches as mpatches
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from highlight_text import ax_text, fig_text

# ---------- Define functions ----------


def get_url(league, season, week=1):
    '''Generates the appropriate URL based on the parameters'''
    league = league_dict.get(league, 'eng-premier-league')
    url_path = f'schedule/{league}-{season-1}-{season}-spieltag/{week}/'
    url = 'https://www.worldfootball.net/schedule/' + url_path
    return url


def get_season_range(league):
    '''
    Returns the first and last season with data available for the selected league.
    '''
    league = league_dict.get(league, 'eng-premier-league')
    url = f'https://www.worldfootball.net/schedule/{league}'
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')
    seasons = soup.find('select', attrs={'name': 'saison'}).find_all('option')
    first_season = int(seasons[-1].text.split('/')[1])
    last_season = int(seasons[0].text.split('/')[1])
    return first_season, last_season


@st.cache(show_spinner=False)
def scrape_standings(league, season):
    '''
    Returns a DataFrame with the league standings by gameweek for a given season
    '''
    week = 1
    standings = []
    while True:
        url = get_url(league, season, week)
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        standings_table = soup.find_all(
            'table', attrs={'class': 'standard_tabelle'})[1]
        if 'news' in standings_table.find('td').text or '-:-' in page.text:
            break
        else:
            teams = [team.text for team in standings_table.find_all('a')]
            standings.append(teams)
            week += 1

    # Return DataFrame
    return pd.DataFrame(standings).T


def get_patch(p1, p2, color):
    '''Creates a smooth path between two points'''
    Path = mpath.Path
    x1, y1 = p1
    x2, y2 = p2

    if y2 > y1:
        patch = mpatches.PathPatch(
            Path(
                [p1,
                 (x1+(x2-x1)/2, y1),
                 (x1+(x2-x1)/2, y1 + (y2-y1)/2),
                 (x1+(x2-x1)/2, y2),
                 p2],
                [Path.MOVETO, Path.CURVE3, Path.CURVE3,
                 Path.CURVE3, Path.CURVE3
                 ]
            ),
            ec=color, fc='none', zorder=5
        )

    elif y2 < y1:
        patch = mpatches.PathPatch(
            Path([p1,
                  (x1 + (x2-x1)/2, y1),
                  (x1+(x2-x1)/2, y1+(y2-y1)/2),
                  (x1 + (x2-x1)/2, y2),
                  p2],
                 [Path.MOVETO, Path.CURVE3, Path.CURVE3,
                 Path.CURVE3, Path.CURVE3]),
            ec=color, fc='none', zorder=5
        )

    else:
        patch = mpatches.PathPatch(
            Path([p1, p2],
                 [Path.MOVETO, Path.LINETO]),
            ec=color, fc='none', zorder=5
        )

    return patch


# ---------- Change report view width ----------

st.markdown(
    f"""
     <style>
        .reportview-container .main .block-container{{
            max-width: 1500px;
            padding-top: 5rem;
            padding-right: 5rem;
            padding-left: 5rem;
            padding-bottom: 5rem;
            }}
        .reportview-container .main {{
            background-color: #49505c;
            }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- League and Season Selection ----------

# League name mapping to worldfootball.net identifier
league_dict = {'Premier League': 'eng-premier-league',
               'La Liga': 'esp-primera-division',
               'Bundesliga': 'bundesliga',
               'Serie A': 'ita-serie-a',
               'Ligue 1': 'fra-ligue-1',
               'Eredivisie': 'ned-eredivisie',
               'Primeira Liga': 'por-primeira-liga'}

league_min_season = {'Premier League': 'eng-premier-league',
                     'La Liga': 'esp-primera-division',
                     'Bundesliga': 'bundesliga',
                     'Serie A': 'ita-serie-a',
                     'Ligue 1': 'fra-ligue-1',
                     'Eredivisie': 'ned-eredivisie',
                     'Primeira Liga': 'por-primeira-liga'}

st.sidebar.markdown('## Select League and Season')

league_options = list(league_dict.keys())
league = st.sidebar.selectbox('League', league_options)

first_season, last_season = get_season_range(league)
season = st.sidebar.number_input('Season',
                                 min_value=first_season,
                                 max_value=last_season,
                                 value=2020,
                                 help='Enter the last year of the season')
if season:
    season_title = f'Selected season: {season-1}/{str(season)[2:]}'
    st.sidebar.write(season_title)

with st.spinner('Scraping data...'):
    standings = scrape_standings(league, season)

num_teams = len(standings)
num_games = len(standings.columns)
team_names = standings.iloc[:, -1].to_list()


# ---------- Plot configuration ----------

# Sidebar title
st.sidebar.markdown('## Plot aesthetics')

# Team selection
highlight_options = standings.values[:, -1]  # order of last gameweek
highlights = st.sidebar.multiselect(label='Highlight teams',
                                    options=highlight_options)


# Highlight color picker
colors = []
default_colors = ['#FF0000', '#2EFDF7', '#3BEF1D', '#E64BF7']
for i, team in enumerate(highlights):
    if i < len(default_colors):
        value = default_colors[i]
    else:
        value = '#ffffff'
    color = st.sidebar.color_picker(label=team, value=value)
    colors.append(color)

highlight_colors = {i: c for i, c in zip(highlights, colors)}

# Reorder team name list to emphasize highlighted lines
for team in highlight_colors.keys():
    team_names.append(team_names.pop(team_names.index(team)))

# Titles
st.sidebar.markdown('---')
custom_title = st.sidebar.text_input('Custom Title', max_chars=40)

if highlights:
    subtitle = st.sidebar.checkbox(label='Subtitle', value=True)
else:
    subtitle = False

# Aspect ratio slider
st.sidebar.markdown('---')
aspect_ratio = st.sidebar.slider(label='Aspect ratio',
                                 min_value=0.4,
                                 max_value=0.8,
                                 value=0.60,
                                 step=0.05)

# Background color picker
st.sidebar.markdown('---')
facecolor = st.sidebar.color_picker(label='Background color',
                                    value='#111111')

# ---------- Draw plot ----------

fig, ax = plt.subplots(facecolor=facecolor,
                       figsize=(18, 18*aspect_ratio),
                       dpi=200)

for team_name in team_names:
    # Determine text color and fontweight
    color = highlight_colors.get(team_name, 'dimgrey')
    fontweight = 'bold' if color != 'dimgrey' else None

    indices = standings[standings == team_name].stack().index.tolist()
    coords = [(idx[1], idx[0]) for idx in indices]
    coords = [(int(coord[0]), coord[1]) for coord in coords]
    coords = sorted(coords, key=lambda x: x[0])

    # Plot patches
    for p1, p2 in zip(coords[:-1], coords[1:]):
        patch = get_patch(p1, p2, color=color)
        ax.add_patch(patch)

    # Plot dots
    for i, j in coords:
        ax.plot(i, j, 'o', color=color, alpha=0.3, zorder=1)

    # Team name at the end of the line
    ax.text(x=num_games,
            y=coords[-1][-1],
            s=team_name,
            va='center',
            color=color,
            fontweight=fontweight,
            fontname='Rockwell')

# Title

if custom_title:
    title = custom_title
else:
    league_title = league.title()
    season_title = str(season-1) + '/' + str(season)[2:]
    title = f'{league_title} {season_title} Standings by Gameweek'

fig.text(x=0.5,
         y=0.84,
         s=title,
         color='w',
         fontsize=22,
         fontweight='bold',
         fontname='Rockwell',
         ha='center',)

# Subtitle
if subtitle and highlight_colors:
    subtitle_teams, subtitle_colors = zip(*highlight_colors.items())
    subtitle_teams_hl = [f'<{team}>' for team in subtitle_teams]
    if len(subtitle_teams) == 1:
        subtitle_text = f"{subtitle_teams_hl[0]} highlighted."
    elif len(subtitle_teams) == 2:
        subtitle_text = f"Comparison between {' and '.join(subtitle_teams_hl)}."
    elif len(subtitle_teams) > 2:
        subtitle_text = f"Comparison between {', '.join(subtitle_teams_hl[:-2])}, {' and '.join(subtitle_teams_hl[-2:])}."

    highlight_textprops = [{'color': c,
                            'fontweight': 'bold'} for c in subtitle_colors]
    fig_text(x=0.5,
             y=0.82,
             s=subtitle_text,
             color='w',
             highlight_textprops=highlight_textprops,
             fontsize=18,
             ha='center',
             fontname='Rockwell')

# X-axis
ax.text(x=num_games/2,
        y=num_teams+0.5,
        s='Gameweek',
        fontsize=12,
        c='w',
        va='center',
        ha='center')

# Y-axis
ax.text(x=-1.25,
        y=num_teams/2,
        s='Position',
        rotation=90,
        fontsize=12,
        c='w',
        va='bottom',
        ha='center')

# Axis configuration
ax.set_axis_off()
ax.set_xlim(-2, num_games+2)
ax.set_ylim(-4, num_teams+1)
ax.invert_yaxis()

# Tick labels
x_labels = [ax.text(x=i-1,
                    y=num_teams-0.25,
                    s=i,
                    ha='center',
                    va='center',
                    c='w',
                    size=8) for i in range(1, num_games+1)]

y_labels = [ax.text(x=-0.5,
                    y=i,
                    s=i+1,
                    ha='center',
                    va='center',
                    c='w',
                    size=8) for i in range(num_teams)]


# ---------- Display plot ----------
st.pyplot(fig)


# ---------- Raw data ----------
def get_table_download_link(df):
    """
    (Adapted from https://discuss.streamlit.io/t/how-to-download-file-in-streamlit/1806)
    Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    # some strings <-> bytes conversions necessary here
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="raw_data.csv">*Download raw data as .csv*</a>'
    return href


st.markdown(get_table_download_link(standings), unsafe_allow_html=True)
