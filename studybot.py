import logging
from telegram import Update
from telegram.ext import CallbackContext, Updater, CommandHandler, MessageHandler, Filters
import datetime
from navertts import NaverTTS
import uuid
from pymongo import MongoClient
from langdetect import detect
import requests
import json
import time
import os
from bson.objectid import ObjectId
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes

client = MongoClient('mongodb://localhost:27017/')
db = client.students
answers = db['answers']
questions = db['bot_data']


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def generate_hebrew_audio(text):
    url = 'https://api.narakeet.com/text-to-speech/mp3?voice=lior'

    headers = {'x-api-key': 'Ha7pORFOiy2Z1hqL35AIb5A7qRB6erfvayGk6jWj', 'Content-Type': 'text/plain'}

    text = text
    encoded_text = text.encode('utf-8')

    response = requests.post(url, headers=headers, data=encoded_text)
    status_url = json.loads(response.text)['statusUrl']

    succeeded = False
    url = None
    while not succeeded:
        polling_url = requests.get(status_url).text
        get_url = json.loads(polling_url).get('result', None)
        if get_url:
            succeeded = True
            url = get_url

    return url


def apply_spaced_repetition(update):
    day = 1000 * 60 * 1440
    three_days = day * 3
    six_days = three_days * 2
    twelve_days = six_days * 2
    month_ish = twelve_days * 3
    two_months = twelve_days * 6
    intervals = [day, three_days, six_days, twelve_days, month_ish, two_months]
    attempts_count = [3, 4, 5, 6, 7, 8]
    username = update.message.chat.username
    answer_attempts = answers.find({'username': username})
    for attempt in answer_attempts:
        if attempt.get('number_of_times_answered', None) < 3:
            q_id = attempt.get('question_id', None)
            question = questions.find_one({'_id': ObjectId(q_id)})
            if question:
                questions.update_one({'_id': ObjectId(q_id)}, {'$pull': {'completed_by': username}})
        else:
            for interval, attempt_count in zip(intervals, attempts_count):
                if attempt.get('number_of_times_answered', None) == attempt_count and \
                        int(time.time()) - attempt.get('answered_last', None) > interval:
                    q_id = attempt.get('question_id', None)
                    question = questions.find_one({'_id': ObjectId(q_id)})
                    if question:
                        questions.update_one({'_id': ObjectId(q_id)}, {'$pull': {'completed_by': username}})


def start(update: Update, context: CallbackContext):
    apply_spaced_repetition(update)
    username = update.message.chat.username

    total = questions.count_documents({"assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})

    if not total:
        message_reply_text = 'There\'s no homework for you to do at the moment. 😌 ' \
                             'Press /start to check for homework at a later time.'
    else:
        message_reply_text = f'Welcome, you have {str(total)} questions left to answer. ' \
                             f'Ready to do your homework? Type in "y" or "Y" to proceed. Use /add to add terms.'
    context.chat_data['step'] = -1
    update.message.reply_text(message_reply_text)


def add(update: Update, context: CallbackContext):
    context.chat_data['step'] = 0
    update.message.reply_text("Please add term")

def check_answer(correct_answer, provided_answer):
    if type(correct_answer) == list:
        if provided_answer in correct_answer:
            return True
    if provided_answer == correct_answer:
        return True
    else:
        return False


def create_tts(text, lang):
    tts = NaverTTS(text, lang=lang)
    text = uuid.uuid4()
    mp3_title = str(text) + '.mp3'
    tts.save('bot_audio/' + mp3_title)
    return mp3_title


def add_item(update, context):
    command = update.message.text
    username = update.message.chat.username
    if context.chat_data.get('step', None) == 0:
        context.chat_data['text'] = command
        context.chat_data['step'] = 1
        return update.message.reply_text("Please insert translation")
    if context.chat_data.get('step', None) == 1:
        context.chat_data['translation'] = command
        lang = detect(context.chat_data.get('text', "English"))
        if lang not in ['en', 'ko', 'he', 'iw']:
            lang = "en"
        query = {
            "topic": "",
            "task": context.chat_data['translation'],
            "original": context.chat_data['text'],
            "modified_original": context.chat_data['translation'],
            "max_attempts": 1,
            "audio": "yes",
            "lang": lang,
            "assigned_to": [
                username
            ],
            "completed_by": [
            ],
            "created": str(datetime.date.today())
        }
        questions.insert_one(query)
        update.message.reply_text(f"Inserted {str(query)}")
        context.chat_data['step'] = -1
        return


def reply(update: Update, context: CallbackContext):
    #apply_spaced_repetition(update)
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

    if previous_answer.lower() == 'y':
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
                               {'$set': {'time': datetime.datetime.utcnow(), 'answered_last': int(time.time())}})

        else:
            answers.insert_one({'question_id': element_id,
                                'username': username,
                                'correct_answer': correct_answer,
                                'time': datetime.datetime.utcnow(),
                                'number_of_tries': 0,
                                'number_of_tries_historic': 0,
                                'number_of_times_answered': 0,
                                'answered_last': int(time.time())
                                })
        audio = question.get('audio', None)
        lang = question.get('lang', None)
        if audio and lang in ['en', 'ko']:
            lang = question['lang']
            directory = 'bot_audio/'
            for f in os.listdir(directory):
                os.remove(os.path.join(directory, f))
            title = create_tts(correct_answer, lang)
            path_to_file = 'bot_audio/' + title
            update.message.reply_text(task_line)
            context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(path_to_file, 'rb'))
        elif audio and lang in ['he', 'iw']:
            update.message.reply_text(task_line)
            context.bot.send_audio(chat_id=update.effective_chat.id, audio=generate_hebrew_audio(correct_answer))
        elif 'http' in audio:
            update.message.reply_text(task_line)
            context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio)
        else:
            update.message.reply_text(task_line)
            update.message.reply_text(task_text)
    elif context.chat_data.get('step', None) in [0, 1]:
        add_item(update, context)
    else:
        previous_questions_raw = answers.find({'username': username}).sort([('time', -1)])
        previous_questions_sorted = []

        for question in previous_questions_raw:
            previous_questions_sorted.append(question)

        previous_question = previous_questions_sorted[0]
        correct_previous = previous_question['correct_answer']

        element_id = previous_question['question_id']
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

                task_line = question['task']
                task_text = question['modified_original']
                correct_answer = question['original']
                element_id = question['_id']
                is_answered = answers.find_one({'question_id': element_id, 'username': username})

                if bool(is_answered):
                    answers.update_one({'question_id': element_id, 'username': username},
                                       {'$set': {'time': datetime.datetime.utcnow(),
                                                 'answered_last': int(time.time())}})

                else:
                    answers.insert_one({'question_id': element_id,
                                        'username': username,
                                        'correct_answer': correct_answer,
                                        'time': datetime.datetime.utcnow(),
                                        'number_of_tries': 0,
                                        'number_of_tries_historic': 0,
                                        'number_of_times_answered': 0,
                                        'answered_last': int(time.time())
                                        })

                audio = question.get('audio', None)
                lang = question.get('lang', None)
                if audio and lang in ['en', 'ko']:
                    lang = question['lang']
                    title = create_tts(correct_answer, lang)
                    path_to_file = 'bot_audio/' + title
                    update.message.reply_text(task_line)
                    context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(path_to_file, 'rb'))
                elif audio and lang in ['he', 'iw']:
                    update.message.reply_text(task_line)
                    context.bot.send_audio(chat_id=update.effective_chat.id,
                                           audio=generate_hebrew_audio(correct_answer))
                elif 'http' in audio:
                    update.message.reply_text(task_line)
                    context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio)
                else:
                    update.message.reply_text(task_line)
                    update.message.reply_text(task_text)
        else:
            num_of_tries = answers.find_one({'question_id': element_id, 'username': username})['number_of_tries']
            max_attempts = 1
            if num_of_tries < max_attempts:
                update.message.reply_text('Please try again.')
                answers.update_one({'question_id': element_id, 'username': username},
                                   {"$inc": {'number_of_tries': 1, 'number_of_tries_historic': 1}})
            else:
                correct_answer = questions.find_one({'_id': element_id})['original']
                if type(correct_answer) == list:
                    answer_merger = '\' or \''.join(correct_answer)
                    correct_answer = answer_merger

                explanation = questions.find_one({'_id': element_id}).get('explanation', None)
                if explanation:
                    update.message.reply_text(f'The answer is \'{correct_answer}\' \n\n{explanation}\n\n'
                                              f'Please type in the correct answer to proceed.')
                else:
                    update.message.reply_text(f'The answer is \'{correct_answer}\' \n\n'
                                              f'Please type in the correct answer to proceed.')

                answers.update_one({'question_id': element_id, 'username': username}, {"$set": {'number_of_tries': 0}})


def today(update: Update, context: CallbackContext):
    username = update.message.chat.username
    query = {'assigned_to': {"$in": [username]}, "created": str(datetime.date.today())}
    res = questions.find(query)
    data = ''
    counter = 1
    if res:
        for entry in res:
            data += f"{counter}. {entry['original']} - {entry['modified_original']}\n"
            counter += 1
        return update.message.reply_text(data)
    else:
        return update.message.reply_text("No words were added today 😌.")


def help_command(update: Update):
    """Displays info on how to use the bot."""
    update.message.reply_text("Use /start to test this bot.")


def stop(update: Update):
    update.message.reply_text("Use /start to start again.")


def main() -> None:
    """Run the bot."""
    updater = Updater("1896847698:AAFtp1t66yDx-z8-H2m2_d_lj2eC59Q0ay4", use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.dispatcher.add_handler(CommandHandler('today', today))
    updater.dispatcher.add_handler(CommandHandler('add', add))
    updater.dispatcher.add_error_handler(start)
    updater.dispatcher.add_handler(MessageHandler(Filters.text, reply))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
