from nba_api.stats.endpoints import playergamelog
import matplotlib.pyplot as plt
import time
import numpy as np
import pandas as pd
import requests
import re
import json
from nba_api.stats.endpoints import playercareerstats
from bs4 import BeautifulSoup
pd.set_option('display.max_columns', None)

player_career = playercareerstats.PlayerCareerStats(player_id='202681')
player_career_df = player_career.get_data_frames()[0]
seasons_played = player_career_df['SEASON_ID'].unique()
print(seasons_played.tolist())
# test = "https://www.nba.com/stats/teams/traditional?sort=PTS&dir=-1"
# test2 = "https://www.statmuse.com/nba/ask/haliburton-last-20-games"

# r = requests.get(url=test)
# soup = BeautifulSoup(r.content, 'html.parser')
# print(soup)

# # # data_points = soup.find_all('div', {'class': 'data-point'})
# # # print(data_points, 'done')
# # # data = [dp.text.strip() for dp in data_points]

# # # print(data)


# Initialize an empty DataFrame to store all game logs
all_seasons_logs_df = pd.DataFrame()

# List of seasons to loop through (update this list as needed)
seasons = ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']

# Fetch game logs for each season and add a 'SEASON' column
for season in seasons:
    player_logs = playergamelog.PlayerGameLog(
        player_id='202681', season=season)
    season_logs_df = player_logs.get_data_frames()[0]
    season_logs_df['SEASON'] = season
    all_seasons_logs_df = pd.concat(
        [all_seasons_logs_df, season_logs_df], ignore_index=True)

print(all_seasons_logs_df)

# Convert Game_Date to a datetime
all_seasons_logs_df['GAME_DATE'] = pd.to_datetime(
    all_seasons_logs_df['GAME_DATE'])
# Create Month_Year to faciliate Month/Date Analysis
all_seasons_logs_df['MONTH_YEAR'] = all_seasons_logs_df['GAME_DATE'].dt.to_period(
    'M')

# Aggregate game level data to yearly
yearly_stats = all_seasons_logs_df.groupby('YEAR').agg(
    {'FGM': 'sum',     'FGA': 'sum',     'FG3M': 'sum',     'FG3A': 'sum',     'FTM': 'sum',     'FTA': 'sum', }).reset_index()
# This takes the field goals made and attempted to calculate field goal percent
yearly_stats['FG_PCT'] = yearly_stats['FGM'] / yearly_stats['FGA']
yearly_stats['FG3_PCT'] = yearly_stats['FG3M'] / yearly_stats['FG3A']
yearly_stats['FT_PCT'] = yearly_stats['FTM'] / yearly_stats['FTA']
# yearly_stats['GAMES'] = yearly_stats.groupby(
#     'YEAR')['Game_ID'].count().values

print(yearly_stats)
