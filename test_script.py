from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, NBA
from app import nba_statistics, nba_analysis
pd.set_option('display.max_columns', None)


# current_season_players = NBA('nba_players.csv')
# statistics = NBAStats()

# tatum = current_season_players.get_player_by_name('jayson tatum')
# celtics_players = current_season_players.get_players_by_team('celtics')
# print(get_player_career_stats(tatum[0]))
# print(list(celtics_players.values()))
# print(get_team_players_career_stats(list(celtics_players.values())))
# print(statistics.get_player_last_games(tatum[0], away=True, opponent_team='MIL'))
# print(current_season_players.get_id_by_name('lebron james'))
# print(statistics.get_player_career_stats(
#     current_season_players.get_id_by_player_name('lebron james')))
# print(statistics.get_last_n_games_against_team(current_season_players.get_id_by_player_name(
#     'lebron james'), current_season_players.get_team_abbreviation('celtics'), 10))
# print(tatum[0])
# id = tatum[0]
# print(current_season_players.get_id_by_team_name('heat'))
# print(statistics.get_player_games_last_n_seasons_against_team(s
# print(statistics.get_player_games_last_n_seasons_against_team(
# tatum[0], matchup=current_season_players.get_team_abbreviation_by_name('heat'), away=True))
# print(statistics.get_player_games_last_n_seasons_against_team(
#   current_season_players.get_player_by_name('pascal siakam'),
#   matchup=current_season_players.get_team_abbreviation_by_name('nuggets'),
#   num_games=30,
#   away=True,
#   home=False))

# GAMES = statistics.get_player_games_last_n_seasons_against_team(
#     tatum[0], matchup=current_season_players.get_team_abbreviation_by_name('heat'), num_games=90)
# charts.plot_game_logs(GAMES)
log = pd.read_csv('players_csv/celtics/tatum.csv')
# print(log)

print(nba_analysis.get_probability_table(log, cats=['PTS']))
# print(log)
