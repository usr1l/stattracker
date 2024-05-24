import pandas as pd
from nba_api.stats.endpoints import playercareerstats, playergamelog, TeamGameLogs


def get_player_career_stats(player_id):
    player_stats = playercareerstats.PlayerCareerStats(
        player_id=player_id)

    # gets alll seasons, pick the first for current season
    # print(player_stats.get_data_frames())
    player_stats_df = player_stats.get_data_frames()[0]
    return player_stats_df


def get_team_players_career_stats(player_ids):
    stats_df = []
    for player_id in player_ids:
        player_stats = playercareerstats.PlayerCareerStats(
            player_id=player_id)

        # gets alll seasons, pick the first for current season
        # print(player_stats.get_data_frames())
        player_stats_df = player_stats.get_data_frames()[0]
        stats_df.append(player_stats_df)

    return stats_df


def get_player_last_games(player_id, num_games):
    gamelog_regular = playergamelog.PlayerGameLog(
        player_id=player_id, season='2023-24', season_type_all_star='Regular Season').get_data_frames()[0]
    gamelog_playoffs = playergamelog.PlayerGameLog(
        player_id=player_id, season='2023-24', season_type_all_star='Playoffs').get_data_frames()[0]
    logs = pd.concat([gamelog_playoffs, gamelog_regular])
    return logs.head(num_games)


# def get_player_season_stats(player_id):
#     player_stats = playercareerstats.PlayerCareerStats(
#         player_id=player_id)

#     # gets alll seasons, pick the first for current season
#     # print(player_stats.get_data_frames())
#     player_stats_df = player_stats.get_data_frames()[1]
#     return player_stats_df
