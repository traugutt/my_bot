from pymongo import MongoClient
import sys


client = MongoClient('mongodb://localhost:27017/')
db = client.students
questions = db['bot_data']
topic = 'maxim_11_01_22'
username = 'Maxon_Stenduper'
limit = 40
res = questions.find({'topic':topic})
#res = questions.find({'topic':topic, "assigned_to":{"$nin":[username]},"completed_by":{"$nin":[username]}}, limit=limit)
# res = collection.findMany({"assigned_to":{"$nin":[username]},"completed_by":{"$nin":[username]}})
for i in res:
    element_id = i['_id']
    questions.update_one({'_id':element_id},{"$set":{"assigned_to":['traugutt'], "completed_by":[], "case_sensitive":False}})
