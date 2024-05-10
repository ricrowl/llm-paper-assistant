# llm-paper-assistant

This application translates English research papers into Japanese and summarizes them using a Large Language Model (LLM).

## Install

Install the required Python packages:
```
pip install -r requirements.txt
```

## Get LLM API key

1. Create Groq account: https://console.groq.com/
2. Generate an API key and copy it to the GROQ_API_KEY variable in the .env file

## Usage

1. In the .env file, set `PDF_DIRS` to a comma-separated list of directories containing the PDFs to translate. For example:
    ```
    PDF_DIRS=./data/papers1,./data/papers2
    ```
2. Save the English research paper PDFs in the directories defined in `PDF_DIRS`
3. Run the translation script:
    ```
    python main.py
    ```