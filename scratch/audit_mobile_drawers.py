from bs4 import BeautifulSoup
import glob

html_files = ['victim-home.html', 'checkin.html', 'distress-trends.html', 'case-journey.html', 'my-support.html', 'resources.html', 'privacy-consent.html']
for fpath in html_files:
    with open(fpath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    drawer = soup.find('div', class_='mobile-menu-drawer')
    if drawer:
        links = [f"{a.text.strip()} ({a.get('href')})" for a in drawer.find_all('a')]
        print(f"{fpath} mobile drawer: {len(links)} links -> {links}")
