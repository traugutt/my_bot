import logging
from telegram import Update
from telegram.ext import CallbackContext, Updater, CommandHandler, MessageHandler
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
from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, filters
from bson import ObjectId
from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

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


def generate_german_audio(text):
    url = 'https://api.narakeet.com/text-to-speech/mp3?voice=monika'

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
    update = update
    day = 1000 * 60 * 1440
    three_days = day * 3
    six_days = three_days * 2
    twelve_days = six_days * 2
    month_ish = twelve_days * 3
    two_months = twelve_days * 6
    three_months = two_months + month_ish
    intervals = [three_days, six_days, twelve_days, month_ish, two_months, three_months]
    attempts_count = [1, 2, 3, 4, 5, 6]
    username = update.effective_chat.username
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


async def start(update: Update, context: CallbackContext):
    apply_spaced_repetition(update)
    username = update.effective_chat.username

    total = questions.count_documents({"assigned_to": {"$in": [username]}, "completed_by": {"$nin": [username]}})

    keyboard_start_homework = [
        [
            InlineKeyboardButton("Let's do it! 💪", callback_data="y"),
        ]
    ]

    if not total:
        message_reply_text = 'There\'s no homework for you to do at the moment. 😌 ' \
                             'Press /start to check for homework at a later time. Press /add to add terms.'
        reply_markup = InlineKeyboardMarkup([])
    else:
        message_reply_text = f'Welcome, you have {str(total)} questions left to answer. ' \
                             f'Ready to do your homework?'
        reply_markup = InlineKeyboardMarkup(keyboard_start_homework)

    context.chat_data['step'] = -1






    await update.message.reply_text(message_reply_text, reply_markup = reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery



async def add(update: Update, context: CallbackContext):
    context.chat_data['step'] = 0
    await update.message.reply_text("Please add term")


async def check_answer(correct_answer, provided_answer):
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


async def add_item(update, context):
    command = update.message.text
    username = update.effective_chat.username
    if context.chat_data.get('step', None) == 0:
        context.chat_data['text'] = command
        context.chat_data['step'] = 1
        return await update.message.reply_text("Please insert translation")
    if context.chat_data.get('step', None) == 1:
        context.chat_data['translation'] = command
        lang = detect(context.chat_data.get('text', "English"))
        if lang not in ['en', 'ko', 'he', 'iw', 'de']:
            lang = "en"
        if username == "traugutt":
            lang = "de"
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
        await update.message.reply_text(f"Inserted:\n {str(query['original'])} - {str(query['modified_original'])}")
        context.chat_data['step'] = -1
        return


async def generate_audio(audio, lang, question, correct_answer, update: Update, task_line, task_text, context):

    keyboard_start_homework = [
        [
            InlineKeyboardButton("Remove entry", callback_data="REMOVE"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard_start_homework)

    if update.effective_user.username == "traugutt":
        lang = "de"
    if audio and lang in ['en', 'ko']:
        lang = question['lang']
        title = create_tts(correct_answer, lang)
        path_to_file = 'bot_audio/' + title
        if not update.message:
            await update.callback_query.message.edit_text(task_line, reply_markup=reply_markup)
        else:
            await update.message.reply_text(task_line, reply_markup=reply_markup)
        await context.bot.send_audio(chat_id=update.effective_chat.id, audio=open(path_to_file, 'rb'))
    elif audio and lang in ['he', 'iw']:
        if not update.message:
            await update.callback_query.message.edit_text(task_line)
        else:
            await update.message.reply_text(task_line, reply_markup=reply_markup)
        await context.bot.send_audio(chat_id=update.effective_chat.id,
                               audio=generate_hebrew_audio(correct_answer))
    elif audio and lang in ['de']:
        if not update.message:
            await update.callback_query.message.edit_text(task_line, reply_markup=reply_markup)
        else:
            await update.message.reply_text(task_line, reply_markup=reply_markup)
        await context.bot.send_audio(chat_id=update.effective_chat.id,
                               audio=generate_german_audio(correct_answer), title='play_me', filename='play_me')
    elif audio and 'http' in audio:
        if not update.message:
            await update.callback_query.message.edit_text(task_line, reply_markup=reply_markup)
        else:
            await update.message.reply_text(task_line, reply_markup=reply_markup)
        await context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio, title='play_me')
    else:
        if not update.message:
            await update.callback_query.message.edit_text(task_line, reply_markup=reply_markup)
        else:
            await update.message.reply_text(task_line, reply_markup=reply_markup)
            await update.message.reply_text(task_text)


async def reply(update: Update, context: CallbackContext):
    apply_spaced_repetition(update)
    username = update.effective_chat.username
    previous_answer = update.callback_query.data if not update.message else update.message.text

    if previous_answer == 'REMOVE':
        questions.delete_many({'_id': ObjectId(context.chat_data['current_question_id'])})
        answers.delete_many({'question_id': ObjectId(context.chat_data['current_question_id'])})

        await update.callback_query.message.edit_text('Removed entry.')

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
        context.chat_data['current_question_id'] = question.get('_id')
        if not bool(question):
            await update.message.reply_text('There\'s no homework for you to do at the moment. '
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
        audio = True if question.get('audio', None) == "yes" else False
        lang = question.get('lang', None)
        await generate_audio(audio=audio, lang=lang, update=update, context=context, task_line=task_line, task_text=task_text, question=question, correct_answer=correct_answer)
    elif context.chat_data.get('step', None) in [0, 1]:
        await add_item(update, context)
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

        is_correct = await check_answer(correct_previous, previous_answer)

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
                await update.message.reply_text('Congrats! You did all your homework! '
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

                audio = True if question.get('audio', None) == "yes" else False
                lang = question.get('lang', None)
                await generate_audio(audio=audio, lang=lang, update=update, context=context, task_line=task_line,
                               task_text=task_text, question=question, correct_answer=correct_answer)
        else:
            num_of_tries = answers.find_one({'question_id': element_id, 'username': username})['number_of_tries']
            max_attempts = 1
            if num_of_tries < max_attempts:
                await update.message.reply_text('Please try again.')
                answers.update_one({'question_id': element_id, 'username': username},
                                   {"$inc": {'number_of_tries': 1, 'number_of_tries_historic': 1}})
            else:
                correct_answer = questions.find_one({'_id': element_id})['original']
                if type(correct_answer) == list:
                    answer_merger = '\' or \''.join(correct_answer)
                    correct_answer = answer_merger

                explanation = questions.find_one({'_id': element_id}).get('explanation', None)
                if explanation:
                    await update.message.reply_text(f'The answer is \'{correct_answer}\' \n\n{explanation}\n\n'
                                              f'Please type in the correct answer to proceed.')
                else:
                    await update.message.reply_text(f'The answer is \'{correct_answer}\' \n\n'
                                              f'Please type in the correct answer to proceed.')

                answers.update_one({'question_id': element_id, 'username': username}, {"$set": {'number_of_tries': 0}})


async def today(update: Update, context: CallbackContext):
    username = update.effective_chat.username
    query = {'assigned_to': {"$in": [username]}, "created": str(datetime.date.today())}
    res = questions.find(query)
    data = ''
    counter = 1
    if res:
        for entry in res:
            data += f"{counter}. {entry['original']} - {entry['modified_original']}\n"
            counter += 1
        return await update.message.reply_text(data)
    else:
        return await update.message.reply_text("No words were added today 😌.")


async def help_command(update: Update):
    """Displays info on how to use the bot."""
    await update.message.reply_text("Use /start to test this bot.")


async def stop(update: Update):
    await update.message.reply_text("Use /start to start again.")


def main() -> None:
    """Run the bot."""
    TOKEN = os.getenv('TELEGRAM_API_KEY')
    #updater = Updater("1896847698:AAFtp1t66yDx-z8-H2m2_d_lj2eC59Q0ay4", use_context=True)
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('today', today))
    application.add_handler(CallbackQueryHandler(reply))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    application.add_handler(CommandHandler('add', add))
    #updater.dispatcher.add_error_handler(start)
    application.run_polling()


if __name__ == '__main__':
    main()
