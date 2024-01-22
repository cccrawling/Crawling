import pandas as pd
from bs4 import BeautifulSoup
import requests



def crawling_active():
    headers = {'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get('https://search.daum.net/search?w=tot&DA=TMZ&q=%EC%9D%BC%EA%B0%84%EC%98%81%ED%99%94%EC%88%9C%EC%9C%84', headers=headers)
    data = BeautifulSoup(data.text, 'html.parser')


    # name 
    name_list = []


    data_list = data.find_all('a', class_='tit_main')
    num = len(data_list)

    for i in range(num):
        name_list.append(''.join(data_list[i].text.split(' ')[1:-1]))
        
        
    # date
    data_list = data.find_all('dd', class_='cont')
    num = len(data_list)

    date_list = []
    people_list = []
    for i in range(num):
        if i%2 == 1:
            people_list.append(data_list[i].text)
        else:
            date_list.append(data_list[i].text)

    date_list = date_list[:-1]
    people_list = people_list[:-1]


    # img
    img_list = data.find_all('img', class_='thumb_img')
    img_url_list = []

    for i in range(len(img_list)):
        url = img_list[i]['data-original-src']
        img_url_list.append(url)
        
    #url
    site_list = data.find_all('a', class_='tit_main')
    site_url_list = []
    url_path = 'https://search.daum.net/search'

    for i in range(len(site_list)):
        url = url_path + site_list[i]['href']
        site_url_list.append(url)
        
        
        
    num_list = [len(name_list), len(people_list), len(date_list), len(img_url_list), len(site_url_list)]
    num_min = min(num_list)

    name_list = name_list[:num_min]
    people_list = people_list[:num_min]
    date_list = date_list[:num_min]
    img_url_list = img_url_list[:num_min]
    site_url_list = site_url_list[:num_min]


    df = pd.DataFrame({'name' : name_list,
                    'people' : people_list,
                    'date' : date_list,
                    'img_url' : img_url_list,
                    'url' : site_url_list,
                    'trash' : [0]*num_min,
                    'likes' : [0]*num_min
                    })
    return df



