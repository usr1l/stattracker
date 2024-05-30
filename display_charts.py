import matplotlib as mpl
mpl.use('TkAgg')
import matplotlib.pyplot as plt
import pandas as pd

class DisplayCharts:
    def plot_game_logs(self, logs, cats=['FG3M', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF']):
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

        # # create a table with the data_frame
        # table_data = logs[cats].values
        # table_col = cats
        # table_rows = logs['GAME_DATE'].dt.strftime('%Y-%m-%d')

        # # Create the table
        # plt.table(cellText=table_data, rowLabels=table_rows, colLabels=table_col,
        #           loc='bottom', bbox=[0, -0.5, 1, 0.5])

        # Show the plot
        plt.show()
