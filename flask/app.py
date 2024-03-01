from flask import Flask, render_template, request, jsonify
import pandas as pd
from pymongo import MongoClient
from flask_cors import CORS

client = MongoClient('localhost', 27017)
db = client.movies.info
db_upcoming = client.movies.upcoming
db_boxoffice = client.movies.boxoffice

app = Flask(__name__)
CORS(app)  # 모든 origin에서의 모든 요청을 허용합니다.


# 메인페이지
@app.route('/main')
def main():
    movie_list = list(db.find())
    # msg = '영화 업데이트는 매주 수요일입니다.'
    movie_list = pd.DataFrame(movie_list)
    movie_list.drop(columns=['_id', 'positive', 'keywords'], inplace=True)
    
    movie_list_top5 = movie_list[movie_list['mp4_url'] != '0'][:5]
    top5_list = list(movie_list_top5.name.values)
    
    movie_list_filter = movie_list[~movie_list['name'].isin(top5_list)]
    
    movie_list_top5 = movie_list_top5.to_dict(orient='records')
    movie_list_filter = movie_list_filter.to_dict(orient='records')
    
    return jsonify({'top5' : movie_list_top5, 'result' : movie_list_filter})

# 정렬
@app.route('/main/<sort_type>')
def sortBy(sort_type):

    movie_list = list(db.find())
    movie_list = sorted(movie_list, key=lambda x: x[sort_type], reverse=True)
    
    for movie in movie_list:
        movie.pop('_id')
        movie.pop('positive')
        movie.pop('keywords')
    
    return jsonify({'result' : movie_list})



@app.route('/main/detail/<name>')
def detail(name):

    movie_list = db.find_one({'name': name})
    movie_list.pop('_id')

    return jsonify({'result': movie_list})

@app.route('/upcoming')
def upcoming():
    movie_list = list(db_upcoming.find())
    
    movie_list = pd.DataFrame(movie_list)
    movie_list.drop(columns=['_id', 'code'], inplace=True)
    movie_list_filter = movie_list.to_dict(orient='records')
    
    return jsonify({'result' : movie_list_filter})

@app.route('/upcoming/<sort_type>')
def upcoming_sortBy(sort_type):

    movie_list = list(db_upcoming.find())
    if sort_type == 'date':
        movie_list = sorted(movie_list, key=lambda x: x[sort_type], reverse=False)
    else:
        movie_list = sorted(movie_list, key=lambda x: x[sort_type], reverse=True)
        
    movie_list = pd.DataFrame(movie_list)
    movie_list.drop(columns=['_id'], inplace=True)
    movie_list = movie_list.to_dict(orient='records')
    
    return jsonify({'result' : movie_list})

@app.route('/upcoming/detail/<name>')
def upcoming_detail(name):

    movie_list = db_upcoming.find_one({'name': name})
    movie_list.pop('_id')

    return jsonify({'result': movie_list})


@app.route('/boxoffice')
def boxoffice():
    
    result_list = list(db_boxoffice.find())
    for result in result_list:
        result.pop('_id')
    
    return jsonify({'result' : result_list})
    

@app.route('/favicon.ico')
def favicon():
    pass

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)