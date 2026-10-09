import os
import re
import unittest

from tests.common import ROOT

SKIP_DIRS = {"case_package", ".git", ".cache", "__pycache__", "node_modules"}
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.S)


def markdown_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(base, f)


class TestInternalLinks(unittest.TestCase):
    def test_relative_links_resolve(self):
        problems = []
        checked = 0
        for p in markdown_files():
            text = open(p, encoding="utf-8").read()
            text = FENCE_RE.sub("", text)  # drop fenced code blocks
            for target in LINK_RE.findall(text):
                t = target.strip().strip("<>")
                if t.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                t = t.split("#", 1)[0]
                if not t:
                    continue
                checked += 1
                dest = os.path.normpath(os.path.join(os.path.dirname(p), t))
                if not os.path.exists(dest):
                    problems.append(f"{os.path.relpath(p, ROOT)} -> {target}")
        self.assertEqual(problems, [], "broken relative links:\n" + "\n".join(problems))
        self.assertGreater(checked, 20, "expected many internal links to check")


if __name__ == "__main__":
    unittest.main()
