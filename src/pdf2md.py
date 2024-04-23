import fitz
from mdutils.mdutils import MdUtils
import re
import json


class PdfConverter:
    def __init__(self):
        pass

    def get_title(self, doc):
        title = doc.metadata["title"]
        if title is None or title == "":
            page = doc.load_page(0)
            text_blocks = page.get_text("blocks")
            title = text_blocks[0][4]
            title = title.replace("\n", "")
        return title

    def get_toc_bookmark(self, doc):
        toc = doc.get_toc(simple=False)
        contents = [
            {
                "level": level,
                "title": title,
                "page": page - 1,
                "nameddest": info["nameddest"],
            }
            for (level, title, page, info) in toc
        ]
        return contents

    def get_toc_section(self, doc):
        contents = []
        for p_num in range(len(doc)):
            page = doc.load_page(p_num)
            text_blocks = page.get_text("dict")["blocks"]
            for b in text_blocks:
                if "lines" in b:
                    for line in b["lines"]:
                        for span in line["spans"]:
                            title = span["text"]
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
                                            "size": span["size"],
                                        }
                                    )
        return contents

    def add_toc_abstract(self, doc, contents):
        p_num, title = 0, "Abstract"
        toc_idx = self.search_toc_block(doc, p_num, title)
        if toc_idx is not None:
            extracted_title = toc_idx["block"][4]
            m = re.search(title, extracted_title, re.IGNORECASE)
            extracted_title = m.group(0) if m else extracted_title
            existed_titles = [c["title"] for c in contents]
            if extracted_title not in existed_titles:
                contents.insert(
                    0,
                    {
                        "level": 1,
                        "title": extracted_title,
                        "page": p_num,
                    },
                )
        return contents

    def add_toc_terminal(self, doc, contents):
        title = "References"
        toc_indice = [
            self.search_toc_block(doc, c["page"], c["title"]) for c in contents
        ]
        # remove no block toc
        for toc_idx, c in zip(toc_indice, contents):
            if toc_idx is None:
                toc_indice.remove(toc_idx)
                contents.remove(c)
        toc_fonts = [
            self.get_block_font(doc, c["page"], idx["index"])
            for c, idx in zip(contents, toc_indice)
        ]
        toc_font_sizes = [font["size"] for font in toc_fonts if font is not None]

        for p_num in range(len(doc)):
            toc_idx = self.search_toc_block(doc, p_num, title)
            if toc_idx is not None:
                extracted_title = toc_idx["block"][4]
                extracted_font = self.get_block_font(doc, p_num, toc_idx["index"])
                m = re.search(title, extracted_title, re.IGNORECASE)
                extracted_title = m.group(0) if m else extracted_title
                existed_titles = [c["title"].lower() for c in contents]
                if (
                    extracted_font["size"] in toc_font_sizes
                    and extracted_title.lower() not in existed_titles
                ):
                    insert_idx = [
                        c["page"] <= p_num
                        or (c["page"] == p_num and c["block"] < toc_idx["index"])
                        for c in contents
                    ]
                    insert_idx = sum(insert_idx)
                    contents.insert(
                        insert_idx,
                        {
                            "level": 1,
                            "title": extracted_title,
                            "page": p_num,
                            "terminal": True,
                        },
                    )
                    break
        return contents

    def get_toc(self, doc):
        contents = self.get_toc_bookmark(doc)
        if len(contents) == 0:
            contents = self.get_toc_section(doc)
        return contents

    def search_toc_block_match(self, text_blocks, toc_title):
        blocks = [
            (i, b, len(b[4])) for i, b in enumerate(text_blocks) if toc_title in b[4]
        ]
        return blocks

    def search_toc_block_lower(self, text_blocks, toc_title):
        alt_toc_title = toc_title.lower()
        alt_toc_title = re.sub(r"^[0-9]+(\.[0-9]+)*\s+", "", alt_toc_title)
        blocks = [
            (i, b, len(b[4]))
            for i, b in enumerate(text_blocks)
            if alt_toc_title in b[4].lower()
        ]
        return blocks

    def search_toc_block_number(self, text_blocks, toc_title):
        m = re.search(r"^[0-9]+(\.[0-9]+)*", toc_title)
        if m:
            alt_toc_title = m.group()
            blocks = [
                (i, b, len(b[4]))
                for i, b in enumerate(text_blocks)
                if alt_toc_title in b[4]
            ]
        else:
            blocks = []
        return blocks

    def search_toc_block(self, doc, toc_page, toc_title):
        page = doc.load_page(toc_page)
        text_blocks = page.get_text("blocks")
        start_block_cands = self.search_toc_block_match(text_blocks, toc_title)
        if len(start_block_cands) == 0:
            start_block_cands = self.search_toc_block_lower(text_blocks, toc_title)
        if len(start_block_cands) == 0:
            start_block_cands = self.search_toc_block_number(text_blocks, toc_title)
        if len(start_block_cands) == 0:
            return None
        start_block = min(start_block_cands, key=lambda x: x[2])
        block_index, block = start_block[0], start_block[1]
        return {"index": block_index, "block": block}

    def get_block_font(self, doc, page_num, block_index):
        page = doc.load_page(page_num)
        text_blocks = page.get_text("dict")["blocks"]
        block = text_blocks[block_index]
        if "lines" in block:
            span = block["lines"][0]["spans"][0]
            return {"font": span["font"], "size": float(span["size"])}
        else:
            return None

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

    def read_pdf_document(self, pdf_path):
        with fitz.open(pdf_path) as doc:
            # get title
            title = self.get_title(doc)
            # get TOC
            contents = self.get_toc(doc)
            # add no number toc
            contents = self.add_toc_abstract(doc, contents)
            contents = self.add_toc_terminal(doc, contents)
            # get block index
            toc_indice = [
                self.search_toc_block(doc, c["page"], c["title"]) for c in contents
            ]
            # remove no block toc
            for toc_idx, c in zip(toc_indice, contents):
                if toc_idx is None:
                    toc_indice.remove(toc_idx)
                    contents.remove(c)
            # extract text
            for i, (toc_idx, c) in enumerate(zip(toc_indice, contents)):
                if i < len(contents) - 1:
                    end_page = contents[i + 1]["page"]
                    end_idx = toc_indice[i + 1]["index"]
                else:
                    end_page = len(doc) - 1
                    end_idx = None
                texts = []
                for p_num in range(c["page"], end_page + 1):
                    page = doc.load_page(p_num)
                    text_blocks = page.get_text("blocks")
                    if p_num == end_page and end_idx is not None:
                        text_blocks = text_blocks[:end_idx]
                    if p_num == c["page"]:
                        text_blocks = text_blocks[toc_idx["index"] :]
                    extracted = [b[4] for b in text_blocks]
                    extracted = self.filter_texts(extracted)
                    texts += extracted
                contents[i].update({"texts": texts})
            self.add_toc_abstract(doc, contents)

            print(f"{title}\n===")
            for c in contents:
                print(f"{c}\n")

        return {"title": title, "contents": contents}

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

    def run(self, pdf_path, md_path):
        document = self.read_pdf_document(pdf_path)
        self.write_md(document, md_path)


def main():
    PdfConverter().run(
        "./data/pdf/sample.pdf", "./data/pdf/sample.pdf.md"
    )


if __name__ == "__main__":
    main()
