from nba_api.stats.endpoints import playergamelog, playercareerstats, commonallplayers
import matplotlib.pyplot as plt
import time
import numpy as np
import pandas as pd
import requests
import re
import json
from bs4 import BeautifulSoup
from get_players import get_nba_players_csv, find_player_by_id
pd.set_option('display.max_columns', None)

print(find_player_by_id("LeBron James"))
