from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, get_players_from_csv
from get_statistics import get_player_career_stats
pd.set_option('display.max_columns', None)

nba_players = get_players_from_csv('nba_players.csv')
print(get_player_career_stats(nba_players('lebron james')[0]['PERSON_ID']))
