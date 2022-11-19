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
    res = questions.find({'topic': topic, "assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})
    for i in res:
        element_id = i['_id']
        task = i['original']
        questions.update_one({'_id': element_id}, {'$pull': {"assigned_to": username}})
    return 'Removed %s from %s' % (topic, username)


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello teacher! ✨")


def reply(update: Update, context: CallbackContext):
    command = update.message.text
    pattern_matcher = re.findall('[Ss]tats [A-z_]+', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        username = pattern[1]
        res = user_stats(username)
        return update.message.reply_text(res)
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
        lang = detect(context.chat_data.get('text', "English"))
        if lang not in ['en', 'ko']:
            lang = "en"
        query = {
            "topic": "",
            "task": context.chat_data['translation'],
            "original": context.chat_data['text'],
            "modified_original": context.chat_data['translation'],
            "max_attempts": 3,
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
        update.message.reply_text(f"Inserted {str(query)}")
        context.chat_data['step'] = 0
        return

def add(update: Update, context: CallbackContext):
    context.chat_data['step'] = 0
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
    updater.dispatcher.add_handler(MessageHandler(Filters.text, reply))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
