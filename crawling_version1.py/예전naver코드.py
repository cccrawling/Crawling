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