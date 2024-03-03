## Installation

**Note:** This application is designed to work on machines with either Chrome or Firefox installed. It may not function correctly on RCAS unless Chrome is manually installed. While there are potential solutions, I have not personally tested them.

To install the required dependencies, run the following command:

```bash
python3 -m pip install nltk prettytable selenium prompt_toolkit beautifulsoup4 pyfiglet chromedriver_autoinstaller
```

If you wish to use AI, you need to install `llama_cpp`. For CPU-only usage, run:

```bash
python3 -m pip install llama_cpp
```

For GPU support, you must refer to platform-specific instructions as configurations may vary based on your GPU hardware. Unfortunately, there is no universal script for cross-platform compatibility.

Using GPU for inference is highly recommended due to significantly faster performance compared to CPU.

## Download Shift Log

Assuming you have a list of problematic runs from the QA code named `badrun.list`, execute the following command:

```bash
python3 shiftLog.py -i badrun.list -br newBadrun.list
```

Enter your username and password when prompted. The download will commence upon successful validation of your credentials.

Upon completion, an interactive interface will appear allowing you to categorize each run as either good or bad. The final list of selections will be saved to `newBadrun.list`.

All downloaded run entries will be cached locally to minimize network load during subsequent retrievals.

## Use Firefox

If Chrome is unavailable, add the `--useFirefox` argument to your command:

```bash
python3 shiftLog.py -i badrun.list -br newBadrun.list --useFirefox
```

## Ask AI

To utilize AI, you need the LLM file stored as a gguf file. Various LLMs can be downloaded from Hugging Face (search for it). Keep in mind that not all LLMs are equal in intelligence; some may not follow instructions well.

The Mistral 7B instruct model was tested and found to work effectively. Ensure you have at least 8 GB of RAM or VRAM for GPU usage.

To run AI, modify the "model" entry in `LLM_settings.json` to point to the gguf file. Adjust the "badRunDescription" according to your needs.

Use the following command to create a bad run list automatically:

```bash
python3 shiftLog.py -i badrun.list -br newBadrun.list --justAI LLM
```

For manual review of each AI entry, use the `--useAI` flag instead of `--justAI`:

```bash
python3 shiftLog.py -i badrun.list -br newBadrun.list --useAI LLM
```

## Other Questions

For a comprehensive list of options, use the `-h` argument:

```bash
python3 shiftLog.py -h
```
