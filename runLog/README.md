## Installation

ONLY WORKS on machine with chrome installed. Does not work on RCAS unless you installed chrome manually there. I heard it's possible, but I haven't tried it.

Run `python3 -m pip install nltk prettytable selenium prompt_toolkit beautifulsoup4 pyfiglet pynput chromedriver_autoinstaller`

## Download shift log

Run `python3 shiftLog.py -i badrun.list -br newBadrun.list`

When download is completed, an interactive interface appears where you can select if a run is good or bad. The final selected list will be saved to newBadrun.list. The corresponding shift logs will be saved to newBadrun.txt

All downloaded run entries will be cached locally. It will not download retrieved entries to reduce network load.
