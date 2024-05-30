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
        return " + ".join(cats), new_num_logs/num_logs

    def get_probability_stl_blk(self, logs, stl=None, blk=None, total=0):
        cats = []
        if stl is True:
            cats.append('STL')
        if blk is True:
            cats.append('BLK')
        num_logs=len(logs)
        logs = logs[logs['STL'] + logs['BLK'] >= total]
        new_num_logs=len(logs)
        return " + ".join(cats), new_num_logs/num_logs
