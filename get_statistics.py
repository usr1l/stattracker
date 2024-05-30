import pandas as pd
from nba_api.stats.endpoints import playercareerstats, playergamelog, TeamGameLogs, commonplayerinfo
from datetime import datetime

CURRENT_SEASON = '2023-24'
LAST_FIVE_SEASONS = ['2023-24', '2022-23', '2021-22', '2020-21', '2019-20']

class NBAStats:
    def sort_logs_by_date(self, logs):
        logs['GAME_DATE'] = pd.to_datetime(logs['GAME_DATE'], format='%b %d, %Y')
        logs = logs.sort_values(by='GAME_DATE', ascending=False)
        return logs

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

    def get_player_statistics(
            self,
            player_id,
            matchup="",
            seasons=LAST_FIVE_SEASONS,
            num_games=10,
            home=False,
            away=False,
            assists=None,
            rebounds=None,
            points=None,
            steals=None,
            blocks=None,
            personal_fouls=None,
            threes_made=None,
            triple_double=None,
            double_double=None,
            win=None
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

                # Concatenate the DataFrames, excluding any empty or all-NA columns
                logs = pd.concat([logs.loc[:, logs.notna().any()],
                           gamelog_playoffs.loc[:, gamelog_playoffs.notna().any()],
                           gamelog_regular.loc[:, gamelog_regular.notna().any()]],
                          ignore_index=True)
                logs = self.sort_logs_by_date(logs)

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
        if personal_fouls is not None:
            logs = logs[logs['PF'].ge(personal_fouls)]
        if threes_made is not None:
            logs = logs[logs['FG3M'].ge(threes_made)]
        if triple_double is True:
            logs = logs[logs['PTS'].ge(10) & logs['REB'].ge(10) & logs['AST'].ge(10)]
        if double_double is True:
            logs = logs[((logs['PTS'].ge(10) & logs['REB'].ge(10)) |
                         (logs['PTS'].ge(10) & logs['AST'].ge(10)) |
                         (logs['REB'].ge(10) & logs['AST'].ge(10)))]
        if win is not None:
            if win is True:
                logs = logs[logs['WL'] == 'W']
            if win is False:
                logs = logs[logs['WL'] == 'L']

        if num_games:
            return logs.head(num_games)
        return logs
