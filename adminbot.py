# -*- coding: utf-8 -*-
#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that uses inline keyboards. For an in-depth explanation, check out
 https://git.io/JOmFw.
"""
import logging
import time
import re
# from daemonize import Daemonize

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters
import datetime

# from homework_bot.__init__ import app
# from mindmeld.components.dialogue import Conversation

from pymongo import MongoClient
# pid = "/tmp/studybot.pid"

client = MongoClient('mongodb://localhost:27017/')
db = client.students
answers = db['answers']
questions = db['bot_data']


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# def start(update, context):
#     context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

#conversations = {}

def assign_n_tasks(topic, username):
    res = questions.find({'topic':topic, "assigned_to":{"$nin":[username]},"completed_by":{"$nin":[username]}})
    # res = collection.findMany({"assigned_to":{"$nin":[username]},"completed_by":{"$nin":[username]}})
    counter = 0
    for i in res:
        element_id = i['_id']
        task = i['original']
        questions.update_one({'_id':element_id},{'$push':{"assigned_to":username}})
        counter+=1
    return 'Assigned %s from %s to %s' % (counter, topic, username)


def user_stats(username):
    topics = {}
    assigned_not_completed_count = 0
    assigned_not_completed = questions.find({"assigned_to":{"$in":[username]},"completed_by":{"$nin":[username]}})

    for i in assigned_not_completed:
        assigned_not_completed_count +=1
        topic = i['topic']
        try:
            topics[topic]+=1
        except KeyError:
            topics[topic]=0

    print(topics)

    result = '%s has ' % (username) + str(assigned_not_completed_count) + ' tasks left to complete\nThe topic are:\n'
    for i in topics.keys():
        topic_stat = i + ' ' + str(topics[i]) + '\n'
        result+=topic_stat
    return result

def remove_tasks(topic, username):
    res = questions.find({'topic':topic, "assigned_to":{"$in":[username]},"completed_by":{"$nin":[username]}})
    for i in res:
        element_id = i['_id']
        task = i['original']
        questions.update_one({'_id':element_id},{'$pull':{"assigned_to":username}})
    return 'Removed %s from %s' % (topic, username)



def start(update: Update, context: CallbackContext):
    
    # total = questions.count_documents({"assigned_to":{"$in":[username]}, "completed_by":{"$nin":[username]}})

    update.message.reply_text("Hello teacher!")


def reply(update: Update, context: CallbackContext):
    print('hello')
    command = update.message.text
    pattern_matcher = re.findall('[A-z_0-9]+ to [A-z_0-9]+', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        topic = pattern[0]
        username = pattern[2]
        res = assign_n_tasks(topic, username)
        update.message.reply_text(res)

    pattern_matcher = re.findall('[Ss]tats [A-z_]+', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        username = pattern[1]
        res = user_stats(username)
        update.message.reply_text(res)


    pattern_matcher = re.findall('[Rr]emove [A-z_0-9]+ from [A-z_0-9]+', command)
    if len(pattern_matcher) >= 1:
        pattern = pattern_matcher[0]
        pattern = pattern.split(' ')
        topic = pattern[1]
        username = pattern[3]
        res = remove_tasks(topic, username)
        update.message.reply_text(res)


    pattern_matcher = re.findall('audio', command)
    if len(pattern_matcher) >= 1:
        context.bot.send_audio(chat_id=update.effective_chat.id, audio='https://www.goethe-verlag.com/book2/_alleima/_mp3/ES/x01.mp3')

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
    updater.dispatcher.add_handler(MessageHandler(Filters.text, reply))


    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()

# daemon = Daemonize(app="studybot", pid=pid, action=main)
# daemon.start()

