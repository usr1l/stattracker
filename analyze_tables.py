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

    def get_probability_stl_blk(self, logs, stl=None, blk=None, total=0):
        cats = []
        if stl is True:
            cats.append('STL')
        if blk is True:
            cats.append('BLK')
        num_logs=len(logs)
        logs = logs[logs['STL'] + logs['BLK'] >= total]
        new_num_logs=len(logs)
        return " + ".join(cats), f'{new_num_logs/num_logs * 100} %'

    def get_combination_probability(self, log1, log2, player1, player2, log3=None, player3=None):
        # for tracking which dates fit for all
        dates = {}
        # for tracking how many they played in together
        matches = {}
        count = 0
        total = 0
        num_games = len(log1)
        for index, row in log1.iterrows():
            game_id = row['Game_ID']
            if game_id not in matches:
                matches[game_id] = 1
            else:
                matches[game_id] += 1
            if 'total' in player1 and isinstance(player1['total'], int):
                if row['AST'] + row['REB'] + row['PTS'] >= player1['total']:
                    game_id = row['Game_ID']
                    if game_id not in dates:
                        dates[game_id] = 1
                    else:
                        dates[game_id] += 1
                continue


            ast1 = player1['ast']
            reb1 = player1['reb']
            pts1 = player1['pts']
            if row['AST'] >= ast1 and row['REB'] >= reb1 and row['PTS'] >= pts1:
                # print(game_id)
                if game_id not in dates:
                    dates[game_id] = 1
                else:
                    dates[game_id] += 1


        for index, row in log2.iterrows():
            game_id = row['Game_ID']
            if game_id not in matches:
                matches[game_id] = 1
            else:
                matches[game_id] += 1
            if 'total' in player2 and isinstance(player2['total'], int):
                if row['AST'] + row['REB'] + row['PTS'] >= player2['total']:
                    game_id = row['Game_ID']
                    if game_id not in dates:
                        dates[game_id] = 1
                    else:
                        dates[game_id] += 1
                continue

            ast2 = player2['ast']
            reb2 = player2['reb']
            pts2 = player2['pts']
            if row['AST'] >= ast2 and row['REB'] >= reb2 and row['PTS'] >= pts2:
                if game_id not in dates:
                    dates[game_id] = 1
                else:
                    dates[game_id] += 1


        if player3:
            for index, row in log3.iterrows():
                game_id = row['Game_ID']
                if game_id not in matches:
                    matches[game_id] = 1
                else:
                    matches[game_id] += 1
                if 'total' in player3 and isinstance(player3['total'], int):
                    if row['AST'] + row['REB'] + row['PTS'] >= player3['total']:
                        game_id = row['Game_ID']
                        if game_id not in dates:
                            dates[game_id] = 1
                        else:
                            dates[game_id] += 1
                    continue
                ast3 = player3['ast']
                reb3 = player3['reb']
                pts3 = player3['pts']

                if row['AST'] >= ast3 and row['REB'] >= reb3 and row['PTS'] >= pts3:
                    if game_id not in dates:
                        dates[game_id] = 1
                    else:
                        dates[game_id] += 1
        if player3:
            for key in dates:
                if dates[key] == 3:
                    count+=1
            for key in matches:
                if matches[key] == 3:
                    total+=1

            return f'{count}/{total} = {count/total * 100}%'


        for key in dates:
            if dates[key] == 2:
                count+=1
        for key in matches:
            if matches[key] == 2:
                total+=1

        if total == 0:
            total+=1

        return f'{count}/{total} = {count/total * 100}%'

    def get_cat_averages(self, logs, cats=['FG3M', 'PTS', 'REB', 'AST', 'STL', 'BLK']):
        averages = {}
        for cat in cats:
            averages[cat] = logs[cat].mean()
        return averages

    def get_combined_cats(self):
        pass
