## Installation

**Note:** This application is designed to work on machines with either Chrome or Firefox installed. It may not function correctly on RCAS unless Chrome is manually installed. While there are potential solutions, I have not personally tested them.

To install the required dependencies, run the following command:

```bash
python3 -m pip install nltk prettytable selenium prompt_toolkit beautifulsoup4 pyfiglet chromedriver_autoinstaller tqdm
```

If you wish to use AI, you need to install `llama_cpp`. For CPU-only usage (NOT RECOMMENDED!!!), run:

```bash
conda install llama_cpp
```

For GPU support, you must refer to platform-specific instructions as configurations may vary based on your GPU hardware. Unfortunately, there is no universal script for cross-platform compatibility.

Using GPU for inference is highly recommended due to significantly faster performance compared to CPU.

## Download Shift Log

Assuming you have a list of problematic runs from the QA code named `badrun.list`, execute the following command:

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list
```

Where \<Run Year\> is the last two digits of the run year. For instance, you should put `python3 shiftLog.py -YR 20 -i ...` for run number 20344002 because run number 20344002 belongs to Run 20. 

Enter your username and password when prompted. The download will commence upon successful validation of your credentials.

Upon completion, an interactive interface will appear allowing you to categorize each run as either good or bad. The final list of selections will be saved to `newBadrun.list`.

All downloaded run entries will be cached locally to minimize network load during subsequent retrievals. To remove the cached pages, remove the `HTML` directory. 

## Use Firefox

If Chrome is unavailable, add the `--useFirefox` argument to your command:

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list --useFirefox
```

## Set minimal run duration

You can automatically reject runs that are too short. Use the flag `-md` as follow,

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list -md <minimum duration in seconds>
```

When you manually review bad runs in the UI, runs that are too short will be indicated clearly both in the center and lower left hand corner of the UI.

Alternatively, if you do not want to review every run manually and just want a list of short run, enable `--skipUI`,

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list -md <minimum duration in seconds> --skipUI
```

You will not be prompted to select bad runs. Only runs with short duration will be saved to `newBadrun.list`.


## Ask AI

To utilize AI, you need the LLM file stored as a gguf file. Various LLMs can be downloaded from Hugging Face (search for it). Keep in mind that not all LLMs are equal in intelligence; some may not follow instructions well.

The Microsoft Phi4 model was tested and found to work effectively. Ensure you have at least 8 GB of RAM or VRAM for GPU usage.

To run AI, modify the "model" entry in `LLM_settings.json` to point to the gguf file. Adjust the "badRunDescription" according to your needs.

When you switch to using a new AI, remember to first test if they obtain instructions by runing self test,

```bash
python3 shiftLog.py --test --jsonAI jsons\<insert json file> -i test -YR 0 --useAI -md 0 --skipUI
```

Make sure the accuracy make sense before using it.

Here's the default settings for FXT 7.2 GeV data for reference,

```bash
python3 shiftLog.py --jsonAI jsons\LLM_settings_mid_Phi4.json -i badrun_7.2GeV.list -YR 20 --useAI -md 120 --skipUI
```

Use the following command to create a bad run list automatically:

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list --useAI
```

For manual review of each AI entry, use the `--useAI` flag instead of `--justAI`:

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list --useAI 
```

You can also use `--skipUI` to save all bad runs without manual review,

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list --useAI --skipUI
```

Response from AI are cached. The responses are saved in `.LLMCache` directory so the next time you run AI with the same json file and runID, it will just retrieve the cache to speed things up.

## Change bad run criteria

Create a copy of `jsons/LLM_settings_mid.json`, then describe what a bad run is in plain English in the new json file. Three example json files are provided in the jsons\ directory with various strictness in bad run definition. The script uses `jsons/LLM_settings_mid.json` by default. If you do not want to overwrite your previous settings, you can copy that file and call it something else, then run,

```bash
python3 shiftLog.py -YR <Run Year> -i badrun.list -br newBadrun.list --useAI --jsonAI <the new json filename>
```

## Other Questions

For a comprehensive list of options, use the `-h` argument:

```bash
python3 shiftLog.py -YR <Run Year> -h
```
