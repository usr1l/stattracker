import requests
from bs4 import BeautifulSoup

url = "https://www.basketball-reference.com/wnba/players/c/clarkca02w/gamelog/2024/"
response = requests.get(url)

soup = BeautifulSoup(response.content, 'html.parser')

# print(soup)
# # Extract player name
player_name = soup.find('span', itemprop='name')
print(player_name)

# # Extract career statistics
# career_stats_table = soup.find('table', id='per_game-playoffs_per_game')
# career_stats_rows = career_stats_table.find_all('tr')

# # for row in career_stats_rows:
# #     cols = row.find_all('td')
# #     if cols:
# #         season = cols[0].text.strip()
# #         games_played = cols[1].text.strip()
# #         points_per_game = cols[2].text.strip()
# #         print(f"Season: {season}, Games Played: {games_played}, Points Per Game: {points_per_game}")
