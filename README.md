# 🏀 StatTracker

StatTracker is a fast and intuitive tool for exploring NBA data directly within a Jupyter notebook. Built on top of the official NBA API, it makes it simple to view, track, and compare both player and team statistics without the hassle of complex setup. Whether you’re analyzing performance trends, preparing fantasy insights, or just keeping up with your favorite players, StatTracker gives you a streamlined way to access and interact with NBA stats in real time.

![NBA API](https://img.shields.io/badge/API-NBA-orange?logo=nba&logoColor=white)
![Jupyter](https://img.shields.io/badge/Notebook-Jupyter-F37626?logo=jupyter&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9-blue?logo=python&logoColor=white)


## ⚙️ Setup
1. Clone this repository. <pre>git clone https://github.com/yourusername/stattracker.git</pre>

2. Navigate to the root directory and install dependencies. <pre>pip install -r requirements.txt</pre>

3. Launch the application in VSCode from the root directory. <pre>code .</pre>

5. Rename the provided `.env.example` module to `.env`.

4. Create a new Jupyter notebook in the root directory, or rename the example provided. <pre>example.ipynb</pre>

6. In your new Jupyter notebook, import the `pandas` and `matplotlib` libraries, as well as the `NBA`, `NBAStats`, `Analysis`, and `DisplayCharts` classes from the `app.py` module. <pre>
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from app import nba_players, nba_statistics, nba_charts, nba_analysis
</pre>

7. Import `env` variables. <pre>from dotenv import dotenv_values
config = dotenv_values(".env")</pre>Update the current year and other env variables, and be sure to follow the formatting.

8. Create a csv with all current NBA players, or skip this step if csv is already up to date. First, import the `get_nba_players_csv` function from `app.py`. <pre>from get_players import get_nba_players_csv</pre>Then, run the function. A csv file names `nba_players` with all currently active players and their corresponding Player ID's will be created in the `players_csv` directory.

9. Create create a new instance of the NBA class using the newly generated csv file.<pre>nba_players = NBA("players_csv/nba_players.csv")</pre>

10. Create new instances for the NBAStats, Analysis, and DisplayCharts classes as well. <pre>nba_statistics = NBAStats()
nba_charts = DisplayCharts()
nba_analysis = Analysis()
</pre>
If you created multiple cells, run them in order.

## How to Use
When using the NBA API, players will mainly be identified using a player ID. To simplify this process, a ```get_id_by_player_name()``` method can be used to retrieve a player's ID by using their name as an argument. <pre>nba_players.get_id_by_player_name('LeBron James')</pre>

The method call above will return the player ID ```2544```. The spelling of the name is not case sensitive. Likewise, the ```get_player_by_name()``` has a similar funcitonality, but returns both the ID and full player name in a list.

## Features
1. Refresh the Player List<pre>from get_players import get_nba_players_cs
get_nba_players_csv()</pre>

2. Look up a player's player ID<pre>player_id = nba.get_player_id("LeBron James")
==> 2544
</pre>

3. Look up a player's career stats<pre>nba_statistics.get_player_career_stats(2544)</pre>

4. Look up and filter through a player's stats<pre>nba_statistics.get_player_statistics(player_id=2544, matchup="LAL",pts=10,reb=5,ast=5)</pre>
