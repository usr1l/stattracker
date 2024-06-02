from py_ball import league, image

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}

league_id = '10' # WNBA
franchises = league.League(headers=headers,
                           endpoint='franchisehistory',
                           league_id=league_id)

print(franchises)
