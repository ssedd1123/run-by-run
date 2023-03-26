# Import the SentimentIntensityAnalyzer class
import json
import argparse
from prettytable import PrettyTable, ALL

def sentiment(result, modelName='NLTK', **kwargs):
    if modelName == 'NLTK':
        return sentimentNLTK(result, **kwargs)
    else:
        return sentimentTrans(result, **kwargs)

def sentimentNLTK(result, **kwargs):
    try:
        import nltk
    except ModuleNotFoundError as e:
        print('nltk module not found. Please install with pip. Abort')
        raise e
    from nltk.sentiment import SentimentIntensityAnalyzer
    nltk.download('vader_lexicon')
    negResult = {}
    posResult = {}
    # Create an instance of the class
    sia = SentimentIntensityAnalyzer()

    for runId, content in result.items():
        scores = sia.polarity_scores(content[0])
        if scores['neg'] > 0:
            negResult[runId] = content
        else:
            posResult[runId] = content
    return posResult, negResult

def sentimentTrans(result, threshold, **kwargs):
    try:
        from transformers import pipeline
    except ModuleNotFoundError as e:
        print('Module transformer not found. Please install both transformer and tensorflow with pip. Abort')
        raise e
    sentiment_pipeline = pipeline('sentiment-analysis', truncation=True)
    negResult = {}
    posResult = {}

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
            negResult[runId] = content
        else:
            posResult[runId] = content
    return posResult, negResult

