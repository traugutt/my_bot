from pymongo import MongoClient
import sys
import os

csv_file = sys.argv[1]
print(csv_file)

os.system('mongoimport --host=127.0.0.1 -d students -c bot_data --type csv --file '+ csv_file +' --headerline')

client = MongoClient('mongodb://localhost:27017/')
db = client.students
questions = db['bot_data']
topic = csv_file.split('.csv')[0]
print(topic)
res = questions.find({'topic':topic})

for i in res:
    element_id = i['_id']
    questions.update_one({'_id':element_id},{"$set":{"assigned_to":[], "completed_by":[], "case_sensitive":False}})
