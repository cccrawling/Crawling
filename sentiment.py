import pandas as pd
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from sqlalchemy import create_engine

############
# MySQL 연결 설정 (SQLAlchemy 엔진 사용)
engine = create_engine("mysql+pymysql://admin:admin12345@movie-db.cte4qk2ucq5d.ap-northeast-2.rds.amazonaws.com:3306/movie")

query = 'SELECT * FROM movie_reviews'

# mysql movie_reviews 테이블 데이터 가져와서 csv 저장
data_frame = pd.read_sql(query, engine)
# data_frame.to_csv('movie_reviews.csv', index=False)
data = data_frame
############

# data = pd.read_csv("movie_reviews.csv")
data.dropna(axis=0, inplace=True)

# 리뷰 마지막 숫자제거
def remove_last_num(sentence):
    cleaned_sentence = sentence.rstrip(' 0123456789')
    while cleaned_sentence and cleaned_sentence[-1].isdigit():
        cleaned_sentence = cleaned_sentence.rstrip(' 0123456789')
    return cleaned_sentence

data['review'] = data['review'].apply(remove_last_num)


#모델, 토크나이저 로드
tokenizer = AutoTokenizer.from_pretrained("matthewburke/korean_sentiment")
model = AutoModelForSequenceClassification.from_pretrained("matthewburke/korean_sentiment")

def analyze_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt")
    outputs = model(**inputs)
    
    # 확률
    proabilities = torch.softmax(outputs.logits, dim=1)
    # 라벨링  긍정1 부정0
    sentiment_label = torch.argmax(proabilities, dim=1).item()

    return proabilities.detach().numpy(), sentiment_label

# data[review]열 감정분석 후 data[['per', 'sentiment']] 열 추가
data[['per', 'sentiment']] = data['review'].apply(analyze_sentiment).apply(pd.Series)

data.to_csv('review_sentiment.csv', index=False)

# 긍부정도 평가
unique_movie_ids = data['movie_id'].unique()

positive = []
negative = []

for movie_id in unique_movie_ids:
    selected_rows = data.loc[data['movie_id'] == movie_id]
    
    # sentiment 컬럼 값에 대한 카운트
    sentiment_counts = selected_rows['sentiment'].value_counts()
    
    # 각 sentiment 값의 비율 계산
    positive_percentage = sentiment_counts.get(1, 0) / len(selected_rows) * 100
    negative_percentage = sentiment_counts.get(0, 0) / len(selected_rows) * 100
    
    positive.append(positive_percentage)
    negative.append(negative_percentage)

for i, movie_id in enumerate(unique_movie_ids):
    print(f"Movie ID {movie_id}: 긍정(1)의 비율: {positive[i]:.2f}%, 부정(0)의 비율: {negative[i]:.2f}%")
