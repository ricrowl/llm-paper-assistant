import argparse
import re
import copy


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="LLM paper assistant")
    parser.add_argument(
        "-p", "--pdf", type=str, required=True, help="Target pdf file or dir"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="",
        help="Output directory to save markdown files.",
    )
    parser.add_argument(
        "-f",
        "--format",
        type=str,
        default="",
        help="Comma-separated format methods, e.g.: del_break,neurips_preprint.",
    )

    return parser.parse_args()


class Formatter:
    def __init__(self):
        self.funcs = {
            "del_break": Formatter.del_break,
            "neurips_preprint": Formatter.neurips_preprint,
        }

    def run(self, document, methods):
        """
        Run format functions involved in Comma-separated methods.

        Args:
            document: Document composed of title and contents.
            methods: Comma-separated format methods, e.g.: "del_break,neurips_preprint".

        Returns:
            dict: Formatted document composed of title and contents.
        """
        method_names = methods.split(",")
        formatted_document = copy.deepcopy(document)
        for name in method_names:
            if name != "":
                formatted_document = self.funcs[name](formatted_document)
        return formatted_document

    @staticmethod
    def batch(document, format_func):
        for content in document["contents"]:
            format_texts = [format_func(text) for text in content["texts"]]
            content["texts"] = format_texts
        return document

    @staticmethod
    def del_break(document):
        """
        ex: hoge\nfuga -> hoge fuga
        """
        regex = re.compile("\\n")

        def func(s):
            return regex.sub(" ", s)

        return Formatter.batch(document, func)

    @staticmethod
    def neurips_preprint(document):
        """
        ex: hoge \n34\n -> hoge
        """
        regex = re.compile("\\n\d+\\n")

        def func(s):
            return regex.sub("", s)

        return Formatter.batch(document, func)
