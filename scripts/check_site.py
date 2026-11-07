#!/usr/bin/env python3
"""Validate standalone browser scripts without fetching external dependencies."""
import subprocess,tempfile
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Scripts(HTMLParser):
    def __init__(self):
        super().__init__();self.reading=False;self.blocks=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script' and not dict(attrs).get('src'):
            self.reading=True;self.blocks.append('')
    def handle_endtag(self,tag):
        if tag=='script':self.reading=False
    def handle_data(self,data):
        if self.reading:self.blocks[-1]+=data
def main():
    for page in ('index.html','search.html'):
        parser=Scripts();parser.feed((ROOT/page).read_text(encoding='utf-8'))
        if not parser.blocks:raise SystemExit('No browser scripts in '+page)
        for n,source in enumerate(parser.blocks):
            with tempfile.NamedTemporaryFile(mode='w',suffix='.js',encoding='utf-8') as fp:
                fp.write(source);fp.flush()
                subprocess.run(['node','--check',fp.name],check=True)
            print(page,'script',n,'syntax OK')
if __name__=='__main__':main()
