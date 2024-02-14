import re
import pandas as pd
from pymongo import MongoClient
from bs4 import BeautifulSoup
import requests


client = MongoClient('localhost', 27017)
db = client.movies

collection = db.info
df = pd.DataFrame(list(collection.find())).drop(columns='_id')

# 전체 df
title_filter = df.english_name.apply(lambda x: re.sub(r'[^a-zA-Z0-9]',' ',x))
title_list = list(title_filter.apply(lambda x: re.sub(r'\s+', '_', x)))
date = list(df.date.apply(lambda x:[x[:4], str(int(x[:4])-1)]))

# # 외국영화만
# idx_list = []
# country_list = list(df['info'].apply(lambda x: x.split(', ')[2:]))
# for idx, country in enumerate(country_list):
#     if '한국' not in country and len(country) != 0:
#         idx_list.append(idx)
        
# # 외국영화만
# title_filter = df.iloc[idx_list, :].english_name.apply(lambda x: re.sub(r'[^a-zA-Z0-9]',' ',x))
# title_list = list(title_filter.apply(lambda x: re.sub(r'\s+', '_', x)))
# date = list(df.iloc[idx_list, :].date.apply(lambda x:x[:4]))

list_zip = zip(title_list, date)

items = []

for name, date in list_zip:
    url = 'https://www.rottentomatoes.com/m/' + name
    data = requests.get(url)
    if data.status_code == 200:
        soup = BeautifulSoup(data.text, 'html.parser')
        year = soup.find('p', class_='info').text.split(',')[0]
        
        if year in date:
            popcorn = soup.find('score-board-deprecated')['audiencescore']
            tomato = soup.find('score-board-deprecated')['tomatometerscore']
            
            items.append({
                'tomato' : tomato,
                'popcorn' : popcorn
                })
        else:
            items.append({
            'tomato' : '',
            'popcorn' : ''
            })
    else:
        items.append({
            'tomato' : '',
            'popcorn' : ''
            })
        
df_t = pd.DataFrame(items)
df_concat = pd.concat([df, df_t], axis=1)
df_filter = df_concat[df_concat['popcorn'] !='']
df_filter_dict = df_filter.to_dict(orient='records')

collection_box = db.boxoffice
collection_box.insert_many(df_filter_dict)