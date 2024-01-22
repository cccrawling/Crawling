from datetime import datetime
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from bs4 import BeautifulSoup
import requests
from crawling import crawling_active
client = MongoClient('localhost', 27017)
db = client.test.users

app = Flask(__name__)


@app.route('/crawling')
def crawling():
    df = crawling_active()
    cnt = 0
    records = df.to_dict(orient='records')
    for record in records:
        db_bool = db.find_one({'name' : record['name']})
        if db_bool is None:
            db.insert_one(record)
            cnt += 1
            print('1')
    return jsonify({'result' : cnt})
    
    

# 메인 페이지 완료
@app.route('/')
def home():
    all_list = list(db.find({'trash' : 0}))

    return render_template('main.html', movies=all_list)


@app.route('/trashList')
def trashList():
    all_list = list(db.find({'trash' : 1}))

    return render_template('trash.html', movies=all_list)



# 메인페이지 버튼 동작
@app.route('/like', methods=['POST'])
def like():
    name = dict(request.form)['name']
    db.update_one(
        {'name' : name},
        {'$inc': {'likes': 1}}
    )    
    
    return render_template('main.html')


@app.route('/trash', methods=['POST'])
def trash():
    name = dict(request.form)['name']
    db.update_many(
        {'name' : name},
        {'$set': {'trash': 1}}
    )
        
    return render_template('main.html')





# 휴지통 페이지 버튼 동작
@app.route('/delete', methods=['POST'])
def delete():
    name = dict(request.form)['name']
    db.delete_one({'name' : name})
    
    all_list = list(db.find({'trash' : 1}))
    
    return render_template('trash.html', movies=all_list)

@app.route('/back', methods=['POST'])
def back():
    name = dict(request.form)['name']
    db.update_one(
        {'name' : name},
        {'$set': {'trash': 0}}
    )
    
    all_list = list(db.find({'trash' : 1}))
    
    return render_template('trash.html', movies=all_list)





# 정렬 완료
@app.route('/<sort_type>')
def sortBy(sort_type):
    all_list = list(db.find({'trash' : 0}))
    
    sorted_movies = sorted(all_list, key=lambda x: x[sort_type], reverse=True)
    return render_template('main.html', movies=sorted_movies)

@app.route('/trashList/<sort_types>')
def trashSortBy(sort_types):
    all_list = list(db.find({'trash' : 1}))
    print(sort_types)
    sorted_movies = sorted(all_list, key=lambda x: x[sort_types], reverse=True)
    return render_template('trash.html', movies=sorted_movies)


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
    
