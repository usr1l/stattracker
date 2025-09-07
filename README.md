# 🏀 StatTracker

StatTracker is a fast and intuitive tool for exploring NBA data directly within a Jupyter notebook. Built on top of the official NBA API, it makes it simple to view, track, and compare both player and team statistics without the hassle of complex setup. Whether you’re analyzing performance trends, preparing fantasy insights, or just keeping up with your favorite players, StatTracker gives you a streamlined way to access and interact with NBA stats in real time.

## ⚙️ Setup
1. Clone this repository. <pre>git clone https://github.com/yourusername/stattracker.git</pre>
2. Navigate to the root directory and install dependencies. <pre>pip install -r requirements.txt</pre>
3. Launch the application in VSCode from the root directory. <pre>code .</pre>
5. Rename the provided `.env.example` module to `.env`.
4. Create a new Jupyter notebook in the root directory, or rename the example provided. <pre>example.ipynb</pre>
6. In your new Jupyter notebook, import the `pandas` and `matplotlib` libraries, as well as the `nba_player`, `nba_statistics`, `nba_charts`, and `nba_analsis` classes from the `app.py` module. <pre>
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from app import nba_players, nba_statistics, nba_charts, nba_analysis
</pre>
7. Import `env` variables. <pre>from dotenv import dotenv_values
config = dotenv_values(".env")</pre>
8. Create a csv with all current NBA players, or skip this step if csv is already up to date.
