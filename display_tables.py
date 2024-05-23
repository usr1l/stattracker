import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate
from get_statistics import get_player_career_stats

print(tabulate(get_player_career_stats(2544).head(),
      headers='keys', tablefmt='pretty'))
# def create_table(df):
