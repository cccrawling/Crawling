import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch import nn
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from datetime import datetime, timedelta
import numpy as np
from pymongo import MongoClient

# 감정분석 모델링 함수
def process_news_keyword(article):
    tokenizer = AutoTokenizer.from_pretrained("snunlp/KR-FinBert-SC")
    model = AutoModelForSequenceClassification.from_pretrained("snunlp/KR-FinBert-SC")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    # 감성 분석 결과 초기화
    sentiments_list = []

    review_list = list(article.review.values)
    # 각 제목에 대한 감성 분석 수행
    for review in review_list:
        temp_sentiment = []
        for text in (review):
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            inputs = inputs.to(device)

            with torch.no_grad():
                outputs = model(**inputs)

            prediction = nn.functional.softmax(outputs.logits, dim=1)
            positive_score = prediction[:, 2].item()
            negative_score = prediction[:, 0].item()
            neutral_score = prediction[:, 1].item()

            # 긍정, 부정, 중립 점수에 따른 감성 결정
            if positive_score > max(negative_score, neutral_score):
                sentiment = 1  # 긍정
            elif negative_score > max(positive_score, neutral_score):
                sentiment = -1  # 부정
            else:
                sentiment = 0  # 중립
                
        temp_sentiment.append(sentiment)
        val = np.sum(temp_sentiment)
        sentiments_list.append(val)
        
    
    article['sentiment'] = sentiments_list


    return article

client = MongoClient('localhost', 27017)
collection = client.movies.cgv
print(pd.DataFrame(list(collection.find())))
