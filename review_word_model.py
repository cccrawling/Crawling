import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from konlpy.tag import Okt
from collections import Counter
from sklearn.feature_extraction.text import CountVectorizer
from sqlalchemy import create_engine

# MySQL 연결 설정 (SQLAlchemy 엔진 사용)
db_engine = create_engine("mysql+pymysql://아이디:비밀번호@엔드포인트:포트/movie")

# 데이터프레임 불러오기
# data = pd.read_csv("/content/movie_reviews.csv")

# NaN 값 채우기 또는 삭제
data['review'].fillna('', inplace=True)

# 리뷰 마지막 숫자 제거
def remove_last_num(sentence):
    cleaned_sentence = sentence.rstrip(' 0123456789')
    while cleaned_sentence and cleaned_sentence[-1].isdigit():
        cleaned_sentence = cleaned_sentence.rstrip(' 0123456789')
    return cleaned_sentence

data['review'] = data['review'].apply(remove_last_num)

# 모델, 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained("matthewburke/korean_sentiment")
model = AutoModelForSequenceClassification.from_pretrained("matthewburke/korean_sentiment")

# 감정 분석 함수
def analyze_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)

    # 확률
    probabilities = torch.softmax(outputs.logits, dim=1)
    # 라벨링  긍정1 부정0
    sentiment_label = torch.argmax(probabilities, dim=1).item()

    return  sentiment_label #probabilities.detach().numpy()  = per

# data[review]열 감정분석 후 data[['per', 'sentiment']] 열 추가
data['sentiment'] = data['review'].apply(analyze_sentiment).apply(pd.Series)

# 긍부정도 평가
unique_movie_ids = data['movie_id'].unique()

positive_percentages = []
negative_percentages = []

for movie_id in unique_movie_ids:
    selected_rows = data.loc[data['movie_id'] == movie_id]

    # sentiment 컬럼 값에 대한 카운트
    sentiment_counts = selected_rows['sentiment'].value_counts()

    # 각 sentiment 값의 비율 계산
    positive_percentage = sentiment_counts.get(1, 0) / len(selected_rows) * 100
    negative_percentage = sentiment_counts.get(0, 0) / len(selected_rows) * 100

    positive_percentages.append(positive_percentage)
    negative_percentages.append(negative_percentage)

# 감정 분석 결과 컬럼 추가
data['positive_percentages'] = data['movie_id'].map(dict(zip(unique_movie_ids, positive_percentages)))
data['negative_percentages'] = data['movie_id'].map(dict(zip(unique_movie_ids, negative_percentages)))

# 형태소 분석 및 단어 빈도 계산
custom_stopwords = ['영화']
okt = Okt()
vectorizer = CountVectorizer(stop_words=custom_stopwords, max_features=500)

word_frequencies_list = []
for movie_id in unique_movie_ids:
    selected_rows = data.loc[data['movie_id'] == movie_id]
    reviews = selected_rows['review'].str.cat(sep=' ')

    # 형태소 분석 수행 및 명사만 추출
    nouns = okt.nouns(reviews)

    # 리스트를 공백으로 이어 붙여 문자열로 변환
    processed_review = ' '.join(nouns)

    # 단어 빈도 계산
    word_frequencies = Counter(vectorizer.build_analyzer()(processed_review))

    # 가장 빈도가 높은 단어 상위 5개 리스트에 추가
    most_common_words = word_frequencies.most_common(5)
    word_frequencies_list.append((movie_id, most_common_words))

# 감정 분석 결과 컬럼 추가
data['word_fre'] = data['movie_id'].map(dict(word_frequencies_list))

# 데이터프레임
#data

# 데이터프레임을 DB에 저장
# data.to_sql('movie_reviews', con=db_engine, if_exists='replace', index=False)