from nba_api.stats.endpoints import commonallplayers
import pandas as pd


def csv_file_check(func):
    def wrapper(self, *args, **kwargs):
        if not self.csv_file:
            return "No CSV file found"
        return func(self, *args, **kwargs)
    return wrapper


class NBAPlayers:
    def __init__(self, csv_file):
        self.csv_file = csv_file or None
        # Read the CSV file into a DataFrame
        self.df = pd.read_csv(csv_file) if csv_file else None

    def change_csv_file(self, csv_file):
        self.csv_file = csv_file
        self.df = pd.read_csv(csv_file)

    def get_nba_players_csv(self):
        players = commonallplayers.CommonAllPlayers(is_only_current_season=1)
        players_df = players.get_data_frames()[0]
        players_df[['PERSON_ID', 'DISPLAY_FIRST_LAST']].to_csv(
            'nba_players.csv', index=False)

    def find_player_by_id(self, player_name):

        # Search for the player name
        result = self.df[self.df['DISPLAY_FIRST_LAST'].str.contains(
            player_name, case=False, na=False)]

        # Check if the result is empty
        if result.empty:
            return f"No player found with the name: {player_name}"
        else:
            return result[['PERSON_ID', 'DISPLAY_FIRST_LAST']].to_dict(orient='records')
