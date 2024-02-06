import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

client = MongoClient('mongodb://admin:admin12345@10.0.5.126:27017/admin')
db = client.movies.lotte

movie_code_list = []  # 영화 코드
name_list = []  # 영화 제목
review_list = []  # 리뷰 리스트
num = 10  # 한 번에 들어가는 리뷰 개수

url = 'https://www.lottecinema.co.kr/LCWS/Movie/MovieData.aspx'

# 사용자 에이전트(User-Agent) 및 robots.txt 무시 설정 추가
headers = {
    "User-Agent": "Mozilla/5.0",
    "robots": "noindex, nofollow"  # robots.txt를 무시하는 설정
}

payload = {
    "paramList": '{"MethodName":"GetMoviesToBe","channelType":"HO","osType":"Chrome","osVersion":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36","multiLanguageID":"KR","division":1,"moviePlayYN":"Y","orderType":"1","blockSize":100,"pageNo":1,"memberOnNo":""}'
}

response = requests.post(url, data=payload, headers=headers)
data_list = json.loads(response.text)['Movies']['Items']

for i in range(len(data_list)):
    code = data_list[i]['RepresentationMovieCode']
    name = data_list[i]['MovieNameUS']
    if code != 'AD':
        movie_code_list.append(code)
        name_list.append(name)

for code in movie_code_list:
    temp = []
    for j in range(1, 21):
        payload = {
            "paramList": json.dumps({"MethodName": "GetReviews", "channelType": "HO", "osType": "Chrome",
                                        "osVersion": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                        "representationMovieCode": code, "memberID": "", "realReviewYN": "Y",
                                        "sortSeq": 1, "pageNo": j, "pageSize": num})
        }
        response = requests.post(url, data=payload, headers=headers)
        data_list = json.loads(response.text)['TotalReviewItems']['Items']
        try:
            for k in range(num):
                review = data_list[k]['ReviewText']
                temp.append(review)
        except:
            break
    review_list.append(temp)

lotte_data = {
    'name': name_list,
    'review': review_list
}
lotte_df = pd.DataFrame(lotte_data)
df_dict = lotte_df.to_dict(orient='records')

# 데이터 삽입
db.insert_many(df_dict)
