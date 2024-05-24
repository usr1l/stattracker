from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, NBA
from get_statistics import get_player_career_stats
pd.set_option('display.max_columns', None)


CURRENT_SEASON_PLAYERS = NBA('nba_players.csv')

tatum = CURRENT_SEASON_PLAYERS.get_player_by_name('jayson tatum')
print(tatum)

print(CURRENT_SEASON_PLAYERS.get_players_by_team('celtics'))
# print(get_player_career_stats(nba_players('lebron james')[0]['PERSON_ID']))
