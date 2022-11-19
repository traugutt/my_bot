# -*- coding: utf-8 -*-
#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that uses inline keyboards. For an in-depth explanation, check out
 https://git.io/JOmFw.
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters
import datetime
from navertts import NaverTTS
import uuid
from pymongo import MongoClient


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


def start(update: Update, context: CallbackContext):
    username = update.message.chat.username
    total = questions.count_documents({"assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})

    if not total:
        message_reply_text = 'There\'s no homework for you to do at the moment. ' \
                             'Press /start to check for homework at a later time.'
    else:
        message_reply_text = f'Welcome, you have {str(total)} questions left to answer. ' \
                             f'Ready to do your homework? Type in "Y or y" to proceed.'
    
    # keyboard = [
    # [
    #     KeyboardButton("Begin", callback_data='1')
    # ],
    # [
    #     KeyboardButton("/stop", callback_data='/stop')
    # ]
    # ]

    # reply_markup = ReplyKeyboardMarkup(keyboard)
    # update.message.reply_text(message_reply_text, reply_markup=reply_markup)
    update.message.reply_text(message_reply_text)


def check_answer(correct_answer, provided_answer):
    if type(correct_answer) == list:
        if provided_answer in correct_answer:
            return True
    elif type(correct_answer) == str:
        print(f'correct answer: {correct_answer}')
        print(f'provided answer: {provided_answer}')
    if provided_answer == correct_answer:
        return True
    else:
        return False


def create_tts(text, lang, username):
    tts = NaverTTS(text, lang=lang)
    text = uuid.uuid4()
    mp3_title = str(text) + '.mp3'
    tts.save('bot_audio/' + mp3_title)
    print('audio saved')
    return mp3_title


def reply(update: Update, context: CallbackContext):

    print(datetime.datetime.now())
    username = update.message.chat.username
    previous_answer = update.message.text
    if '’' in previous_answer:
        res = ''
        split_chars = list(previous_answer)
        for char in split_chars:
            if char == '’':
                char = '\''
            res += char
        previous_answer = res
    print(f'previous_answer: {previous_answer}')

    if previous_answer.lower() == 'y':
        print(previous_answer)

        question = questions.find_one({"assigned_to": {"$in": [username]},
                                       "completed_by": {"$nin": [username]}})

        if not bool(question):
            update.message.reply_text('There\'s no homework for you to do at the moment. '
                                      'Press /start to check for homework at a later time.')
            return

        task_text = question['modified_original']
        correct_answer = question['original']
        element_id = question['_id']
        task_line = question['task']

        is_answered = answers.find_one({'question_id': element_id, 'username': username})

        if bool(is_answered):
            answers.update_one({'question_id': element_id, 'username': username},
                               {'$set': {'time': datetime.datetime.utcnow()}})
        else:
            answers.insert_one({'question_id': element_id,
                                'username': username,
                                'correct_answer': correct_answer,
                                'time': datetime.datetime.utcnow(),
                                'number_of_tries': 0,
                                'number_of_tries_historic': 0,
                                'number_of_times_answered': 0})

        audio = question.get('audio', None)
        if audio:
            lang = question['lang']
            title = create_tts(correct_answer, lang, username)
            path_to_file = 'bot_audio/' + title
            update.message.reply_text(task_line)
            context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(path_to_file, 'rb'))
        elif 'http' in audio:
            update.message.reply_text(task_line)
            context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio)
        else:
            update.message.reply_text(task_line)
            update.message.reply_text(task_text)

    else:
        previous_questions_raw = answers.find({'username': username}).sort([('time', -1)])
        previous_questions_sorted = []

        for question in previous_questions_raw:
            previous_questions_sorted.append(question)

        previous_question = previous_questions_sorted[0]
        element_id = previous_question['_id']
        correct_previous = previous_question['correct_answer']

        print(correct_previous)
        element_id = previous_question['question_id']
        print(element_id)
        print(username)
        is_case_sensitive = questions.find_one({'_id': element_id}).get('case_sensitive', False)

        if not is_case_sensitive:
            previous_answer = previous_answer.lower()
            correct_previous = correct_previous.lower()

        is_correct = check_answer(correct_previous, previous_answer)

        if is_correct:
            questions.update_one({'_id': element_id}, {'$push': {"completed_by": username}})
            question = questions.find_one({"assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})
            answers.update_one(
                {'question_id': element_id, 'username': username},
                {'$inc': {'number_of_times_answered': 1}})
            answers.update_one(
                {'question_id': element_id, 'username': username},
                {'$set': {'time': datetime.datetime.utcnow()}})
            if not question:
                update.message.reply_text('Congrats! You did all your homework! '
                                          'Press /start to check for new homework at a later time.')
            else:

                print(question)
                task_line = question['task']
                task_text = question['modified_original']
                correct_answer = question['original']
                element_id = question['_id']
                is_answered = answers.find_one({'question_id': element_id, 'username': username})

                if is_answered:
                    answers.update_one({'question_id': element_id, 'username': username},
                                       {'$set': {'time': datetime.datetime.utcnow()}})
                else:
                    answers.insert_one({'question_id': element_id,
                                        'username': username,
                                        'correct_answer': correct_answer,
                                        'time': datetime.datetime.utcnow(),
                                        'number_of_tries': 0,
                                        'number_of_tries_historic': 0,
                                        'number_of_times_answered': 0})

                audio = question.get('audio', None)
                if audio:
                    lang = question['lang']
                    title = create_tts(correct_answer, lang)
                    path_to_file = 'bot_audio/' + title
                    update.message.reply_text(task_line)
                    context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(path_to_file, 'rb'))
                elif 'http' in audio:
                    update.message.reply_text(task_line)
                    context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio)
                else:
                    update.message.reply_text(task_line)
                    update.message.reply_text(task_text)
        else:
            num_of_tries = answers.find_one({'question_id': element_id, 'username': username})['number_of_tries']
            max_attempts = 3
            if num_of_tries < max_attempts:
                update.message.reply_text('Please try again.')
                answers.update_one({'question_id': element_id, 'username': username},
                                   {"$inc": {'number_of_tries': 1, 'number_of_tries_historic': 1}})
            else:
                correct_answer = questions.find_one({'_id': element_id})['original']

                answer_merger = ''
                if type(correct_answer) == list:
                    answer_merger = '\' or \''.join(correct_answer)
                    correct_answer = answer_merger
                
                print(answer_merger)

                explanation = questions.find_one({'_id': element_id}).get('explanation', None)
                if explanation:
                    update.message.reply_text(f'The answer is \'{correct_answer}\' \n\n{explanation}\n\n'
                                              f'Please type in the correct answer to proceed.')
                else:
                    update.message.reply_text(f'The answer is \'{correct_answer}\' \n\n'
                                              f'Please type in the correct answer to proceed.')

                answers.update_one({'question_id': element_id, 'username': username}, {"$set": {'number_of_tries': 0}})

def today(update: Update, context):
    username = update.message.chat.username
    query = {'assigned_to':{"$in":[username]}, "created": str(datetime.date.today())}
    res = questions.find(query)
    data = ''
    for entry in res:
        data += f"{entry['original']} - {entry['modified_original']}\n"
    return update.message.reply_text(data)
def help_command(update: Update, context):
    """Displays info on how to use the bot."""
    update.message.reply_text("Use /start to test this bot.")


def stop(update: Update, context):
    update.message.reply_text("Use /start to start again.")


def main() -> None:
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater("1896847698:AAFtp1t66yDx-z8-H2m2_d_lj2eC59Q0ay4", use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('today', today))
    updater.dispatcher.add_error_handler(start)
    updater.dispatcher.add_handler(MessageHandler(Filters.text, reply))
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()

# daemon = Daemonize(app="studybot", pid=pid, action=main)
# daemon.start()


