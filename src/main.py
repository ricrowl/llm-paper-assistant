import os
from dotenv import load_dotenv
import re
import time
from pdf_extractor import PdfConverter
from assistant_groq import SummaryWriter

load_dotenv()

# Directories of pdf files
PDF_DIRS = os.environ.get("PDF_DIRS").split(",")

# sleep time for rate limits
# https://console.groq.com/settings/limits
SLEEP_FOR_RATE_LIMITS = 60
LLM_COOL_SEC = 30
LLM_COOL_TOKENS = 6000


def main():
    def run(pdf_path):
        PdfConverter(pdf_path).run()
        base_path, _ = os.path.splitext(pdf_path)
        json_path = base_path + ".json"
        SummaryWriter(
            json_path, llm_cool_sec=LLM_COOL_SEC, llm_cool_tokens=LLM_COOL_TOKENS
        ).run()

    target_pdf_paths = []
    # select uncreated pdf
    for pdf_dir in PDF_DIRS:
        file_names = [n for n in os.listdir(pdf_dir)]
        for pdf_name in file_names:
            base_name, ext = os.path.splitext(pdf_name)
            if ext == ".pdf":
                done = False
                for n in file_names:
                    pattern = r"^{}.*{}$".format(
                        re.escape(base_name), re.escape("JP.md")
                    )
                    if re.match(pattern, n):
                        done = True
                        break
                if not done:
                    pdf_path = os.path.join(pdf_dir, pdf_name)
                    print("Detect: {}".format(pdf_path))
                    target_pdf_paths.append(pdf_path)
    # create
    for i, pdf_path in enumerate(target_pdf_paths):
        try:
            st = time.time()
            header = "{} {} {}".format("=" * 5, pdf_path, "=" * 5)
            print(header)
            run(pdf_path)
            print("- {}[s] -\n{}\n".format(round(time.time() - st), "=" * len(header)))
            if i < len(target_pdf_paths) - 1:
                print("sleep {}[s] for rate limits".format(SLEEP_FOR_RATE_LIMITS))
                time.sleep(SLEEP_FOR_RATE_LIMITS)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
