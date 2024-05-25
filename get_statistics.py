import pandas as pd
from nba_api.stats.endpoints import playercareerstats, playergamelog, TeamGameLogs, commonplayerinfo
from datetime import datetime


class NBAStats:
    def get_player_career_stats(self, player_id):
        player_stats = playercareerstats.PlayerCareerStats(
            player_id=player_id)

        # gets alll seasons, pick the first for current season
        # print(player_stats.get_data_frames())
        player_stats_df = player_stats.get_data_frames()[0]
        return player_stats_df

    def get_team_players_career_stats(self, player_ids):
        stats_df = []
        for player_id in player_ids:
            player_stats = playercareerstats.PlayerCareerStats(
                player_id=player_id)

            # gets alll seasons, pick the first for current season
            # print(player_stats.get_data_frames())
            player_stats_df = player_stats.get_data_frames()[0]
            stats_df.append(player_stats_df)

        return stats_df

    # opponent team is abbrev
    def get_player_last_games(self, player_id, num_games=10, home=False, away=False, opponent_team=''):
        opponent_team = " " + opponent_team if opponent_team else ""
        gamelog_regular = playergamelog.PlayerGameLog(
            player_id=player_id, season='2023-24', season_type_all_star='Regular Season').get_data_frames()[0]
        gamelog_playoffs = playergamelog.PlayerGameLog(
            player_id=player_id, season='2023-24', season_type_all_star='Playoffs').get_data_frames()[0]
        logs = pd.concat([gamelog_playoffs, gamelog_regular])
        if home == True:
            return logs[logs['MATCHUP'].str.contains('vs.' + opponent_team)].head(num_games)
        if away == True:
            return logs[logs['MATCHUP'].str.contains('@' + opponent_team)].head(num_games)
        return logs.head(num_games)

    def get_player_seasons(self, player_id):
        player_info = commonplayerinfo.CommonPlayerInfo(
            player_id=player_id).get_data_frames()[0]
        from_year = player_info['FROM_YEAR'].values[0]
        to_year = player_info['TO_YEAR'].values[0]
        return range(from_year, to_year + 1)

    def get_player_games_last_n_seasons_against_team(self, player_id, seasons=['2023-24', '2022-23', '2021-22', '2020-21'], matchup="", num_games=10, home=False, away=False):

        if home:
            matchup = "vs. " + matchup
        elif away:
            matchup = "@ " + matchup
        else:
            matchup = matchup

        logs = pd.DataFrame()
        for season in seasons:
            try:
                gamelog_regular = playergamelog.PlayerGameLog(
                    player_id=player_id, season=season, season_type_all_star='Regular Season').get_data_frames()[0]
                gamelog_playoffs = playergamelog.PlayerGameLog(
                    player_id=player_id, season=season, season_type_all_star='Playoffs').get_data_frames()[0]
                if matchup:
                    if not gamelog_playoffs.empty:
                        gamelog_playoffs = gamelog_playoffs[gamelog_playoffs['MATCHUP'].str.contains(
                            matchup, case=False, na=False)]
                    if not gamelog_regular.empty:
                        gamelog_regular = gamelog_regular[gamelog_regular['MATCHUP'].str.contains(
                            matchup, case=False, na=False)]

                    # print(gamelog_playoffs, gamelog_regular)
                    if not gamelog_playoffs.empty:
                        if not gamelog_regular.empty:
                            logs = pd.concat(
                                [logs, gamelog_playoffs, gamelog_regular])
                        else:
                            logs = pd.concat([logs, gamelog_playoffs])
                    elif not gamelog_regular.empty:
                        logs = pd.concat([logs, gamelog_regular])
            except KeyError as e:
                print(f"Error: {e}. Skipping season {season}.")
        # print(logs.columns)
        if num_games:
            return logs.head(num_games)
        return logs
