import time
import numpy as np
import pandas as pd
import requests
import re
import json
from bs4 import BeautifulSoup
pd.set_option('display.max_columns', None)

test = "https://www.nba.com/stats/teams/traditional?sort=PTS&dir=-1"
test2 = "https://www.statmuse.com/nba/ask/haliburton-last-20-games"

r = requests.get(url=test)
soup = BeautifulSoup(r.content, 'html.parser')
print(soup)

# # data_points = soup.find_all('div', {'class': 'data-point'})
# # print(data_points, 'done')
# # data = [dp.text.strip() for dp in data_points]

# # print(data)
