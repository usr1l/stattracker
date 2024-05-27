from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, NBA
from get_statistics import NBAStats
from display_charts import DisplayCharts
pd.set_option('display.max_columns', None)


current_season_players = NBA('nba_players.csv')
statistics = NBAStats()
charts = DisplayCharts()
