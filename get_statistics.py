import pandas as pd
from nba_api.stats.endpoints import playercareerstats, playergamelog, TeamGameLogs, commonplayerinfo
from datetime import datetime

CURRENT_SEASON = '2023-24'

class NBAStats:
    def get_player_career_stats(self, player_id):
        player_stats = playercareerstats.PlayerCareerStats(
            player_id=player_id)

        # gets all seasons, pick the first for current season
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

    def get_player_seasons(self, player_id):
        player_info = commonplayerinfo.CommonPlayerInfo(
            player_id=player_id).get_data_frames()[0]
        from_year = player_info['FROM_YEAR'].values[0]
        to_year = player_info['TO_YEAR'].values[0]
        return range(from_year, to_year + 1)

    def get_games_based_on_stats(
            self,
            player_id,
            matchup="",
            seasons=['2023-24', '2022-23', '2021-22', '2020-21'],
            num_games=10,
            home=False,
            away=False,
            assists=None,
            rebounds=None,
            points=None,
            steals=None,
            blocks=None,
            triple_double=None,
            double_double=None
            ):

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

                logs = pd.concat([logs, gamelog_playoffs, gamelog_regular])
            except KeyError as e:
                print(f"Error: {e}. Skipping season {season}.")
        # print(logs.columns)
        # Filter by assists, rebounds, points, steals, blocks, triple-double, and double-double
        if assists is not None:
            logs = logs[logs['AST'].ge(assists)]
        if rebounds is not None:
            logs = logs[logs['REB'].ge(rebounds)]
        if points is not None:
            logs = logs[logs['PTS'].ge(points)]
        if steals is not None:
            logs = logs[logs['STL'].ge(steals)]
        if blocks is not None:
            logs = logs[logs['BLK'].ge(blocks)]
        if triple_double is not None:
            logs = logs[logs['PTS'].ge(10) & logs['REB'].ge(10) & logs['AST'].ge(10)]
        if double_double is not None:
            logs = logs[((logs['PTS'].ge(10) & logs['REB'].ge(10)) |
                         (logs['PTS'].ge(10) & logs['AST'].ge(10)) |
                         (logs['REB'].ge(10) & logs['AST'].ge(10)))]

        # Sort by date
        logs = logs.sort_values(by='GAME_DATE', ascending=False)

        if num_games:
            return logs.head(num_games)
        return logs

    # opponent team is abbrev
    def get_player_last_games(self, player_id, num_games=10, home=False, away=False, opponent_team=''):
        opponent_team = " " + opponent_team if opponent_team else ""
        gamelog_regular = playergamelog.PlayerGameLog(
            player_id=player_id, season=CURRENT_SEASON, season_type_all_star='Regular Season').get_data_frames()[0]
        gamelog_playoffs = playergamelog.PlayerGameLog(
            player_id=player_id, season=CURRENT_SEASON, season_type_all_star='Playoffs').get_data_frames()[0]
        logs = pd.concat([gamelog_playoffs, gamelog_regular])
        if home == True:
            return logs[logs['MATCHUP'].str.contains('vs.' + opponent_team)].head(num_games)
        if away == True:
            return logs[logs['MATCHUP'].str.contains('@' + opponent_team)].head(num_games)
        return logs.head(num_games)


    def get_player_games_last_n_seasons_against_team(self, player_id, matchup="", seasons=['2023-24', '2022-23', '2021-22', '2020-21'], num_games=10, home=False, away=False):

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

                logs = pd.concat([logs, gamelog_playoffs, gamelog_regular])
            except KeyError as e:
                print(f"Error: {e}. Skipping season {season}.")
        # print(logs.columns)
        if num_games:
            return logs.head(num_games)
        return logs


    # def get_team_games(self, team_id, num_games=10):
