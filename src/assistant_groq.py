import os
from dotenv import load_dotenv
from groq import Groq
import pickle
import json
from mdutils.mdutils import MdUtils
import time

load_dotenv()


SYSTEM_PROMPT_EXPRAINER = """
You are an AI assistant who explains AI technology.
"""
SYSTEM_PROMPT_TRANSLATOR = """
あなたは英語の文章を日本語に翻訳するAIアシスタントです。
"""
PRE_PROMPT_EXPRAINER = """
Please explain the following sentences in detail. Please summarize in bullet points using only * for clarity.
<example>
**section**
* point1
* point2
</example>
<sentence>
{}
</sentence>
"""
PRE_PROMPT_TRANSLATOR = """
以下の文章を日本語訳してください。ただし、文章の形は崩さず、専門用語は翻訳しないでください。
<文章>
{}
</文章>
"""


class LLM:
    def __init__(self):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.system_prompt = {
            "explainer": SYSTEM_PROMPT_EXPRAINER,
            "translator": SYSTEM_PROMPT_TRANSLATOR,
        }
        self.pre_prompt = {
            "explainer": PRE_PROMPT_EXPRAINER,
            "translator": PRE_PROMPT_TRANSLATOR,
        }
        self.model_params = {
            "model": "llama3-70b-8192",
            # model="mixtral-8x7b-32768",
            # model="gemma-7b-it",
            "temperature": 0.6,
            "max_tokens": 8192,
            "top_p": 0.9,
        }
        self.max_redo = 3

    def post_process(self, sentence):
        lines = sentence.split("\n")
        start = end = None
        for i, line in enumerate(lines):
            if (len(line) > 0) and (line[0] == "*"):
                start = start if start is not None else i
                end = i
        if start is None or end is None:
            return None
        else:
            return "\n".join(lines[start : end + 1])

    def chat(self, sentence, actor, post_proc=False):
        def run():
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt[actor],
                    },
                    {
                        "role": "user",
                        "content": self.pre_prompt[actor].format(sentence),
                    },
                ],
                **self.model_params
            )
            return chat_completion.choices[0].message.content

        res = run()
        if post_proc:
            cnt = 0
            while True:
                processed = self.post_process(res)
                if (processed is None) and (cnt < self.max_redo):
                    print("Redo: Bad responce.")
                    res = run()
                    cnt += 1
                else:
                    break
            if processed is None:
                print("No valid responce.")
            else:
                res = processed
        return res


class SummaryWriter:
    def __init__(self, file_path, llm_cool_sec=0, llm_cool_tokens=12000):
        self.llm = LLM()
        self.base_path, self.ext = os.path.splitext(file_path)
        self.document = self.read(file_path, self.ext)
        self.llm_cool_sec = llm_cool_sec
        self.llm_cool_tokens = llm_cool_tokens

    def read(self, file_path, ext=".json"):
        if ext == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                document = json.load(f)
        elif ext == ".pkl":
            with open(file_path, "rb") as f:
                document = pickle.load(f)
        else:
            document = None
        return document

    def summary(self):
        def cool_llm(sentence):
            num_words = len(sentence.split(" "))
            print("\tAbout {} tokens".format(num_words))
            if num_words > self.llm_cool_tokens:
                print(
                    "\t\tSleep{}[s]: Over LLM cool tokens {}".format(
                        self.llm_cool_sec, self.llm_cool_tokens
                    )
                )
                time.sleep(self.llm_cool_sec)

        def run_llm(sentence):
            summary = self.llm.chat(sentence, actor="explainer", post_proc=True)
            cool_llm(sentence)
            summary_jp = self.llm.chat(summary, actor="translator", post_proc=True)
            cool_llm(summary)
            return summary, summary_jp

        contents = self.document["contents"]
        for i, c in enumerate(contents):
            print("Summary: {}".format(c["title"]))
            st = time.time()
            sentence = "\n".join(c["texts"])
            if len(sentence.split(" ")) > 1:
                summary, summary_jp = run_llm(sentence)
            else:
                print("No sentence")
                summary, summary_jp = sentence, sentence
            contents[i]["summary"] = summary
            contents[i]["summary_jp"] = summary_jp
            print("\tElapsed time: {}[s]".format(round(time.time() - st, 1)))
        return contents

    def write_json(self, document, json_path):
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(document, f, ensure_ascii=False, indent=4)

    def write_md(self, document, md_path, write_key):
        title = document["title"]
        contents = document["contents"]
        mdFile = MdUtils(file_name=md_path, title=title)
        for c in contents:
            mdFile.new_header(level=c["level"], title=c["title"])
            mdFile.new_line(c[write_key])
        mdFile.create_md_file()

    def run(self, json_path=None, md_en_path=None, md_jp_path=None):
        title = self.document["title"]
        print("Call assistant for: {}({})".format(self.base_path, title))
        contents = self.summary()
        summary_doc = {"title": title, "contents": contents}
        json_path = self.base_path + ".json" if json_path is None else json_path
        self.write_json(summary_doc, json_path)
        md_en_path = (
            "{}({})_EN.md".format(self.base_path, title)
            if md_en_path is None
            else md_en_path
        )
        self.write_md(summary_doc, md_en_path, "summary")
        md_jp_path = (
            "{}({})_JP.md".format(self.base_path, title)
            if md_jp_path is None
            else md_jp_path
        )
        self.write_md(summary_doc, md_jp_path, "summary_jp")


def main():
    SummaryWriter("./data/pdf/sample.json").run()


if __name__ == "__main__":
    main()
