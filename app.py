import time
import numpy as np
import pandas as pd
import requests
import json
from bs4 import BeautifulSoup
pd.set_option('display.max_columns', None)

test = "https://www.statmuse.com/nba/game/4-29-2024-okc-at-nop-75742"

# r = requests.get(url=test)
# soup = BeautifulSoup(r.text, 'html.parser')
# print(soup)

# data_points = soup.find_all('div', {'class': 'data-point'})
# # print(data_points)
# data = [dp.text.strip() for dp in data_points]

# # print(data)

r = requests.get(url=test)
soup = BeautifulSoup(r.text, 'html.parser')

# Find the script tag with the relevant data
script_tag = soup.find('script', {'id': 'initial-state'})

# Extract the script tag content
script_content = script_tag.contents[0]

# Remove the first part of the content (up to the first ';')
script_content = script_content.split(';')[1]

# Parse the JSON data
data = json.loads(script_content)

# Extract the game data
game_data = data['game']

# Print the game data
print(game_data)
