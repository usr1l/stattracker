# for fetching gamelogs
# gamelog_regular = playergamelog.PlayerGameLog(
#     player_id=player_id, season=season, season_type_all_star='Regular Season').get_data_frames()[0]
# gamelog_playoffs = playergamelog.PlayerGameLog(
#     player_id=player_id, season=season, season_type_all_star='Playoffs').get_data_frames()[0]

# get columns
# print(gamelog_regular.columns)

# get row
# print(gamelog_regular['MATCHUP'])
# print(gamelog_regular.loc[0])

# get rows that contain a specific string
# print(gamelog_regular[gamelog_regular['MATCHUP'].str.contains(
#     matchup, case=False, na=False)])

# get rows that contain a specific string and print the columns
# print(gamelog_regular[gamelog_regular['MATCHUP'].str.contains(
#     matchup, case=False, na=False)])
# print(gamelog_regular.columns)
