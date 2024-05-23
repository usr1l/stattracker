from nba_api.stats.endpoints import commonallplayers
import pandas as pd


def get_nba_players_csv():
    players = commonallplayers.CommonAllPlayers(is_only_current_season=1)
    players_df = players.get_data_frames()[0]
    players_df[['PERSON_ID', 'DISPLAY_FIRST_LAST']].to_csv(
        'nba_players.csv', index=False)


def find_player_by_id(player_name, csv_file='nba_players.csv'):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_file)

    # Search for the player name
    result = df[df['DISPLAY_FIRST_LAST'].str.contains(
        player_name, case=False, na=False)]

    # Check if the result is empty
    if result.empty:
        return f"No player found with the name: {player_name}"
    else:
        return result[['PERSON_ID', 'DISPLAY_FIRST_LAST']].to_dict(orient='records')
