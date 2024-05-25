import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt


class DisplayCharts:
    def plot_game_logs(self, logs):
        categories = ['MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA',
                      'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF',
                      'PTS', 'PLUS_MINUS']

        # create a figure and axis object
        fig, ax = plt.subplots(
            len(categories), 1, figsize=(10, 6*len(categories)))

        # loop through each category and plot a line chart
        for i, category in enumerate(categories):
            ax[i].plot(logs['GAME_DATE'], logs[category], marker='o')
            ax[i].set_title(category)
            ax[i].set_xlabel('Date')
            ax[i].set_ylabel(category)

        # show the plot
        plt.tight_layout()
        plt.show()
