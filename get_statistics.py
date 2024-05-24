import pandas as pd
from nba_api.stats.endpoints import playercareerstats


def get_player_career_stats(player_ids):
    if isinstance(player_ids, int):
        player_stats = playercareerstats.PlayerCareerStats(player_id=player_ids)

        # gets alll seasons, pick the first for current season
        # print(player_stats.get_data_frames())
        player_stats_df = player_stats.get_data_frames()[0]
        return player_stats_df

    elif isinstance(player_ids, []):
        player_stats = []
        for player_id in player_ids:
            player_stats.append(playercareerstats.PlayerCareerStats(player_id=player_id).get_data_frames()[0])
