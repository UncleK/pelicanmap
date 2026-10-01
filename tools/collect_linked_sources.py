from archive_io import ROOT, WEB, AUDIT, records, text_for, fetch_batch
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re

jobs = []
for row in records().values():
    if row['kind'] != 'x-api':
        continue
    tweet = json.loads(text_for(row['url'])).get('tweet') or {}
    for t in [tweet, tweet.get('quote') or {}]:
        if t.get('replying_to_status'):
            jobs.append('https://api.fxtwitter.com/status/' + t['replying_to_status'])
        card = t.get('card') or {}
        if card.get('url'):
            jobs.append(card['url'])
        jobs.extend(re.findall(r'https://[^\s<>]+', t.get('text', '')))

for url in ['https://baiguangru.vip/2026/09/09/pelican-bike-model-regression-check.html']:
    soup = BeautifulSoup(text_for(url), 'html.parser')
    jobs.extend(urljoin(url, x['src']) for x in soup.select('iframe[src]'))
for name, base in [('rustfisher-compare.html', 'https://en.rustfisher.com/'), ('ohmyopus.html', 'https://ohmyopus.com/')]:
    soup = BeautifulSoup((WEB / 'demos/sites' / name).read_text(encoding='utf-8'), 'html.parser')
    jobs.extend(urljoin(base, x['src']) for x in soup.select('iframe[src]'))
    jobs.extend(x['href'] for x in soup.select('a[href]') if x['href'].startswith('https://gist.github.com/'))
fetch_batch(jobs, kind='linked-source')
print('Fetched linked sources:', len(set(jobs)))
