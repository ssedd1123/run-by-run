# Import the SentimentIntensityAnalyzer class
import json
import argparse
from prettytable import PrettyTable, ALL
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

def sentiment(result, modelName='NLTK', **kwargs):
    if modelName == 'NLTK':
        return sentimentNLTK(result, **kwargs)
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
        scores = sia.polarity_scores(preprocess_text(content[0]))
        if scores['neg'] > 0:
            negRuns.append(runId)
        splited = content[1].split('RUN' + runId + 'START')
        if len(splited) == 2:
            scores = sia.polarity_scores(preprocess_text(splited[1].lstrip('8')))
        else:
            scores = {'neg': -1}
        #scores = sia.polarity_scores(preprocess_text(content[2].split('run number | status | nEvents |')[0]))
        if scores['neg'] > 0:
            negHistory.append(runId)
        scores = sia.polarity_scores(preprocess_text(content[2]))
        if scores['neg'] > 0:
            negSummary.append(runId)
    return negRuns, negHistory, negSummary

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
    return negRuns

