import re
import pandas as pd
from pymongo import MongoClient
import pandas as pd
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

client = MongoClient('localhost', 27017)
db = client.movies

collection = db.reviews
df = pd.DataFrame(list(collection.find())).drop(columns='_id')

df.review = df.review.apply(lambda x: x[:3])
df_t = df.to_dict(orient='records')

items = []
for dic in df_t:
    for review in dic['review']:
        items.append({
            'name' : dic['name'],
            'review' : review
        })
data = pd.DataFrame(items)
data.review = data.review.apply(lambda x: re.sub(r'\s+', ' ', x))

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

# data.to_csv('review_sentiment.csv', index=False)

# 긍부정도 평가
unique_movie_ids = data['name'].unique()

positive = []
negative = []

for movie_id in unique_movie_ids:
    selected_rows = data.loc[data['name'] == movie_id]
    
    # sentiment 컬럼 값에 대한 카운트
    sentiment_counts = selected_rows['sentiment'].value_counts()
    
    # 각 sentiment 값의 비율 계산
    positive_percentage = sentiment_counts.get(1, 0) / len(selected_rows) * 100
    negative_percentage = sentiment_counts.get(0, 0) / len(selected_rows) * 100
    
    positive.append(positive_percentage)


name = list(data.name)
collection_info = db.info
for name, per in zip(name, positive):
    collection_info.update_one({'name' : name}, {'$set' : {'positive': per}})
