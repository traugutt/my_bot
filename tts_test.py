import requests
import json
import time

def generate_hebrew_audio():
    url = 'https://api.narakeet.com/text-to-speech/mp3?voice=lior'

    headers = {'x-api-key': 'Ha7pORFOiy2Z1hqL35AIb5A7qRB6erfvayGk6jWj', 'Content-Type': 'text/plain'}

    text = 'המשפחה איננה קטנה.'
    encoded_text = text.encode('utf-8')
    data = {'data': text}

    response = requests.post(url, headers=headers, data=encoded_text)
    status_url = json.loads(response.text)['statusUrl']


    succeeded = False
    url = None
    while not succeeded:
        time.sleep(0.5)
        polling_url = requests.get(status_url).text
        get_url = json.loads(polling_url).get('result', None)
        if get_url:
            succeeded = True
            url = get_url

    return url
