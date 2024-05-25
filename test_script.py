from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, NBA
from app import STATISTICS, CURRENT_SEASON_PLAYERS, CHARTS
pd.set_option('display.max_columns', None)


# CURRENT_SEASON_PLAYERS = NBA('nba_players.csv')
# STATISTICS = NBAStats()

tatum = CURRENT_SEASON_PLAYERS.get_player_by_name('jayson tatum')
# celtics_players = CURRENT_SEASON_PLAYERS.get_players_by_team('celtics')
# print(get_player_career_stats(tatum[0]))
# print(list(celtics_players.values()))
# print(get_team_players_career_stats(list(celtics_players.values())))
print(STATISTICS.get_player_last_games(tatum[0], away=True, opponent_team='MIL'))
# print(CURRENT_SEASON_PLAYERS.get_id_by_name('lebron james'))
# print(STATISTICS.get_player_career_stats(
#     CURRENT_SEASON_PLAYERS.get_id_by_player_name('lebron james')))
# print(STATISTICS.get_last_n_games_against_team(CURRENT_SEASON_PLAYERS.get_id_by_player_name(
#     'lebron james'), CURRENT_SEASON_PLAYERS.get_team_abbreviation('celtics'), 10))
# print(tatum[0])
# id = tatum[0]
# print(CURRENT_SEASON_PLAYERS.get_id_by_team_name('heat'))
# print(STATISTICS.get_player_games_last_n_seasons_against_team(s
# STATISTICS.get_player_games_last_n_seasons_against_team(
# tatum[0], matchup=CURRENT_SEASON_PLAYERS.get_team_abbreviation_by_name('heat'))
# GAMES = STATISTICS.get_player_games_last_n_seasons_against_team(
#     tatum[0], matchup=CURRENT_SEASON_PLAYERS.get_team_abbreviation_by_name('heat'), num_games=90)
# CHARTS.plot_game_logs(GAMES)
