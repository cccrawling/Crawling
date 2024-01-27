import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
import time
import multiprocessing
import concurrent.futures
from pymongo import MongoClient


client = MongoClient('mongodb://admin:admin12345@10.0.5.126:27017/admin')
db = client.movies

# 삭제할 콜렉션 이름 리스트
collections_to_drop = ['cgv', 'lotte', 'megabox', 'daum', 'naver']  # 삭제할 콜렉션 이름들을 여기에 추가

# 각 콜렉션을 하나씩 삭제
for collection_name in collections_to_drop:
    db.drop_collection(collection_name)
    


def get_cgv_reviews():
    
    client = MongoClient('mongodb://admin:admin12345@10.0.5.126:27017/admin')
    db = client.movies.cgv
    
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
        cgv_name_list.append(name_tag)
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
    db.insert_many(df_dict)


def get_daum_reviews():
    
    client = MongoClient('mongodb://admin:admin12345@10.0.5.126:27017/admin')
    db = client.movies.daum

    
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    
    # 다음 상영영화 이름리스트
    data = requests.get('https://search.daum.net/search?w=tot&q=%ED%98%84%EC%9E%AC%EC%83%81%EC%98%81%EC%9E%91&rtmaxcoll=0SP&DA=MOR', headers=headers)
    html_data = BeautifulSoup(data.text, 'html.parser')

    # name -> 네이버에서 사용
    name_list = []
    data_list = html_data.find_all('a', class_='fn_tit txt_ellip')
    num = len(data_list)

    for i in range(num):
        name_list.append(''.join(data_list[i].text.split()))

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
    db.insert_many(df_dict)

def get_lotte_reviews():
    
    client = MongoClient('mongodb://admin:admin12345@10.0.5.126:27017/admin')
    db = client.movies.lotte
    
    movie_code_list = []  # 영화 코드
    name_list = []  # 영화 제목
    review_list = []  # 리뷰 리스트
    num = 10  # 한 번에 들어가는 리뷰 개수

    url = 'https://www.lottecinema.co.kr/LCWS/Movie/MovieData.aspx'
    headers = {"User-Agent": "Mozilla/5.0"}
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


def get_megabox_reviews():
    
    client = MongoClient('mongodb://admin:admin12345@10.0.5.126:27017/admin')
    db = client.movies.megabox
    
    movie_list = []
    url = "https://www.megabox.co.kr/on/oh/oha/Movie/selectMovieList.do"
    headers = {"User-Agent": "Mozilla/5.0"}

    # 영화별 댓글을 저장할 딕셔너리
    movie_comments_dict = {}

    for page_number in range(1, 4):
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
            name = movie['movieNm']
            movie_id = movie['movieNo']
            movie_list.append(movie_id)

            # Include name in the dictionary
            movie_comments_dict[movie_id] = {'name': name, 'review': []}

    for movie_num in movie_list:
        url = "https://www.megabox.co.kr/on/oh/oha/Movie/selectOneLnList.do"
        headers = {"User-Agent": "Mozilla/5.0"}

        # 댓글 저장
        all_comments = []

        for page_number in range(1, 11):
            payload = {
                "currentPage": str(page_number),
                "recordCountPerPage": "10",
                "movieNo": f"{movie_num}",
                "onelnEvalDivCd": "",
                "orderCd": ""
            }

            response = requests.post(url, json=payload, headers=headers)
            data = json.loads(response.text)

            # 각 페이지의 댓글을 가져와서 전체 댓글 리스트에 추가
            review = [comment['onelnEvalCn'].replace('\n', '') for comment in data.get('list', [])]
            all_comments.extend(review)

        # Add review and name to the dictionary
        movie_comments_dict[movie_num]['review'] = all_comments

    # Create a DataFrame
    megabox_df = pd.DataFrame.from_dict(movie_comments_dict, orient='index')
    megabox_df.reset_index(inplace=True)

    # Reorder columns
    megabox_df = megabox_df[['name', 'review']]  # 'index',
    megabox_df.columns = ['name', 'review']  # 'movie_id',
    
    df_dict = megabox_df.to_dict(orient='records')
    
    # 데이터 삽입
    db.insert_many(df_dict)

def crawl_naver_movies():
    
    client = MongoClient('mongodb://admin:admin12345@10.0.5.126:27017/admin')
    db = client.movies.naver

    
    # 다음에서 상영영화 이름 리스트
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get('https://search.daum.net/search?w=tot&q=%ED%98%84%EC%9E%AC%EC%83%81%EC%98%81%EC%9E%91&rtmaxcoll=0SP&DA=MOR', headers=headers)
    html_data = BeautifulSoup(data.text, 'html.parser')

    # name -> 네이버에서 사용
    name_list = []
    # 네이버에서 기본정보 불러오기(20개(다음에 등록된 이름 기준이라서, 이름 list 바꾸면 더 가져올 수 있을 듯))
    movie_code = []
    url_list = []
    img_list = []
    rank_list = []
    genre_list = []
    country_list = []
    runtime_list = []
    people_list = []

    data_list = html_data.find_all('a', class_='fn_tit txt_ellip')
    num = len(data_list)

    for i in range(num):
        name_list.append(''.join(data_list[i].text.split()))

    for name in name_list:
        url = f'https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=영화{name}'
        # url
        url_list.append(url)

        data = requests.get(url)
        html_data = BeautifulSoup(data.text, 'html.parser')

        # movie_code
        code = html_data.find_all('div', class_='button_like _reactionModule')[0]['data-cid']
        movie_code.append(code)

        # img_url
        try:
            img_url = html_data.find_all('img', class_='_img')[0]['src']
            img_list.append(img_url)
        except:
            img_url = html_data.find('img')['src']
            img_list.append(img_url)

        # 관객수, 평점
        try:
            item_info = html_data.find_all('div', class_='item_info')
            
            people = item_info[0].text.split()[-1]
            people_list.append(people)
            
            rank = item_info[1].text.split()[0]
            rank_list.append(rank)
        except:
            item_info = html_data.find_all('div', class_='info_group')
            
            rank = item_info[2].text.split()[1]
            rank_list.append(rank)
            
            people = item_info[3].text.split()[1]
            people_list.append(people)

        # 장르, 국가, 시간
        info_group_tag = html_data.find('div', class_='info_group')
        info_list = list(info_group_tag.dd)

        genre = info_list[0]
        info_list.remove(info_list[0])

        runtime = info_list[-1]
        info_list.remove(info_list[-1])

        country = info_list[1:-1]

        if len(country) == 0:
            country = [genre]
            genre = '로맨스'
        genre_list.append(genre)
        country_list.append(country[0])
        runtime_list.append(runtime)

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
        'url': url_list,
        'img_url': img_list,
        'people' : people_list,
        'score': rank_list,
        'genre': genre_list,
        'country' : country_list,
        'runtime' : runtime_list,
        'review': review_list
    }
    
    
    movies_df = pd.DataFrame(naver_data, columns=['name', 'url', 'img_url', 'people', 'score', 'genre','country', 'runtime', 'review'])
    naver_df = movies_df.loc[:,['name', 'review']]
    movies_df.drop(columns=['review'], inplace=True)
    
    df_dict = naver_df.to_dict(orient='records')
    
    # 데이터 삽입
    db.insert_many(df_dict)

def main():
    functions = [get_cgv_reviews, get_daum_reviews, get_lotte_reviews, get_megabox_reviews, crawl_naver_movies]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(lambda func: func(), functions)
        
if __name__ == "__main__":
    main()