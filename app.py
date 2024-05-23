from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import matplotlib.pyplot as plt
import time
import numpy as np
import pandas as pd
import requests
import re
import json
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, get_nba_players_from_csv
pd.set_option('display.max_columns', None)

nba_players = get_nba_players_from_csv('nba_players.csv')
print(nba_players('LeBron James')[0])
