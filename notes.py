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


# Rk,GAME_DATE,AGE,MATCHUP,WL,GS,MP,FG,FGA,FG%,3P,3PA,3P%,FT,FTA,FT%,ORB,DRB,TRB,AST,STL,BLK,TOV,PF,PTS,GmSc
# 1,2024-05-14,22-113,IND @ CON,L (-21),1,32:27,5,15,.333,4,11,.364,6,6,1.000,0,0,0,3,2,0,10,4,20,4.0
# 2,2024-05-16,22-115,IND vs. NYL,L (-36),1,30:08,2,8,.250,1,7,.143,4,4,1.000,0,7,7,6,0,1,3,5,9,6.2
# 3,2024-05-18,22-117,IND @ NYL,L (-11),1,34:27,9,17,.529,4,10,.400,0,0,,2,4,6,8,1,0,8,3,22,13.7
# 4,2024-05-20,22-119,IND vs. CON,L (-4),1,27:24,5,11,.455,3,7,.429,4,4,1.000,0,3,3,5,0,2,5,5,17,10.1
# 5,2024-05-22,22-121,IND @ SEA,L (-2),1,32:56,6,16,.375,2,8,.250,7,9,.778,1,6,7,7,0,2,3,0,21,17.2
# 6,2024-05-24,22-123,IND @ LAS,W (+5),1,36:51,4,14,.286,2,9,.222,1,2,.500,1,9,10,8,4,1,2,2,11,13.3
# 7,2024-05-25,22-124,IND @ LVA,L (-19),1,28:31,2,8,.250,2,5,.400,2,2,1.000,0,5,5,7,1,0,6,2,8,3.8
# 8,2024-05-28,22-127,IND vs. LAS,L (-6),1,34:05,7,16,.438,3,10,.300,13,15,.867,0,5,5,6,3,3,7,5,30,22.6
# 9,2024-05-30,22-129,IND vs. SEA,L (-15),1,39:56,6,17,.353,3,8,.375,5,5,1.000,1,2,3,9,0,1,7,2,20,11.0
