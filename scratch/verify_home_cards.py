from bs4 import BeautifulSoup

with open('victim-home.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

cards = soup.find_all('div', class_='help-card-2')
print(f'Found {len(cards)} help-card-2 elements.')
for idx, c in enumerate(cards):
    title = c.find('h3', class_='help-card-title')
    print(f'Card {idx+1}: {title.text if title else "None"}')

hero_btns = soup.find('div', class_='victim-hero-ctas').find_all('a')
print(f'Hero buttons count: {len(hero_btns)}')
for b in hero_btns:
    print(f' - {b.text.strip()} -> {b.get("href")}')

threat_btn = soup.find(id='homeReportIntimidationBtn')
print(f'homeReportIntimidationBtn present: {threat_btn is not None}')
