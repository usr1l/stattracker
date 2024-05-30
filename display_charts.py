import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

class DisplayCharts:
    def plot_game_logs_linegraph(self, logs, cats=['FG3M', 'PTS', 'REB', 'AST', 'STL', 'BLK']):
        # Convert the GAME_DATE column to datetime format
        logs['GAME_DATE'] = pd.to_datetime(logs['GAME_DATE'])

        # Plot the PTS column against the GAME_DATE column
        for cat in cats:
            plt.plot(logs['GAME_DATE'], logs[cat.upper()], label=cat)

        # Set the title and labels
        plt.title('Stats Over Time')
        plt.xlabel('Date')
        plt.ylabel('Number')
        plt.legend(cats, loc='best')
        plt.show()

    def plot_game_logs_barchart(self, logs, cats=['FG3M', 'PTS', 'REB', 'AST', 'STL', 'BLK']):
        # Convert the GAME_DATE column to datetime format
        logs['GAME_DATE'] = pd.to_datetime(logs['GAME_DATE'])

        # Create a figure and axis
        fig, ax = plt.subplots()

        # Set the width of each bar
        width = 0.15

        # Set the x-axis positions for each category
        x_pos = np.arange(len(logs['GAME_DATE']))

        # Plot the data as a bar chart with each category side by side
        for i, cat in enumerate(cats):
            ax.bar(x_pos + i * width, logs[cat.upper()], width, label=cat)

        # Set the x-axis tick labels
        ax.set_xticks(x_pos + len(cats) / 2 * width)

        # Set the title and labels
        ax.set_title('Stats Over Time')
        ax.set_xlabel('Date')
        ax.set_ylabel('Number')
        ax.legend(cats, loc='best')
        plt.show()
