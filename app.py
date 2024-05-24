from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, NBA
from get_statistics import get_player_career_stats, get_team_players_career_stats, get_player_last_games, get_player_seasons, get_last_n_games_against_team
pd.set_option('display.max_columns', None)


CURRENT_SEASON_PLAYERS = NBA('nba_players.csv')

tatum = CURRENT_SEASON_PLAYERS.get_player_by_name('jayson tatum')

celtics_players = CURRENT_SEASON_PLAYERS.get_players_by_team('celtics')

# print(get_player_career_stats(tatum[0]))
# print(list(celtics_players.values()))
# print(get_team_players_career_stats(list(celtics_players.values())))
# print(get_player_last_games(tatum[0], 20))
# print(CURRENT_SEASON_PLAYERS.get_id_by_name('lebron james'))
print(get_last_n_games_against_team(CURRENT_SEASON_PLAYERS.get_id_by_player_name(
    'lebron james'), CURRENT_SEASON_PLAYERS.get_team_abbreviation('celtics'), 10))
# print(get_player_career_stats(nba_players('lebron james')[0]['PERSON_ID']))
