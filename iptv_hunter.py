#!/usr/bin/env python3
import requests
import json
import os
import sys
from datetime import datetime
from bs4 import BeautifulSoup

print("🚀 Starting IPTV Channel Hunt...")

# Config
SEARCH_URL = "https://html.duckduckgo.com/html/"
SEARCH_QUERY = "site:raw.githubusercontent.com iptv m3u"
MAX_SOURCES = 30
TIMEOUT = 15

def search_playlists():
    """Search for IPTV M3U playlists"""
    print("🔍 Searching...")
    urls = []
    try:
        params = {'q': SEARCH_QUERY}
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(SEARCH_URL, params=params, headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'raw.githubusercontent.com' in href and '.m3u' in href:
                urls.append(href.split('?')[0])
        
        return list(set(urls))[:MAX_SOURCES]
    except Exception as e:
        print(f"Search error: {e}")
        return []

def parse_m3u(url):
    """Parse M3U file"""
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={'User-Agent': 'VLC/3.0'})
        if '#EXTM3U' not in r.text:
            return []
        
        channels = []
        lines = r.text.split('\n')
        current = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                name = line.split(',')[-1] if ',' in line else 'Unknown'
                country = 'INT'
                low = line.lower()
                if any(x in low for x in ['ru','russia']): country = 'RU'
                elif any(x in low for x in ['us','usa']): country = 'US'
                elif any(x in low for x in ['uk','british']): country = 'UK'
                elif any(x in low for x in ['de','german']): country = 'DE'
                elif any(x in low for x in ['fr','france']): country = 'FR'
                current = {'name': name, 'country': country}
            elif line.startswith('http') and current:
                current['url'] = line
                channels.append(current.copy())
                current = {}
        return channels
    except:
        return []

def main():
    # Search
    urls = search_playlists()
    if not urls:
        print("❌ No sources found")
        sys.exit(1)
    
    print(f"Found {len(urls)} sources")
    
    # Parse
    all_ch = []
    for url in urls:
        print(f"Parsing: {url[:50]}...")
        ch = parse_m3u(url)
        if ch:
            all_ch.extend(ch)
    
    if not all_ch:
        print("❌ No channels found")
        sys.exit(1)
    
    # Deduplicate
    seen = set()
    unique = []
    for c in all_ch:
        if c['url'] not in seen:
            seen.add(c['url'])
            unique.append(c)
    
    print(f"✅ Total unique: {len(unique)}")
    
    # Group by country
    by_country = {}
    for c in unique:
        co = c.get('country', 'INT')
        by_country.setdefault(co, []).append(c)
    
    # Save playlists
    os.makedirs('playlists', exist_ok=True)
    for country, chans in by_country.items():
        fname = f'playlists/{country}.m3u'
        with open(fname, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for c in chans:
                f.write(f'#EXTINF:-1,{c["name"]}\n{c["url"]}\n')
        print(f"💾 {country}: {len(chans)} channels")
    
    # Create HTML
    create_html(unique, by_country)
    
    # Metadata
    meta = {
        'total': len(unique),
        'countries': len(by_country),
        'time': datetime.now().isoformat()
    }
    with open('metadata.json', 'w') as f:
        json.dump(meta, f)
    
    print("🎉 Done!")

def create_html(channels, by_country):
    total = len(channels)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Main page
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>IPTV</title>
<style>
body{{font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);margin:0;padding:20px;color:white}}
.container{{max-width:900px;margin:0 auto;background:white;color:#333;padding:30px;border-radius:15px;text-align:center}}
.iframe{{width:100%;height:400px;border:2px solid #667eea;border-radius:10px;margin:20px 0}}
.btn{{display:inline-block;padding:12px 25px;background:#667eea;color:white;text-decoration:none;border-radius:20px}}
</style></head>
<body>
<div class="container">
<h1>🌍 IPTV Aggregator</h1>
<h2>{total} channels | {len(by_country)} countries</h2>
<iframe class="iframe" src="full.html"></iframe>
<br><a href="full.html" class="btn">Full Version</a>
<p>Updated: {now}</p>
</div></body></html>''')
    
    # Full page
    with open('full.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Full</title>
<style>body{font-family:Arial;background:#1a1a2e;color:white;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px}
.card{background:#16213e;padding:15px;border-radius:10px}
a{color:#64ffda}</style></head>
<body>
<a href="index.html" style="color:#64ffda">← Back</a>
<h1>All Playlists</h1>
<div class="grid">''')
        
        for c, ch in by_country.items():
            f.write(f'<div class="card"><h2>{c}</h2><p>{len(ch)} channels</p>')
            f.write(f'<a href="playlists/{c}.m3u" download>Download</a></div>')
        
        f.write('</div></body></html>')

if __name__ == "__main__":
    main()
