# Import the SentimentIntensityAnalyzer class
from hashlib import sha256
import json
import argparse
from prettytable import PrettyTable, ALL
from tqdm import tqdm
import json
import os

def sentiment(result, modelName='NLTK', skip=None, **kwargs):
    if modelName == 'NLTK':
        return sentimentNLTK(result, skip, **kwargs)
    elif modelName == 'LLM':
        return sentimentLLM(result, skip, **kwargs)
    else:
        return sentimentTrans(result, skip, **kwargs)


def sentimentNLTK(result, skip, **kwargs):
    raise RuntimeError('sentimentNLTK is deprecated')
    try:
        import nltk
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        from nltk.stem import WordNetLemmatizer
    except ModuleNotFoundError as e:
        print('nltk module not found. Please install with pip. Abort')
        raise e
    from nltk.sentiment import SentimentIntensityAnalyzer
    nltk.download('all')
    nltk.download('vader_lexicon')

    # create preprocess_text function
    def preprocess_text(text):
        # Tokenize the text
        tokens = word_tokenize(text.lower())
    
        # Remove stop words
        filtered_tokens = [token for token in tokens if token not in stopwords.words('english')]
    
        # Lemmatize the tokens
        lemmatizer = WordNetLemmatizer()
        lemmatized_tokens = [lemmatizer.lemmatize(token) for token in filtered_tokens]
    
        # Join the tokens back into a string
        processed_text = ' '.join(lemmatized_tokens)
        return processed_text

    # Create an instance of the class
    sia = SentimentIntensityAnalyzer()
    negRuns = []
    negHistory = []
    negSummary = []
    for runId, content in result.items():
        if runId in skip:
            continue
        scores = sia.polarity_scores(preprocess_text(' '.join([line for _, line in content.message.items()])))
        if scores['neg'] > 0:
            negRuns.append(runId)

        if content.history is None:
            scores = {'neg': 1}
        else:
            runStart = content.runStart
            history = ('\n').join([entry for time, entry in content.history.items() if time > runStart and not entry.startswith('Summary Report')])
            scores = sia.polarity_scores(preprocess_text(history))
        if scores['neg'] > 0:
            negHistory.append(runId)

        if content.summary is None:
            scores = {'neg': 1}
        else:
            txts = content.summary.split('run number | status')
            txts = txts[0] # if the run number doesn't exist, we just use the entire thing
            scores = sia.polarity_scores(preprocess_text(txts))
        if scores['neg'] > 0:
            negSummary.append(runId)
    return negRuns, negHistory, negSummary, reasons


def sentimentLLM(result, skip, threshold=0, settings_json='LLM_settings.json', forceAI=False, debug=False, **kwargs):
    # load settings of LLM from json
    with open(settings_json) as f:
        settings = json.load(f)

    from llama_cpp import Llama
    print('Loading LLM model.')
    #llm = Llama(model_path=r'D:\Download\text-generation-webui-main\text-generation-webui-main\models\mistral-7b-instruct-v0.2.Q5_K_M.gguf', n_gpu_layers=512, n_ctx=512, verbose=False)
    llm = Llama(model_path=settings['model'], n_gpu_layers=settings['n_gpu_layers'], n_ctx=settings['n_ctx'], verbose=settings['verbose'], seed=settings['seed'])

    stop_tokens = settings['stop'] if 'stop' in settings else []


    def askLLMIsRunGood(runID, content):
        # ask LLM to give explicit result
        # look for the following phrase
        badrunKW = 'BAD BAD BAD'
        goodrunKW = 'GOOD GOOD GOOD'

        messages = [
                #{"role": "system", "content": "I am an assistant who help users identify bad runs from runLog. I will follow user's instruction truthfully and accurately. "},
                {
                    "role": "user",
                    "content": settings['promptFormat'].format(runID=runID, content=content, badrunKW=badrunKW, goodrunKW=goodrunKW) 
                }
            ]

        if debug:
            print('[DEBUG] User:')
            print(messages[0]['content'])

        response = llm.create_chat_completion(messages=messages, temperature=settings['temperature'], stop=stop_tokens)
        if debug:
            print('[DEBUG] AI:')
            print(response['choices'][0]['message']['content'])
        reason = response['choices'][0]['message']['content'].replace('\n', ' ')
        # if both good phrase and bad phrase are mentioned, prompt LLM for more clarification
        if not (badrunKW in reason and goodrunKW in reason):
            if badrunKW in reason:
                return False, reason
            elif goodrunKW in reason:
                return True, reason


        # if LLM fails to follow direction, we will prompt it repeatedly until it gives us the answer, or if we run out of time and declare the run bad
        messages.append({"role": "system", "content": reason})
        messages.append({'role': 'user', 'content': settings['reprompt'].format(badrunKW=badrunKW, goodrunKW=goodrunKW)})
        for i in range(settings['maxPromptAttempt']):
            response = llm.create_chat_completion(messages=messages, stop=stop_tokens)
            response = response['choices'][0]['message']['content']
            if not (badrunKW in response and goodrunKW in response):
                if badrunKW in response:
                    return False, reason
                elif goodrunKW in response:
                    return True, reason
        return False, reason

    # save output of LLM to prevent repeated calculations
    CACHEPREFIX = '.LLMCache'
    os.makedirs(CACHEPREFIX, exist_ok=True)

    def LLMCache(runID, content, forceAI):
        dictTot = {'runID': runID, 'content': content, **settings}
        digest = sha256(json.dumps(dictTot, sort_keys=True).encode('utf-8')).hexdigest()
        cacheFilename = os.path.join(CACHEPREFIX, digest + '.json')
        if not forceAI:
            for i in range(1, 10000):
                if os.path.isfile(cacheFilename):
                    with open(cacheFilename) as f:
                        cache = json.load(f)
                        if cache['runID'] == runID:
                            return cache['goodrun'], cache['response']    
                        else:
                            cacheFilename = os.path.join(CACHEPREFIX, digest + '_%d.json' % i)
                else:
                    break
            else:
                raise RuntimeError('Really? 10000 hash collisions? Clear your LLMCache.')

        goodrun, response = askLLMIsRunGood(runID, content)
        with open(cacheFilename, 'w') as f:
            json.dump({'runID': runID, 'goodrun': goodrun, 'response': response}, f)
        return goodrun, response


    print('LLM loaded.')
    reasons = {}
    print('Deciding if the run is good.')
    print('Prompt template:')
    print(settings['promptFormat'])
    for runId, content in tqdm(result.items(), desc='LLM is judging'):
        if runId in skip:
            continue
        text = ' '.join([line for _, line in content.message.items()])
        if text.isspace() or text is None or text == '':
            goodRun = False
            response = 'The run log for run %s is empty' % runId
        else:
            try:
                #response = askLLM(runId, text, "A run is bad if it suffers unexpected beam lost, or a lot of errors, or suffer critical error, or it says explicity that the run is bad, otherwise they are good. However, if only one or two sectors are tripped, it's still good. If you cannot made definitive assessment, assume it is bad.")
                goodRun, response = LLMCache(runId, text, forceAI)
            except Exception as e:
                response = 'LLM encounters an error: ' + str(e)
                goodRun = False
        if not goodRun:
            reasons[runId] = response
    return reasons



def sentimentTrans(result, skip, threshold, **kwargs):
    raise RuntimeError('sentimentTrans is deprecated')
    try:
        from transformers import pipeline
    except ModuleNotFoundError as e:
        print('Module transformer not found. Please install both transformer and tensorflow with pip. Abort')
        raise e
    sentiment_pipeline = pipeline('sentiment-analysis', truncation=True)
    negRuns = []

    runIds = []
    contents = []
    fullContents = []

    for runId, content in result.items():
        runIds.append(runId)
        contents.append('\n'.join([line for line in content[0].split('\n') if 'production_' not in line]))
        fullContents.append(content)
    results = sentiment_pipeline(contents)
    for runId, result, content in zip(runIds, results, fullContents):
        if runId in skip:
            continue
        if result['label'] == 'NEGATIVE' and result['score'] > threshold:
            negRuns.append(runId)
    return negRuns, {}

