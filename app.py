import pandas as pd
from get_players import NBA
from get_statistics import NBAStats
from analyze_tables import Analysis
from display_charts import DisplayCharts
pd.set_option('display.max_columns', None)


# CURRENT_SEASON = '2023-24'
# PREVIOUS_SEASONS = ['2023-24', '2022-23', '2021-22', '2020-21', '2019-20']

nba_players = NBA('players_csv/nba_players.csv')
nba_statistics = NBAStats()
nba_charts = DisplayCharts()
nba_analysis = Analysis()
