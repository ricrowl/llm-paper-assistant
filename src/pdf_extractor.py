import fitz
import re
import os
import pickle
import json
from mdutils.mdutils import MdUtils
from tqdm import tqdm
from utils import parse_args, Formatter


class PdfConverter:
    def __init__(self, pdf_path, format_methods, output_dir=""):
        # get args
        self.pdf_path = pdf_path
        self.format_methods = format_methods
        self.output_dir = output_dir
        # Open PDF
        self.base_path, _ = os.path.splitext(self.pdf_path)
        with fitz.open(self.pdf_path) as doc:
            self.metadata = doc.metadata
            self.text_block_pages = self.load_text_block(doc)
            self.toc = doc.get_toc(simple=False)

    def load_text_block(self, doc):
        text_blocks = {}
        for p_num in range(len(doc)):
            page = doc.load_page(p_num)
            blocks = page.get_text("blocks")
            block_details = page.get_text("dict")["blocks"]
            block_details = [b for b in block_details if "lines" in b.keys()]
            if len(blocks) != len(block_details):
                text_coords = [(b["bbox"][0], b["bbox"][1]) for b in block_details]
            else:
                text_coords = None
            block_data_list = []
            for b_num, b in enumerate(blocks):
                data = {
                    "x0": b[0],
                    "y0": b[1],
                    "x1": b[2],
                    "y1": b[3],
                    "text": b[4],
                }
                if text_coords is None:
                    detail = block_details[b_num]
                    span = detail["lines"][0]["spans"][0]
                    data.update(
                        {
                            "size": span["size"],
                            "flags": span["flags"],
                            "font": span["flags"],
                            "line_text": span["text"],
                        }
                    )
                else:
                    target_coord = (data["x0"], data["y0"])
                    try:
                        d_num = text_coords.index(target_coord)
                        detail = block_details[d_num]
                        span = detail["lines"][0]["spans"][0]
                        data.update(
                            {
                                "size": span["size"],
                                "flags": span["flags"],
                                "font": span["flags"],
                                "line_text": span["text"],
                            }
                        )
                    except ValueError:
                        data.update(
                            {
                                "size": None,
                                "flags": None,
                                "font": None,
                                "line_text": None,
                            }
                        )
                block_data_list.append(data)
            text_blocks[p_num] = block_data_list
        return text_blocks

    def get_title(self):
        title = self.metadata["title"]
        if title is None or title == "":
            blocks = self.text_block_pages[0]
            blocks = blocks[: len(blocks) // 2]
            target_block = max(blocks, key=lambda x: x["size"])
            title = target_block["text"]
            title = title.replace("\n", "")
        return title

    def get_toc_bookmark(self):
        contents = []
        toc = self.toc
        for level, title, p_num, info in toc:
            p_num = p_num - 1
            b_num, b = self.search_block_keyword(p_num, title)
            if b_num is not None:
                contents.append(
                    {
                        "level": level,
                        "title": title,
                        "page": p_num,
                        "block": b_num,
                        "size": b["size"],
                        "title_line_text": b["line_text"],
                        "nameddest": info["nameddest"],
                    }
                )
        return contents

    def get_toc_section(self):
        contents = []
        for p_num, blocks in self.text_block_pages.items():
            for b_num, b in enumerate(blocks):
                title = b["text"]
                if len(title.split(" ")) > 1:
                    m = re.search(r"^[0-9]+(\.[0-9]+)*", title)
                    if m:
                        level = m.group()
                        level = len(level.split("."))
                        contents.append(
                            {
                                "level": level,
                                "title": title,
                                "page": p_num,
                                "block": b_num,
                                "size": b["size"],
                                "title_line_text": b["line_text"],
                            }
                        )
        return contents

    def add_toc_abstract(self, contents):
        p_num, title = 0, "Abstract"
        b_num, b = self.search_block_keyword(p_num, title)
        if b_num is not None:
            target_title = b["text"]
            m = re.search(title, target_title, re.IGNORECASE)
            target_title = m.group(0) if m else target_title
            existed_titles = [c["title"] for c in contents]
            if target_title not in existed_titles:
                contents.insert(
                    0,
                    {
                        "level": 1,
                        "title": target_title,
                        "page": p_num,
                        "block": b_num,
                        "size": b["size"],
                        "title_line_text": b["line_text"],
                    },
                )
        return contents

    def add_toc_terminal(self, contents):
        title = "References"
        toc_sizes = [c["size"] for c in contents]
        toc_lower_titles = [c["title"].lower() for c in contents]
        if title.lower() in toc_lower_titles:
            i = toc_lower_titles.index(title.lower())
            contents[i].update({"terminal": True})
            return contents
        for p_num in self.text_block_pages.keys():
            b_num, b = self.search_block_keyword(p_num, title)
            if b_num is not None:
                if b["size"] in toc_sizes:
                    target_title = b["text"]
                    m = re.search(title, target_title, re.IGNORECASE)
                    target_title = m.group(0) if m else target_title
                    insert_idx = [
                        c["page"] <= p_num
                        or (c["page"] == p_num and c["block"] < b_num)
                        for c in contents
                    ]
                    insert_idx = sum(insert_idx)
                    contents.insert(
                        insert_idx,
                        {
                            "level": 1,
                            "title": target_title,
                            "page": p_num,
                            "block": b_num,
                            "size": b["size"],
                            "title_line_text": b["line_text"],
                            "terminal": True,
                        },
                    )
                    break
        return contents

    def get_toc(self):
        contents = self.get_toc_bookmark()
        if len(contents) == 0:
            contents = self.get_toc_section()
        return contents

    def search_block_keyword(self, page_num, keyword):

        def search_block_keyword_match(text_blocks, keyword):
            blocks = [
                (i, b, len(b["text"]))
                for i, b in enumerate(text_blocks)
                if keyword in b["text"]
            ]
            return blocks

        def search_block_keyword_lower(text_blocks, keyword):
            alt_toc_title = keyword.lower()
            alt_toc_title = re.sub(r"^[0-9]+(\.[0-9]+)*\s+", "", alt_toc_title)
            blocks = [
                (i, b, len(b["text"]))
                for i, b in enumerate(text_blocks)
                if alt_toc_title in b["text"].lower()
            ]
            return blocks

        def search_block_keyword_headnumber(text_blocks, keyword):
            m = re.search(r"^[0-9]+(\.[0-9]+)*", keyword)
            if m:
                alt_toc_title = m.group()
                blocks = [
                    (i, b, len(b["text"]))
                    for i, b in enumerate(text_blocks)
                    if alt_toc_title in b["text"]
                ]
            else:
                blocks = []
            return blocks

        blocks = self.text_block_pages[page_num]
        start_block_cands = search_block_keyword_match(blocks, keyword)
        if len(start_block_cands) == 0:
            start_block_cands = search_block_keyword_lower(blocks, keyword)
        if len(start_block_cands) == 0:
            start_block_cands = search_block_keyword_headnumber(blocks, keyword)
        if len(start_block_cands) == 0:
            return None, None
        start_block = min(start_block_cands, key=lambda x: x[2])
        b_num, block = start_block[0], start_block[1]
        return b_num, block

    def filter_texts(self, texts):
        rejected_regexs = [
            re.compile(r"^Fig"),
            re.compile(r"^Figure"),
            re.compile(r"^Table"),
            re.compile(r"^TABLE"),
        ]
        texts = [t for t in texts if len(t.split(" ")) > 5]
        texts = [t for t in texts if len(t.split(" ")) >= len(t.split("\n"))]
        texts = [
            t
            for t in texts
            if sum(not c.isdigit() for c in t) > sum(c.isdigit() for c in t) * 2
        ]

        for reg in rejected_regexs:
            texts = [t for t in texts if not bool(reg.match(t))]
        return texts

    def construct_document(self):
        # get title
        title = self.get_title()
        # get TOC
        contents = self.get_toc()
        # add no numbering TOC
        contents = self.add_toc_abstract(contents)
        contents = self.add_toc_terminal(contents)
        # limit TOC range to terminal
        limited_contents = []
        limited = False
        for c in contents:
            limited_contents.append(c)
            if "terminal" in c.keys() and c["terminal"]:
                limited = True
                break
        if not limited:
            limited_contents.append(
                {
                    "page": max(self.text_block_pages.keys()),
                    "block": None,
                }
            )
        contents = limited_contents

        # extract text
        for i, c in enumerate(contents[:-1]):
            end_page_num = contents[i + 1]["page"]
            end_block_num = contents[i + 1]["block"]
            texts = []
            for p_num in range(c["page"], end_page_num + 1):
                text_blocks = self.text_block_pages[p_num]
                if p_num == end_page_num and end_block_num is not None:
                    text_blocks = text_blocks[:end_block_num]
                if p_num == c["page"]:
                    text_blocks = text_blocks[c["block"] :]
                extracted = [b["text"] for b in text_blocks]
                extracted = self.filter_texts(extracted)
                texts += extracted
            contents[i].update({"texts": texts})
        contents = contents[:-1]

        return {"title": title, "contents": contents}

    def sanitize_filename(self, filename):
        """
        Removes characters that cannot be used in filenames from a string.

        Args:
            filename (str): The string to sanitize.

        Returns:
            str: A string that is safe to use as a filename.
        """
        # Define characters that are invalid in filenames on Windows, macOS, and Linux
        invalid_chars = r'[\/:*?"<>|]'
        # Replace invalid characters with an empty string
        sanitized = re.sub(invalid_chars, "", filename)
        # Remove leading/trailing whitespace as well
        return sanitized.strip()

    def write_pkl(self, document, pkl_path):
        with open(pkl_path, "wb") as f:
            pickle.dump(document, f)

    def write_json(self, document, json_path):
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(document, f, ensure_ascii=False, indent=4)

    def write_md(self, document, md_path):
        title = document["title"]
        contents = document["contents"]
        mdFile = MdUtils(file_name=md_path, title=title)
        for c in contents:
            mdFile.new_header(level=c["level"], title=c["title"])
            for t in c["texts"]:
                t = t.replace("#", "\#")
                mdFile.new_line(t)
        mdFile.create_md_file()

    def run(self, pkl_path=None, json_path=None, md_path=None):
        print("Extract PDF: {}".format(self.base_path))
        # extract PDF contents
        document = self.construct_document()
        # format texts
        document = Formatter().run(document, methods=self.format_methods)
        # save
        save_dir, save_name = os.path.split(self.base_path)
        if self.output_dir != "":
            save_dir = self.output_dir
        title_name = self.sanitize_filename(document["title"])
        save_name = "{}({})".format(save_name, title_name)
        save_path = os.path.join(save_dir, save_name)
        # # write pkl
        # pkl_path = self.base_path + ".pkl" if pkl_path is None else pkl_path
        # self.write_pkl(document, pkl_path)
        # write json
        json_path = save_path + ".json" if json_path is None else json_path
        self.write_json(document, json_path)
        # write markdown
        md_path = save_path + ".md" if md_path is None else md_path
        self.write_md(document, md_path)


def main():
    args = parse_args()
    pdf_path = args.pdf
    output_dir = args.output
    format_methods = args.format

    if os.path.isfile(pdf_path):
        PdfConverter(pdf_path, format_methods, output_dir=output_dir).run()
    elif os.path.isdir(pdf_path):
        # Process all PDF files in the directory
        print(f"Multiple PDF files detected in '{pdf_path}'.")
        pdfs = []
        if os.path.exists(pdf_path) and os.path.isdir(pdf_path):
            for root, _, files in os.walk(pdf_path):
                for fname in files:
                    if os.path.splitext(fname)[1].lower() == ".pdf":
                        pdfs.append(os.path.join(root, fname))
        for pdf_path_in_dir in tqdm(pdfs, desc="Processing PDFs"):
            PdfConverter(pdf_path_in_dir, format_methods, output_dir=output_dir).run()
    else:
        print(f"Error: '{pdf_path}' is not a valid file or directory.")


if __name__ == "__main__":
    main()
