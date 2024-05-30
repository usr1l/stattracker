from nba_api.stats.static import teams, players
from nba_api.stats.endpoints import commonallplayers, CommonTeamRoster
import pandas as pd

CURRENT_SEASON = '2023-24'


def get_nba_players_csv():
    players = commonallplayers.CommonAllPlayers(is_only_current_season=1)
    players_df = players.get_data_frames()[0]
    players_df[['PERSON_ID', 'DISPLAY_FIRST_LAST']].to_csv(
        'nba_players.csv', index=False)


def get_nba_teams():
    teams_data = teams.get_teams()
    teams_dict = {}
    for team in teams_data:
        teams_dict[team['full_name'].split()[-1].lower()] = [team['id'],
                                                             team['full_name'], team['abbreviation']]

    return teams_dict


class NBA:
    def __init__(self, csv_file):
        self.csv_file = csv_file or None
        # Read the CSV file into a DataFrame
        self.df = pd.read_csv(csv_file) if csv_file else None
        self.teams = get_nba_teams()

    def check_csv_file(self):
        if self.csv_file is None:
            return "No CSV file found. Please provide a CSV file."
        else:
            return self.csv_file

    def change_csv_file(self, csv_file):
        self.csv_file = csv_file
        self.df = pd.read_csv(csv_file)

    def get_id_by_player_name(self, player_name):
        # Search for the player name
        result = self.df[self.df['DISPLAY_FIRST_LAST'].str.contains(
            player_name, case=False, na=False)]

        # Check if the result is empty
        if result.empty:
            return f"No player found with the name: {player_name}"
        else:
            return result['PERSON_ID'].values[0]

    # def get_player_name_by_id(self, player_id):


    def get_id_by_team_name(self, team_name):
        if team_name == "":
            return ""
        elif self.teams[team_name.lower()]:
            return self.teams[team_name.lower()][0]
        else:
            return ""

    def get_team_abbreviation_by_name(self, team_name):
        if team_name == "":
            return ""
        elif self.teams[team_name.lower()]:
            return self.teams[team_name.lower()][2]
        else:
            return ""

    def get_full_team_name(self, team_name):
        if team_name == "":
            return ""
        elif self.teams[team_name.lower()]:
            return self.teams[team_name.lower()][1]
        else:
            return ""

    def get_player_by_name(self, player_name):
        # Search for the player name
        result = self.df[self.df['DISPLAY_FIRST_LAST'].str.contains(
            player_name, case=False, na=False)]

        # Check if the result is empty
        if result.empty:
            return f"No player found with the name: {player_name}"
        else:
            return [result['PERSON_ID'].values[0], result['DISPLAY_FIRST_LAST'].values[0]]

    def get_player_by_id(self, player_id):
        # Search for the player name
        result = self.df[self.df['PERSON_ID'] == player_id]

        # Check if the result is empty
        if result.empty:
            return f"No player found with the ID: {player_id}"
        else:
            return [result['PERSON_ID'].values[0], result['DISPLAY_FIRST_LAST'].values[0]]

    def get_players_by_team(self, team_name):
        team_id = self.teams[team_name.lower()][0]
        team_roster = CommonTeamRoster(team_id=team_id,
                                       season=CURRENT_SEASON)
        team_roster_df = team_roster.get_data_frames()[0]

        # returns [{'PLAYER_ID': 2544, 'PLAYER': 'LeBron James'}, ...]
        # team_roster_df[['PLAYER_ID', 'PLAYER']].to_dict(orient='records')
        return {player['PLAYER']: player['PLAYER_ID'] for player in team_roster_df.to_dict(orient='records')}
