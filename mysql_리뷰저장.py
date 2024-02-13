import pandas as pd
from sqlalchemy import create_engine

# MySQL 
engine = create_engine("mysql+pymysql://아이디:비밀번호@엔드포인트:포트/movie")

query = 'SELECT * FROM movie_reviews'
data_frame = pd.read_sql(query, engine)

print(data_frame)

data_frame.to_csv('movie_reviews.csv', index=False)
