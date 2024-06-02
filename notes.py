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


# Rk,GAME_DATE,AGE,MATCHUP,WL,GS,MP,FG,FGA,FG%,FG3M,3PA,3P%,FT,FTA,FT%,ORB,DRB,TRB,AST,STL,BLK,TOV,PF,PTS,GmSc
# SEASON_ID,Player_ID,Game_ID,GAME_DATE,MATCHUP,WL,MIN,FGM,FGA,FG_PCT,FG3M,FG3A,FG3_PCT,FTM,FTA,FT_PCT,OREB,DREB,REB,AST,STL,BLK,TOV,PF,PTS,PLUS_MINUS,VIDEO_AVAILABLE
