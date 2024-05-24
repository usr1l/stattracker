import pandas as pd
from nba_api.stats.endpoints import playercareerstats


def get_player_career_stats(player_id):
    player_stats = playercareerstats.PlayerCareerStats(
        player_id=player_id)

    # gets alll seasons, pick the first for current season
    # print(player_stats.get_data_frames())
    player_stats_df = player_stats.get_data_frames()[0]
    return player_stats_df


def get_team_players_career_stats(player_ids):
    players_df = []
    for player_id in player_ids:
        player_stats = playercareerstats.PlayerCareerStats(
            player_id=player_id)

        # gets alll seasons, pick the first for current season
        # print(player_stats.get_data_frames())
        player_stats_df = player_stats.get_data_frames()[0]
        players_df.append(player_stats_df)

    return players_df
