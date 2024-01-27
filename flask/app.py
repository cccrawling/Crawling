from flask import Flask, render_template, request
import pandas as pd
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client.movies.card

app = Flask(__name__)


# 메인페이지
@app.route('/')
def main():

    movie_list = list(db.find())
    msg = '!!영화 업데이트는 매주 수요일입니다!!'
    
    return render_template('main.html', movie_list=movie_list, msg=msg)

# 정렬
@app.route('/<sort_type>')
def sortBy(sort_type):
    
    msg = '!!영화 업데이트는 매주 수요일입니다!!'
    all_list = list(db.find())
    
    sorted_movies = sorted(all_list, key=lambda x: x[sort_type], reverse=True)
    return render_template('main.html', movie_list=sorted_movies, msg=msg)

# 메인페이지 버튼 동작
@app.route('/likes', methods=['POST'])
def like():
    name = dict(request.form)['name']
    db.update_one(
        {'name' : name},
        {'$inc': {'like': 1}}
    )    
    
    return render_template('main.html')

@app.route('/detail/<name>')
def detail(name):
    info = list(db.find({'name' : name}))
    
    return render_template('detail.html', info=info[0])


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)