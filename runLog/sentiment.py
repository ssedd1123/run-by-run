# Import the SentimentIntensityAnalyzer class
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import json
import argparse
from prettytable import PrettyTable, ALL

def sentiment(result):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sentimental analysis on runLog entries')
    parser.add_argument('-i', '--input', required=True, help='Json file generated from runLog.py, or otherwise contains all text from runLog.')
    parser.add_argument('-o', '--output', required=True, help='Text file with just runID of bad runs with negative setiment')
    parser.add_argument('-po', '--posOutput', help='Name of the human readible file to which positive runs are stored')
    parser.add_argument('-no', '--negOutput', help='Name of the human readible file to which negative runs are stored')
    parser.add_argument('--useAI', action='store_true', help='Use AI to help select bad runs from runLog.')
    parser.add_argument('--justAI', action='store_true', help='Just Use AI to select bad runs from runLog. No user prompt. Will override --useAI option.')

    args = parser.parse_args()
    if args.justAI:
        args.useAI = True

    with open(args.input) as f:
        result = json.load(f)
    if args.useAI:
        pos, neg, nEmpty = sentiment(result)
        intro = 'AI have selected %d runLog entries out of a total of %d for further review.' % (len(pos) - nEmpty, len(result))
        print(intro)
    else:
        pos = result
        neg = {}
        intro = 'There are %d runLog to go through' % len(result)
    if args.justAI:
        print('justAI enabled. All runs requiring further review are considered good runs.')
    else:
        pos, moreNeg = manualSelect(pos, intro)
        for runID, content in moreNeg.items():
            neg[runID] = content
    if args.posOutput is not None:
        with open(args.posOutput, 'w') as f:
            f.write(printDict(pos))
    if args.negOutput is not None:
        with open(args.negOutput, 'w') as f:
            f.write(printDict(neg))
    with open(args.output, 'w') as f:
        f.write('\n'.join(neg.keys()))
