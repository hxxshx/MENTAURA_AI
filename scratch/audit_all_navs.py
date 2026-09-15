from bs4 import BeautifulSoup
import glob

html_files = glob.glob('*.html')
for fpath in sorted(html_files):
    with open(fpath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    pill = soup.find('nav', class_='nav-pill')
    if pill:
        links = [f"{a.text.strip()} ({a.get('href')})" for a in pill.find_all('a')]
        print(f"{fpath}: {len(links)} links -> {links}")
