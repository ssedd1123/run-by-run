## Installation

ONLY WORKS on machine with chrome installed. Does not work on RCAS unless you installed chrome manually there. I heard it's possible, but I haven't tried it.

Run `pip install nltk prettytable selenium prompt_toolkit beautifulsoup4`

## Download shift log

Run `python runLog.py -i badrun.list -o shiftLog.json -ho shiftLog.txt`

shiftLog.json is for computer to read and shiftLog.txt is for human to read.

## Interactively inspect shift log

Run `python sentiment.py -i shiftLog.json -o newBadrun.list -no newBadrun.txt`

An interactive interface appears where you can select if a run is good or bad. The final selected list will be saved to newBadrun.list. The corresponding shift logs will be saved to newBadrun.txt

### Use AI

Run `python sentiment.py -i shiftLog.json -o newBadrun.list -no newBadrun.txt --useAI`

AI will consider any runs with log entry that conveys negative emotion a bad run. You just have to vet the remainning runs that doesn't convey negative tone. Empirically it saves you 40% of the work.
