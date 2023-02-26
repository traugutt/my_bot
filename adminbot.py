import datetime
import logging
import re
import os
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters
from langdetect import detect
from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient('mongodb://localhost:27017/')
db = client.students
answers = db['answers']
questions = db['bot_data']


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

user = None

client = MongoClient('mongodb://localhost:27017/')
db = client.students
questions = db['bot_data']


def assign_n_tasks(topic, username):
    res = questions.find({'topic': topic, "assigned_to": {"$nin": [username]}, "completed_by": {"$nin": [username]}})
    counter = 0
    for i in res:
        element_id = i['_id']
        task = i['original']
        questions.update_one({'_id': element_id}, {'$push': {"assigned_to": username}})
        counter += 1
    return 'Assigned %s from %s to %s' % (counter, topic, username)


def user_stats(username):
    topics = {}
    assigned_not_completed_count = 0
    assigned_not_completed = questions.find({"assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})

    for i in assigned_not_completed:
        assigned_not_completed_count += 1

    result = '%s has ' % (username) + str(assigned_not_completed_count) + ' tasks left to complete'
    for i in topics.keys():
        topic_stat = i + ' ' + str(topics[i]) + '\n'
        result += topic_stat
    return result


def remove_tasks(topic, username):
    if not username:
        query = {'_id': ObjectId(topic)}
        res = questions.find_one(query)
        if res:
            questions.delete_one(query)
            return 'Removed %s' % (res['task'])
        else:
            return 'Sorry, didn\'t find it 😬'
    else:
        res = questions.find({'topic': topic, "assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})
        if not res:
            try:
                res = questions.find(
                    {'_id': ObjectId(topic), "assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})
                for i in res:
                    element_id = i['_id']
                    task = i['original']
                    questions.update_one({'_id': element_id}, {'$pull': {"assigned_to": username}})
                return 'Removed %s from %s' % (topic, username)
            except Exception:
                return 'Oh no! 😮️'


def remove_all(username):
        questions.delete_many({"assigned_to": {"$in": [username]}})
        res = questions.find_one({"assigned_to": {"$in": [username]}})
        if not res:
                return 'This slacker doesn\'t have any 😜'


def get_task_id(topic):
    res = questions.find({'task': topic})
    print({'task': topic})
    matches = ''
    for i in res:
        print(i)
        matches += f"id: {i['_id']} - topic: {i['topic']} text: {i['original']} task: {i['task']}"
    return matches


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello gorgeous! ✨\nThe commands are:\n'[Ss]tats [A-z_]+$'\n'[Aa]ssign [A-z_0-9-]+ to [A-z_]+$'\n'[Rr]emove [A-z_0-9-]+ from [A-z_]+$' (unassign all from topic or single id)\n'[Cc]lear [A-z_]+$'(unassign all tasks from user)\n'[Gg]et [A-z_0-9-]+$' (get db id for removal)\n'[Rr]emove [A-z_0-9-]+$' (remove entry from db by id)")


def reply(update: Update, context: CallbackContext):
    command = update.message.text
    pattern_matcher = re.findall('[Ss]tats [A-z_]+$', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        username = pattern[1]
        res = user_stats(username)
        return update.message.reply_text(res)
    pattern_matcher = re.findall('[Aa]ssign [A-z_0-9-]+ to [A-z_]+$', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        topic = pattern[1]
        username = pattern[3]
        res = assign_n_tasks(topic, username)
        return update.message.reply_text(res)
    pattern_matcher = re.findall('[Rr]emove [A-z_0-9-]+ from [A-z_]+$', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        topic = pattern[1]
        username = pattern[3]
        res = remove_tasks(topic, username)
        return update.message.reply_text(res)
    pattern_matcher = re.findall('[Cc]lear [A-z_]+$', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        username = pattern[1]
        res = remove_all(username)
        return update.message.reply_text(res)
    pattern_matcher = re.findall('[Gg]etid .+', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split('etid')
        topic = pattern[1].strip()
        print(topic)
        res = get_task_id(topic)
        print(res)
        if not res:
            res = "Not found, sorry 🥺"
        return update.message.reply_text(str(res))
    pattern_matcher = re.findall('[Rr]emove [A-z_0-9-]+$', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        topic = pattern[1]
        username = None
        res = remove_tasks(topic, username)
        return update.message.reply_text(res)
    if context.chat_data.get('batch_step', None) == 0:
        context.chat_data['username'] = command
        context.chat_data['batch_step'] = 1
        return update.message.reply_text("Please insert a bunch of stuff")
    if context.chat_data.get('step', None) == 0:
        context.chat_data['username'] = command
        context.chat_data['step'] = 1
        return update.message.reply_text("Please insert term")
    if context.chat_data.get('step', None) == 1:
        context.chat_data['text'] = command
        context.chat_data['step'] = 2
        return update.message.reply_text("Please insert translation")
    if context.chat_data.get('step', None) == 2:
        context.chat_data['translation'] = command
        try:
            lang = detect(context.chat_data.get('text', "English"))
            if lang not in ['en', 'ko', 'he', 'iw']:
                lang = "en"
        except Exception as e:
            lang = "en"
        query = {
            "topic": "",
            "task": context.chat_data['translation'],
            "original": context.chat_data['text'],
            "modified_original": context.chat_data['translation'],
            "max_attempts": 2,
            "audio": "yes",
            "lang": lang,
            "assigned_to": [
                context.chat_data['username']
            ],
            "completed_by": [
            ],
            "created": str(datetime.date.today())
        }
        questions.insert_one(query)
        update.message.reply_text(f"Inserted: {query.get('original')} - {query.get('task')}\nId: {query.get('_id')}")
        context.chat_data['step'] = 0
        return
    if context.chat_data.get('batch_step', None) == 1:
        items = command.split('\n')
        inserted = 'Inserted:\n'
        for item in items:
            text = item.split(' $ ')[0].strip()
            translation = item.split(' $ ')[1].strip()
            try:
                lang = detect(text)
                if lang not in ['en', 'ko', 'he', 'iw']:
                    lang = "en"
            except Exception as e:
                lang = "en"
            topic = f"{context.chat_data['username']}_{lang}_{datetime.date.today().isoformat()}"
            query = {
                "topic": topic,
                "task": translation,
                "original": text,
                "modified_original": translation,
                "max_attempts": 2,
                "audio": "yes",
                "lang": lang,
                "assigned_to": [
                    context.chat_data['username']
                ],
                "completed_by": [
                ],
                "created": str(datetime.date.today())
            }

            questions.insert_one(query)
            inserted += f"topic: {topic}\t {query.get('original')} - {query.get('task')}\tid: {query.get('_id')}\tlang: {lang}\n"
        update.message.reply_text(inserted)
        context.chat_data['batch_step'] = 0
        return


def add(update: Update, context: CallbackContext):
    context.chat_data['step'] = 0
    update.message.reply_text("Please add username")


def batch(update: Update, context: CallbackContext):
    context.chat_data['batch_step'] = 0
    update.message.reply_text("Please add username")


def audio(update: Update, context: CallbackContext):
    context.bot.send_audio(chat_id=update.effective_chat.id, audio=open('./001-poklon-razogrev.mp3', 'rb'))


def help_command(update: Update, context):
    """Displays info on how to use the bot."""
    update.message.reply_text("Use /start to test this bot.")


def stop(update: Update, context):
    update.message.reply_text("Use /start to start again.")


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater("1952343630:AAFrbnOJ7-c7a4tjGoPqxbs7ln2kInndY-k", use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    #updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('audio', audio))
    updater.dispatcher.add_handler(CommandHandler('add', add))
    updater.dispatcher.add_handler(CommandHandler('batch', batch))
    updater.dispatcher.add_error_handler(start)
    updater.dispatcher.add_handler(MessageHandler(Filters.text, reply))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
