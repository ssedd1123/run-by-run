# Import the SentimentIntensityAnalyzer class
import json
import argparse
from prettytable import PrettyTable, ALL
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from tqdm import tqdm

def sentiment(result, modelName='NLTK', **kwargs):
    if modelName == 'NLTK':
        return sentimentNLTK(result, **kwargs)
    elif modelName == 'LLM':
        return sentimentLLM(result, **kwargs)
    else:
        return sentimentTrans(result, **kwargs)

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


def sentimentNLTK(result, **kwargs):
    try:
        import nltk
    except ModuleNotFoundError as e:
        print('nltk module not found. Please install with pip. Abort')
        raise e
    from nltk.sentiment import SentimentIntensityAnalyzer
    nltk.download('all')
    nltk.download('vader_lexicon')
    # Create an instance of the class
    sia = SentimentIntensityAnalyzer()
    negRuns = []
    negHistory = []
    negSummary = []
    for runId, content in result.items():
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


def sentimentLLM(result, threshold=0, **kwargs):
    # load settings of LLM from json
    import json
    with open('LLM_settings.json') as f:
        settings = json.load(f)

    from llama_cpp import Llama
    print('Loading LLM model.')
    #llm = Llama(model_path=r'D:\Download\text-generation-webui-main\text-generation-webui-main\models\mistral-7b-instruct-v0.2.Q5_K_M.gguf', n_gpu_layers=512, n_ctx=512, verbose=False)
    llm = Llama(model_path=settings['model'], n_gpu_layers=settings['n_gpu_layers'], n_ctx=settings['n_ctx'], verbose=settings['verbose'])
    threshold = settings['threshold']

    def askLLM(runID, content, descriptionOfBadRuns):
        response = llm.create_chat_completion(
          messages = [
                {"role": "system", "content": "You are an assistant who help users identify bad runs from runLog."},
                {
                    "role": "user",
                    "content": "This is the run log of run  %s\n%s\n%s. %s " % (runID, content, descriptionOfBadRuns, settings['additionalPrompt'])
                }
            ]
          )
        return response['choices'][0]['message']['content']

    print('LLM loaded.')

    try:
        import nltk
    except ModuleNotFoundError as e:
        print('nltk module not found. Please install with pip. Abort')
        raise e
    from nltk.sentiment import SentimentIntensityAnalyzer
    nltk.download('all', quiet=not settings['verbose'])
    nltk.download('vader_lexicon', quiet=not settings['verbose'])
    # Create an instance of the class
    sia = SentimentIntensityAnalyzer()
    negRuns = []
    negHistory = []
    negSummary = []
    reasons = {}
    print('Deciding if the run is good.')
    for runId, content in tqdm(result.items()):
        text = ' '.join([line for _, line in content.message.items()])
        if text.isspace() or text is None or text == '':
           scores = {'pos': threshold - 1}
           response = 'The run log for run %s is empty' % runId
        else:
            try:
                #response = askLLM(runId, text, "A run is bad if it suffers unexpected beam lost, or a lot of errors, or suffer critical error, or it says explicity that the run is bad, otherwise they are good. However, if only one or two sectors are tripped, it's still good. If you cannot made definitive assessment, assume it is bad.")
                response = askLLM(runId, text, settings['badRunDescription'])
                scores = sia.polarity_scores(preprocess_text(response))
            except Exception as e:
                response = 'LLM encounters an error: ' + str(e)
                scores = {"pos": threshold - 1}
        if scores['pos'] <= threshold:
            negRuns.append(runId)
            negHistory.append(runId)
            negSummary.append(runId)
            reasons[runId] = response
    return negRuns, negHistory, negSummary, reasons



def sentimentTrans(result, threshold, **kwargs):
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
        if result['label'] == 'NEGATIVE' and result['score'] > threshold:
            negRuns.append(runId)
    return negRuns, {}

