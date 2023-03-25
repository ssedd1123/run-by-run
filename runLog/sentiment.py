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
    nEmpty = 0
    posResult = {}
    # Create an instance of the class
    sia = SentimentIntensityAnalyzer()

    for runId, content in result.items():
        if content is None: 
            posResult[runId] = None
            nEmpty = nEmpty + 1
            continue
        scores = sia.polarity_scores(content)
        if scores['neg'] > 0:
            negResult[runId] = content
        else:
            posResult[runId] = content
    return posResult, negResult, nEmpty

def sentimentTrans(result, threshold, **kwargs):
    try:
        from transformers import pipeline
    except ModuleNotFoundError as e:
        print('Module transformer not found. Please install both transformer and tensorflow with pip. Abort')
        raise e
    sentiment_pipeline = pipeline('sentiment-analysis', truncation=True)
    negResult = {}
    nEmpty = 0
    posResult = {}

    runIds = []
    contents = []
    fullContents = []

    for runId, content in result.items():
        if content is None: 
            posResult[runId] = None
            nEmpty = nEmpty + 1
        else:
            runIds.append(runId)
            contents.append('\n'.join([line for line in content.split('\n') if 'production_' not in line]))
            fullContents.append(content)
    results = sentiment_pipeline(contents)
    for runId, result, content in zip(runIds, results, fullContents):
        if result['label'] == 'NEGATIVE' and result['score'] > threshold:
            negResult[runId] = content
        else:
            posResult[runId] = content
    return posResult, negResult, nEmpty


def printDict(result):
    x = PrettyTable()
    x.hrules=ALL
    x.field_names = ['RunID', 'Content']
    for runId, content in result.items():
        x.add_row([runId, content if content is not None else ''])
    x.align['Content'] = 'l'
    return x.get_string()

def manualSelect(*args, **kwargs):
    from UI import main
    return main(*args, **kwargs)


def main(input, output, posOutput, negOutput, useAI, justAI, **kwargs):
    if justAI is not None:
        useAI = justAI
    with open(input) as f:
        result = json.load(f)
    if useAI is not None:
        pos, neg, nEmpty = sentiment(result, useAI, **kwargs)
        intro = 'AI have selected %d runLog entries out of a total of %d for further review.' % (len(pos) - nEmpty, len(result))
        print(intro)
    else:
        pos = result
        neg = {}
        intro = 'There are %d non empty shift entries to go through' % sum(x is not None for _, x in result.items())
    if justAI is not None:
        print('justAI enabled. All runs requiring further review are considered good runs.')
    else:
        pos, moreNeg = manualSelect(pos, intro)
        for runID, content in moreNeg.items():
            neg[runID] = content
    if posOutput is not None:
        with open(posOutput, 'w') as f:
            f.write(printDict(pos))
    if negOutput is not None:
        with open(negOutput, 'w') as f:
            f.write(printDict(neg))
    with open(output, 'w') as f:
        f.write('\n'.join(neg.keys()))
    return pos, neg

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sentimental analysis on runLog entries')
    parser.add_argument('-i', '--input', required=True, help='Json file generated from runLog.py, or otherwise contains all text from runLog.')
    parser.add_argument('-o', '--output', required=True, help='Text file with just runID of bad runs with negative setiment')
    parser.add_argument('-po', '--posOutput', help='Name of the human readible file to which positive runs are stored')
    parser.add_argument('-no', '--negOutput', help='Name of the human readible file to which negative runs are stored')
    parser.add_argument('--useAI', action='store_true', help='Use AI to help select bad runs from runLog.')
    parser.add_argument('--justAI', action='store_true', help='Just Use AI to select bad runs from runLog. No user prompt. Will override --useAI option.')

    args = parser.parse_args()
    main(args.input, args.output, args.posOutput, args.negOutput, args.useAI, args.justAI)
