import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient
import pymysql
import time


img_list = []
url_list = []
name_list = []
rank_list = []
date_list = []
runtime_list = []
country_list = []
people_list = []


data = requests.get('http://www.cgv.co.kr/movies/?lt=1&ft=1')
soup = BeautifulSoup(data.text, 'html.parser')

num = 19
for i in range(num):
    soup_filter_top = soup.find_all('div', class_='box-image')[i]

    img_list.append(soup_filter_top.find('img')['src'])
    url_list.append('http://www.cgv.co.kr' + soup_filter_top.find('a')['href'])

for url in url_list:
    data = requests.get(url)
    soup = BeautifulSoup(data.text, 'html.parser')

    name = soup.find(class_='title').find('strong').text
    name = ' '.join(name.split(', '))
    name_list.append(name)
    
    soup_filter = soup.find('div', class_='spec').find_all('dd')
    temp = soup_filter[-1].text
    numbers = ''.join(re.findall(r'\d', temp))
    
    if len(numbers) == 8:
        date_list.append(soup_filter[-1].text)
        
        text = soup_filter[-2].text
        runtime_list.append(text.split(',')[1].strip())
        country_list.append(text.split(',')[2].strip())
    else:
        date_list.append(soup_filter[-2].text)
        
        text = soup_filter[-3].text
        runtime_list.append(text.split(',')[1].strip())
        country_list.append(text.split(',')[2].strip())

    rank_list.append(soup.find('div', class_='egg-gage small').find(class_="percent").text)
    people_list.append(int(''.join(soup.find('p', class_='desc').find('em').text.split(','))))

movie_data = {
        'name': name_list,
        'url': url_list,
        'img_url': img_list,
        'people' : people_list,
        'score': rank_list,
        'date' : date_list,
        'country' : country_list,
        'runtime' : runtime_list,
    }
    
movies_df = pd.DataFrame(movie_data, columns=['name', 'url', 'img_url', 'mp4_url', 'people', 'score','date','country', 'runtime'])

temp_name_list = []
temp_code_list = []
url = "https://www.megabox.co.kr/on/oh/oha/Movie/selectMovieList.do"
headers = {"User-Agent": "Mozilla/5.0"}

for page_number in range(1, 3):
    payload = {
        "currentPage": str(page_number),
        "recordCountPerPage": "20",
        "pageType": "ticketing",
        "ibxMovieNmSearch": "",
        "onairYn": "Y",
        "specialType": "",
        "specialYn": "N"}

    response = requests.post(url, json=payload, headers=headers)
    data = json.loads(response.text)

    for movie in data['movieList']:
        temp_name_list.append(movie['movieNm'])
        temp_code_list.append(movie['movieNo'])
        
        
url = 'https://www.megabox.co.kr/on/oh/oha/Movie/selectMovieStilDetail.do'
headers = {"User-Agent": "Mozilla/5.0"}

mp4_list = []
for code in temp_code_list:
    payload = {
        'rpstMovieNo' : code
    }

    response = requests.post(url, json=payload, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    try:
        mp4 = soup.find('div', class_='swiper-slide').find('source')['src']
        mp4_list.append(mp4)
        
    except:
        mp4_list.append('0')

df_temp = pd.DataFrame()
df_temp['name'] = temp_name_list
df_temp['mp4_url'] = mp4_list

df_t = pd.merge(movies_df, df_temp, on='name', how='left').drop(columns='mp4_url_x')
df_t.rename(columns={'mp4_url_y' : 'mp4_url'}, inplace=True)
df_t.mp4_url = df_t.mp4_url.apply(lambda x: '0' if pd.isna(x) else x)

df_t = df_t.to_dict(orient='records')
    
    
client = MongoClient('localhost', 27017)
db = client.movies

# 삭제할 콜렉션 이름 리스트
collections_list = ['info', 'cgv', 'daum', 'megabox', 'naver', 'reviews']  # 삭제할 콜렉션 이름들을 여기에 추가
 
# 각 콜렉션을 하나씩 삭제
for collection_name in collections_list:
    db.drop_collection(collection_name)

collection = db.info
collection.insert_many(df_t)

# cgv
def get_cgv_reviews():

    collection = db.cgv
    
    cgv_review_list = []
    cgv_movie_list = []
    cgv_name_list = []

    cgv_url = "http://www.cgv.co.kr/movies/?lt=1&ft=1"
    cgv_review_url = 'http://www.cgv.co.kr/common/ajax/point.aspx/GetMoviePointVariableList'
    headers = {"User-Agent": "Mozilla/5.0"}
    cgv_num = 10

    cgv_response = requests.get(cgv_url, headers=headers)
    cgv_soup = BeautifulSoup(cgv_response.text, 'html.parser')

    # class가 'box-image'인 div 안에 있는 모든 a 태그 가져오기
    box_image_divs = cgv_soup.find_all('div', class_='box-image')
    box_contents = cgv_soup.find_all('div', class_='box-contents')

    # 영화리스트
    for box_image_div, box_content in zip(box_image_divs, box_contents):
        cgv_a_tag = box_image_div.find('a')
        img_tag = box_image_div.find('img')
        name_tag = ','.join(img_tag['alt'][:-4].split())
        name = ' '.join(name_tag.split(','))
        cgv_name_list.append(name)
        
        c_num = re.search(r'\d+', cgv_a_tag['href']).group()
        cgv_movie_list.append(int(c_num))

    # 리뷰 크롤링
    for i in cgv_movie_list:
        temp = []
        for j in range(1, 21):
            payload = {'movieIdx': i, 'pageIndex': j, 'pageSize': cgv_num, 'orderType': 0, 'filterType': 1,
                        'isTotalCount': False, 'isMyPoint': 'false'}
            try:
                response = requests.post(cgv_review_url, json=payload, headers=headers)
                data = json.loads(response.text)
                for k in range(cgv_num):
                    review = json.loads(data['d'])['List'][k]['CommentText']
                    temp.append(review)
            except:
                break
        cgv_review_list.append(temp)

    cgv_data = {
        'name': cgv_name_list,
        'review': cgv_review_list
    }
    cgv_df = pd.DataFrame(cgv_data)
    df_dict = cgv_df.to_dict(orient='records')
    
    # 데이터 삽입
    collection.insert_many(df_dict)
    
    return 'good'


# 다음
def get_daum_reviews():

    collection = db.daum

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    
    # 다음 상영영화 이름리스트
    data = requests.get('https://search.daum.net/search?w=tot&q=%ED%98%84%EC%9E%AC%EC%83%81%EC%98%81%EC%9E%91&rtmaxcoll=0SP&DA=MOR', headers=headers)
    html_data = BeautifulSoup(data.text, 'html.parser')

    # name -> 네이버에서 사용
    name_list = []
    data_list = html_data.find_all('a', class_='fn_tit txt_ellip')
    num = len(data_list)

    for i in range(num):
        name_list.append(' '.join(data_list[i].text.split()))

    # url -> 다음 리뷰 긁어올때 사용
    url_list = []
    url = 'https://search.daum.net/search'
    data_list = html_data.find_all('div', class_='wrap_thumb')
    data_list = data_list[:num]
    for i in range(num):
        movie_url = url + data_list[i].find('a')['href']
        url_list.append(movie_url)

    # reivew 링크 저장
    movie_code_list = []
    for url in url_list:
        data = requests.get(url)
        daum_filter = BeautifulSoup(data.text, 'html.parser')
        daum_filter = daum_filter.find_all(attrs={'disp-attr': 'EM1'})[0]
        try:
            link = daum_filter.find_all('dd')[4].find('c-link').get('data-href')
            num = re.search(r'\d+', link).group()
            movie_code_list.append(int(num))
        except:
            movie_code_list.append(0)

    url = 'https://gateway.kinolights.com/graphql'
    num = 10  # 한번에 들어가는 리뷰 개수
    review_list = []  # 리뷰리스트

    for i in movie_code_list:
        temp = []
        if i != 0:
            for j in range(0, 210, 10):
                payload = {
                    'operationName': 'QueryReviews',
                    'query': "fragment FragmentReviewField on UserReviewOutput {\n  id\n  reviewTitle\n  review\n  reviewLink\n  isPrivate\n  isPreview\n  hasSpoiler\n  likeCount\n  commentCount\n  sharedCount\n  viewCount\n  deletedUserId\n  createdAt\n  isMyLike\n  userIndexRating {\n    index\n    __typename\n  }\n  userStarRating {\n    star\n    __typename\n  }\n  movie {\n    id\n    titleKr\n    posterImage {\n      path\n      __typename\n    }\n    __typename\n  }\n  reviewer {\n    id\n    name\n    isPremium\n    profileImage {\n      path\n      __typename\n    }\n    __typename\n  }\n  watchedAt {\n    watchedAt\n    __typename\n  }\n  blindStatus\n  isReportedByMe\n  __typename\n}\n\nquery QueryReviews($offset: Int = 0, $limit: Int = 10, $movieId: Int!, $orderBy: ReviewMoviesOrderType!, $orderOption: OrderOptionType!) {\n  reviews(\n    offset: $offset\n    limit: $limit\n    movieId: $movieId\n    orderBy: $orderBy\n    orderOption: $orderOption\n  ) {\n    ...FragmentReviewField\n    __typename\n  }\n}\n",
                    'variables': {'offset': j, 'limit': num, 'movieId': i, 'orderBy': "LIKE", 'orderOption': "DESC"}
                }
                try:
                    response = requests.post(url, json=payload, headers=headers)
                    data_list = json.loads(response.text)['data']['reviews']
                    for k in range(num):
                        review = data_list[k]['reviewTitle']
                        temp.append(review)
                except:
                    break
            review_list.append(temp)
        else:
            review_list.append([0])

    daum_data = {
        'name': name_list,
        'review': review_list
    }
    daum_df = pd.DataFrame(daum_data)

    df_dict = daum_df.to_dict(orient='records')
    
    
    # 데이터 삽입
    collection.insert_many(df_dict)
    
    return 'good'


# 메가박스
def get_megabox_reviews():

    collection = db.megabox
    
    name_list = []
    code_list = []
    url = "https://www.megabox.co.kr/on/oh/oha/Movie/selectMovieList.do"
    headers = {"User-Agent": "Mozilla/5.0"}

    for page_number in range(1, 3):
        payload = {
            "currentPage": str(page_number),
            "recordCountPerPage": "20",
            "pageType": "ticketing",
            "ibxMovieNmSearch": "",
            "onairYn": "Y",
            "specialType": "",
            "specialYn": "N"
        }

        response = requests.post(url, json=payload, headers=headers)
        data = json.loads(response.text)

        for movie in data['movieList']:
            name_list.append(movie['movieNm'])
            code_list.append(movie['movieNo'])
            
    review_list = []  
    for code in code_list:
        url = "https://www.megabox.co.kr/on/oh/oha/Movie/selectOneLnList.do"
        headers = {"User-Agent": "Mozilla/5.0"}

        # 댓글 저장
        all_comments = []

        for page_number in range(1, 11):
            payload = {
                "currentPage": str(page_number),
                "recordCountPerPage": "10",
                "movieNo": f"{code}",
                "onelnEvalDivCd": "",
                "orderCd": ""
            }

            response = requests.post(url, json=payload, headers=headers)
            data = json.loads(response.text)

            # 각 페이지의 댓글을 가져와서 전체 댓글 리스트에 추가
            review = [comment['onelnEvalCn'].replace('\n', '') for comment in data.get('list', [])]
            all_comments.extend(review)
            
        review_list.append(all_comments)
        
    megabox_data = {
            'name': name_list,
            'review': review_list
        }
    megabox_df = pd.DataFrame(megabox_data)
    df_dict = megabox_df.to_dict(orient='records')
    
    # 데이터 삽입
    collection.insert_many(df_dict)
    
    return 'good'


# 네이버버
def get_naver_reviews():

    collection = db.naver

    
    # 다음에서 상영영화 이름 리스트
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get('https://search.daum.net/search?w=tot&q=%ED%98%84%EC%9E%AC%EC%83%81%EC%98%81%EC%9E%91&rtmaxcoll=0SP&DA=MOR', headers=headers)
    html_data = BeautifulSoup(data.text, 'html.parser')

    name_list = []
    movie_code = []


    data_list = html_data.find_all('a', class_='fn_tit txt_ellip')
    num = len(data_list)

    for i in range(num):
        name_list.append(' '.join(data_list[i].text.split()))

    for name in name_list:
        url = f'https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=영화{name}'

        data = requests.get(url)
        html_data = BeautifulSoup(data.text, 'html.parser')

        # movie_code
        try:
            code = html_data.find_all('div', class_='button_like _reactionModule')[0]['data-cid']
            movie_code.append(code)
        except:
            movie_code.append('16051833')
        time.sleep(1)

    review_list = []
    for code in movie_code:
        temp = []
        for i in range(1, 21):
            url = 'https://m.search.naver.com/p/csearch/content/nqapirender.nhn'
            params = {
                'where': 'nexearch',
                'pkid': '68',
                'fileKey': 'movieKBPointAPI',
                'u1': code,
                'u5': 'true',
                '_callback': '_nexearch_where_68_pkid_movieKBPointAPI_fileKey_196364_u1_true_u5_sympathyScore_u3_false_u4_3_u2',
                'u3': 'sympathyScore',
                'u4': 'false',
                'u2': f'{i}'
            }
            response = requests.get(url, params=params)

            # JSON 데이터 추출
            json_data = json.loads(response.text[response.text.index('{'):response.text.rindex('}') + 1])
            html_content = json_data.get('html', '')

            # HTML 콘텐츠 파싱
            soup = BeautifulSoup(html_content, 'html.parser')

            # 이상한 soup// HTML 구조로 변환
            html_document = soup.prettify()
            target_span = soup.find_all('span', class_='desc _text')

            # 각 span 엘리먼트에서 텍스트 추출하여 리스트에 저장
            text_list = [span.text.strip() for span in target_span]

            for text in text_list:
                temp.append(text)

        review_list.append(temp)
    
    
    
    naver_data = {
        'name': name_list,
        'review': review_list
    }
    
    naver_df = pd.DataFrame(naver_data, columns=['name', 'review'])
    df_dict = naver_df.to_dict(orient='records')
    
    # 데이터 삽입
    collection.insert_many(df_dict)
    
    return 'good'


a = get_cgv_reviews()
b = get_daum_reviews()
c = get_megabox_reviews()
d = get_naver_reviews()

e = a+b+c+d


# 다음
db_dict = list(db['daum'].find())
daum = pd.DataFrame(db_dict)
daum.drop(columns='_id', inplace=True)

# cgv
db_dict = list(db['cgv'].find())
cgv = pd.DataFrame(db_dict)
cgv.drop(columns='_id', inplace=True)

# megabox
db_dict = list(db['megabox'].find())
megabox = pd.DataFrame(db_dict)
megabox.drop(columns='_id', inplace=True)

# naver
db_dict = list(db['naver'].find())
naver = pd.DataFrame(db_dict)
naver.drop(columns='_id', inplace=True)


# 다음 기준으로 제목 동일한 데이터만 추출                    
column = list(cgv.name.values)

daum = daum[daum['name'].isin(column)]
naver = naver[naver['name'].isin(column)]
megabox = megabox[megabox['name'].isin(column)]

# merge
def merge(df1, df2):
    merge_df = pd.merge(df1, df2, on='name', suffixes=('_df1', '_df2'), how='left')
    merge_df['review_df2'] = merge_df['review_df2'].fillna(0)
    merge_df['review_df2'] = merge_df['review_df2'].apply(lambda x: [] if x==0 else x)
    merge_df['review'] = merge_df['review_df1'] + merge_df['review_df2']
    merge_df = merge_df.drop(['review_df1', 'review_df2'], axis=1)
    
    return merge_df

result2 = merge(cgv, megabox)
result3 = merge(result2, daum)
result = merge(result3, naver)


def pre(review):
    if isinstance(review, str):  # 입력이 문자열인지 확인합니다.
        filtered_review = re.sub(r"[^a-zA-Z0-9가-힣]", " ", review)
        return filtered_review
    else:
        return ''  # 문자열이 아닌 경우 빈 문자열을 반환합니다.

result.review = result.review.apply(lambda x: [pre(i) for i in x])
result.review = result.review.apply(lambda x: x[:3])
result_dict = result.to_dict(orient='records')

collection = db.reviews
collection.insert_many(result_dict)

# cursor.execute("SELECT `id`, `name` FROM `movie_info`")
# movie_id_map = {row['name']: row['id'] for row in cursor.fetchall()}

# for review_data in result_dict:
#     # 해당 리뷰의 영화 ID 가져오기
#     movie_id = movie_id_map.get(review_data['name'])
#     for review in review_data['review']:
#         print(review)
#         sql = "INSERT INTO `movie_reviews` (`movie_id`, `review`) VALUES (%s, %s)"
#         cursor.execute(sql, (movie_id, review))
# connection.commit()


