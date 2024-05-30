from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, NBA
from get_statistics import NBAStats
from analyze_tables import Analysis
from display_charts import DisplayCharts
pd.set_option('display.max_columns', None)


CURRENT_SEASON = '2023-24'
LAST_FIVE_SEASONS = ['2023-24', '2022-23', '2021-22', '2020-21', '2019-20']

nba_players = NBA('nba_players.csv')
nba_statistics = NBAStats()
nba_charts = DisplayCharts()
nba_analysis = Analysis()
