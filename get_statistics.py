import pandas as pd
from nba_api.stats.endpoints import playercareerstats


def get_player_career_stats(player_id):
    player_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
    player_stats_df = player_stats.get_data_frames()[0]
    return player_stats_df
