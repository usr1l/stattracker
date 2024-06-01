import pandas as pd

class Analysis():
    def get_cats_probability(
            self,
            logs,
            ast=None,
            reb=None,
            pts=None,
            stl=None,
            blk=None,
            pf=None,
            threes_made=None,
            triple_double=None,
            double_double=None,
            win=None
            ):

        cats = []
        num_logs = len(logs)
        if ast is not None:
            logs = logs[logs['AST'].ge(ast)]
            cats.append(f'{ast} AST')
        if reb is not None:
            logs = logs[logs['REB'].ge(reb)]
            cats.append(f'{reb} REB')
        if pts is not None:
            logs = logs[logs['PTS'].ge(pts)]
            cats.append(f'{pts} PTS')
        if stl is not None:
            logs = logs[logs['STL'].ge(stl)]
            cats.append(f'{stl} STL')
        if blk is not None:
            logs = logs[logs['BLK'].ge(blk)]
            cats.append(f'{blk} BLK')
        if pf is not None:
            logs = logs[logs['PF'].ge(pf)]
            cats.append(f'{pf} PF')
        if threes_made is not None:
            logs = logs[logs['FG3M'].ge(threes_made)]
            cats.append(f'{threes_made} 3PM')
        if triple_double is True:
            logs = logs[logs['PTS'].ge(10) & logs['REB'].ge(10) & logs['AST'].ge(10)]
            cats.append('TD')
        if double_double is True:
            logs = logs[((logs['PTS'].ge(10) & logs['REB'].ge(10)) |
                         (logs['PTS'].ge(10) & logs['AST'].ge(10)) |
                         (logs['REB'].ge(10) & logs['AST'].ge(10)))]
            cats.append('DD')
        if win is not None:
            if win is True:
                logs = logs[logs['WL'] == 'W']
            if win is False:
                logs = logs[logs['WL'] == 'L']
            cats.append('W' if win is True else 'L')

        new_num_logs=len(logs)

        return " + ".join(cats), new_num_logs, num_logs, new_num_logs/num_logs


    def get_probability_pts_reb_ast(
            self,
            logs,
            ast=None,
            reb=None,
            pts=None,
            total=0
            ):
        cats = []
        if ast is True:
            cats.append('AST')
        if reb is True:
            cats.append('REB')
        if pts is True:
            cats.append('PTS')
        num_logs = len(logs)
        logs = logs[logs['PTS'] + logs['REB'] + logs['AST'] >= total]
        new_num_logs = len(logs)
        return " + ".join(cats), f'{new_num_logs/num_logs * 100} %'


    def get_probability_stl_blk(
            self,
            logs,
            stl=None,
            blk=None,
            total=0
            ):
        """
        """
        cats = []
        if stl is True:
            cats.append('STL')
        if blk is True:
            cats.append('BLK')
        num_logs=len(logs)
        logs = logs[logs['STL'] + logs['BLK'] >= total]
        new_num_logs=len(logs)
        return " + ".join(cats), f'{new_num_logs/num_logs * 100} %'


    def get_combination_probability(self, logs=[], players=[]):
        """
        logs: list of pandas.DataFrame
        players: list of dict

        use 'total_pra' key for points, rebounds, assists category combination totals, total must be a number to work
        use 'total_sb' for steals, blocks totals, must be number

        dates: {} which dates match for players achieving their goals
        matches: {} which games match for players
        """
        if len(players) != len(logs) or not players or not logs:
            return 'Players and logs mismatch, check your inputs'
        dates = {}
        matches = {}
        count = 0
        total = 0
        num_players = len(players)

        for i in range(num_players):
            player = players[i]
            log = logs[i]
            for index, row in log.iterrows():
                game_id = row['Game_ID']
                if game_id not in matches:
                    matches[game_id] = 1
                else:
                    matches[game_id] += 1
                # points, rebounds, assists total
                if 'total_pra' in player and isinstance(player['total_pra'], int):
                    if row['AST'] + row['REB'] + row['PTS'] >= player['total_pra']:
                        game_id = row['Game_ID']
                        if game_id not in dates:
                            dates[game_id] = 1
                        else:
                            dates[game_id] += 1
                # steals and blocks total
                elif 'total_sb' in player and isinstance(player['total_sb'], int):
                    if row['STL'] + row['BLK'] >= player['total_sb']:
                        game_id = row['Game_ID']
                        if game_id not in dates:
                            dates[game_id] = 1
                        else:
                            dates[game_id] += 1
                else:
                    ast = player['ast']
                    reb = player['reb']
                    pts = player['pts']
                    stl = player['stl']
                    blk = player['blk']
                    if row['AST'] >= ast and row['REB'] >= reb and row['PTS'] >= pts and row['STL'] >= stl and row['BLK'] >= blk:
                        if game_id not in dates:
                            dates[game_id] = 1
                        else:
                            dates[game_id] += 1

        for key in dates:
            if dates[key] == num_players:
                count+=1
        for key in matches:
            if matches[key] == num_players:
                total+=1

        if total == 0:
            total+=1

        return f'Times Achieved / Total Games, {count}/{total} = {count/(total if total > 0 else 1) * 100} %'


    def get_cat_averages(self, logs, cats=['FG3M', 'PTS', 'REB', 'AST', 'STL', 'BLK']):
        averages = {}
        for cat in cats:
            averages[cat] = logs[cat].mean()
        return averages


    def get_combined_cats(self):
        pass
