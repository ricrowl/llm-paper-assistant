# llm-paper-assistant

This application translates English research papers into Japanese and summarizes them using a Large Language Model (LLM).

## Install

Install uv
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Initialize
```
uv init --no-readme
```

Activate virtual env / Update env from pyproject.toml
```
uv sync
```


## Get LLM API key

### Hugging Face

1. Create HuggingFace account
2. Generate an API key and copy it to the HF_TOKEN variable in the .env file

### If want to use Groq

1. Create Groq account: https://console.groq.com/
2. Generate an API key and copy it to the GROQ_API_KEY variable in the .env file

### If want to use ollama

https://github.com/ollama/ollama/blob/main/docs/linux.md#manual-install

1. Download and extract the package:
    ```
    curl -LO https://ollama.com/download/ollama-linux-amd64.tgz
    sudo rm -rf /usr/lib/ollama
    sudo tar -C /usr -xzf ollama-linux-amd64.tgz
    ```
2. Start Ollama:
    ```
    ollama serve
    ```

## Usage

### Extract PDF

- Single PDF file
    ```
    python src/pdf_extractor.py \
        -p "data/pdf/test/sample.pdf" \
        -o "data/pdf/test/" \
        -f "del_break"
    ```
- Multiple PDF files in dir
    ```
    python src/pdf_extractor.py \
        -p "data/pdf/test/" \
        -o "data/pdf/test/" \
        -f "del_break"
    ```
2. Translate using LLM