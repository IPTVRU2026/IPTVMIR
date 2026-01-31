#!/usr/bin/env python3
import requests
import json
import os
import sys
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

print("🚀 Starting IPTV Channel Hunt...")

# Fallback sources (если поиск не сработает)
FALLBACK_URLS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/uk.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/de.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/fr.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/it.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/es.m3u",
]

# EPG sources по странам
EPG_URLS = {
    'RU': 'https://iptvx.one/epg/epg.xml.gz',
    'US': 'https://epgshare01.online/epgshare01/epg_ripper_US1.xml.gz',
    'UK': 'https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz',
    'DE': 'https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz',
    'FR': 'https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz',
    'IT': 'https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz',
    'ES': 'https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz',
    'INT': 'https://epgshare01.online/epgshare01/epg_ripper_ALL.xml.gz'
}

SEARCH_URL = "https://html.duckduckgo.com/html/"
SEARCH_QUERY = "site:raw.githubusercontent.com iptv m3u"
MAX_SOURCES = 30
TIMEOUT = 15

def search_playlists():
    """Search for IPTV M3U playlists"""
    print("🔍 Searching DuckDuckGo...")
    urls = []
    try:
        params = {'q': SEARCH_QUERY}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(SEARCH_URL, params=params, headers=headers, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'raw.githubusercontent.com' in href and '.m3u' in href:
                clean = href.split('?')[0]
                if clean not in urls:
                    urls.append(clean)
        
        print(f"   Found {len(urls)} URLs")
        return urls[:MAX_SOURCES]
    except Exception as e:
        print(f"   Search error: {e}")
        return []

def parse_m3u(url):
    """Parse M3U with metadata"""
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
                # Parse metadata
                name = line.split(',')[-1] if ',' in line else 'Unknown'
                
                # Extract group-title
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else 'General'
                
                # Extract tvg-logo
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                logo = logo_match.group(1) if logo_match else ''
                
                # Extract tvg-id
                id_match = re.search(r'tvg-id="([^"]*)"', line)
                tvg_id = id_match.group(1) if id_match else ''
                
                # Detect country
                country = 'INT'
                low = line.lower()
                if any(x in low for x in ['tvg-country="ru"', 'ru ', 'russia']): country = 'RU'
                elif any(x in low for x in ['tvg-country="us"', 'usa', ' united states']): country = 'US'
                elif any(x in low for x in ['tvg-country="uk"', 'united kingdom', 'british']): country = 'UK'
                elif any(x in low for x in ['tvg-country="de"', 'germany', 'deutsch']): country = 'DE'
                elif any(x in low for x in ['tvg-country="fr"', 'france']): country = 'FR'
                elif any(x in low for x in ['tvg-country="it"', 'italy']): country = 'IT'
                elif any(x in low for x in ['tvg-country="es"', 'spain']): country = 'ES'
                
                current = {
                    'name': name,
                    'group': group,
                    'logo': logo,
                    'tvg_id': tvg_id,
                    'country': country
                }
            elif line.startswith('http') and current:
                current['url'] = line
                channels.append(current.copy())
                current = {}
        return channels
    except Exception as e:
        print(f"   Parse error: {e}")
        return []

def main():
    # Try search first, fallback to known sources
    urls = search_playlists()
    
    if not urls or len(urls) < 3:
        print("⚠️  Search failed, using fallback sources...")
        urls = FALLBACK_URLS
    
    print(f"📡 Processing {len(urls)} sources...")
    
    # Parse all
    all_ch = []
    for url in urls:
        print(f"   {url[:50]}...")
        ch = parse_m3u(url)
        if ch:
            all_ch.extend(ch)
            print(f"      +{len(ch)} channels")
        time.sleep(0.5)  # Be nice to servers
    
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
    
    print(f"\n✅ Unique channels: {len(unique)}")
    
    # Group by country
    by_country = {}
    for c in unique:
        co = c.get('country', 'INT')
        by_country.setdefault(co, []).append(c)
    
    # Save playlists with EPG and groups
    os.makedirs('playlists', exist_ok=True)
    for country, chans in by_country.items():
        fname = f'playlists/iptv_{country.lower()}.m3u'
        epg = EPG_URLS.get(country, EPG_URLS['INT'])
        
        with open(fname, 'w', encoding='utf-8') as f:
            # Write header with EPG
            f.write(f'#EXTM3U url-tvg="{epg}"\n')
            
            for c in chans:
                # Write with metadata
                extinf = '#EXTINF:-1'
                if c['tvg_id']: extinf += f' tvg-id="{c["tvg_id"]}"'
                extinf += f' tvg-name="{c["name"]}"'
                if c['logo']: extinf += f' tvg-logo="{c["logo"]}"'
                extinf += f' group-title="{c["group"]}"'
                extinf += f',{c["name"]}\n'
                
                f.write(extinf)
                f.write(f'{c["url"]}\n')
        
        print(f"💾 {country}: {len(chans)} channels (EPG: {country in EPG_URLS})")
    
    # Create HTML
    create_html(unique, by_country)
    
    # Metadata
    meta = {
        'total': len(unique),
        'countries': {k: len(v) for k, v in by_country.items()},
        'time': datetime.now().isoformat()
    }
    with open('metadata.json', 'w') as f:
        json.dump(meta, f, indent=2)
    
    print(f"\n🎉 Done! {meta['total']} channels in {len(by_country)} countries")

def create_html(channels, by_country):
    total = len(channels)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    countries = len(by_country)
    
    flags = {
        'RU': '🇷🇺', 'US': '🇺🇸', 'UK': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷',
        'IT': '🇮🇹', 'ES': '🇪🇸', 'INT': '🌍'
    }
    
    # Index with iframe
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IPTV Aggregator</title>
<style>
body{{margin:0;padding:20px;font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;color:white}}
.container{{max-width:900px;margin:0 auto;background:rgba(255,255,255,0.95);padding:30px;border-radius:20px;color:#333;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,0.3)}}
.iframe{{width:100%;height:400px;border:3px solid #667eea;border-radius:10px;margin:20px 0;background:#f5f5f5}}
.btn{{display:inline-block;padding:15px 30px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;text-decoration:none;border-radius:25px;font-weight:bold;margin:10px}}
.stats{{font-size:24px;color:#667eea;margin-bottom:20px}}
.update{{margin-top:20px;color:#666;font-size:14px}}
</style>
</head>
<body>
<div class="container">
<h1>🌍 IPTV Aggregator</h1>
<div class="stats">📺 {total} каналов | 🌐 {countries} стран</div>
<iframe class="iframe" src="full.html"></iframe>
<br>
<a href="full.html" class="btn">🔗 Открыть полную версию</a>
<a href="iptv-playlists.zip" class="btn" download>📦 Скачать ZIP</a>
<div class="update">Обновлено: {now} UTC | EPG + Группы включены</div>
</div>
</body>
</html>''')
    
    # Full page with instructions
    with open('full.html', 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Полный каталог IPTV</title>
<style>
body{{margin:0;padding:20px;font-family:Arial;background:#1a1a2e;color:white;line-height:1.6}}
.container{{max-width:1200px;margin:0 auto}}
.back{{display:inline-block;margin-bottom:20px;color:#64ffda;text-decoration:none;font-size:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;margin:20px 0}}
.card{{background:#16213e;padding:25px;border-radius:15px;text-align:center;border:1px solid #0f3460}}
.flag{{font-size:40px;margin-bottom:10px}}
.count{{font-size:32px;color:#64ffda;font-weight:bold;margin:10px 0}}
.download{{display:inline-block;margin-top:15px;padding:10px 25px;background:#e94560;color:white;text-decoration:none;border-radius:20px}}
.info{{margin-top:40px;padding:30px;background:#16213e;border-radius:15px}}
.info h2{{color:#64ffda;margin-bottom:20px}}
.info ul{{text-align:left;margin-left:20px}}
.info li{{margin-bottom:10px}}
</style>
</head>
<body>
<div class="container">
<a href="index.html" class="back">← Назад на главную</a>
<h1>📺 Все плейлисты IPTV</h1>
<div class="grid">''')
        
        for country in sorted(by_country.keys()):
            count = len(by_country[country])
            flag = flags.get(country, '📡')
            f.write(f'''<div class="card">
<div class="flag">{flag}</div>
<h2>{country}</h2>
<div class="count">{count}</div>
<p>каналов</p>
<a href="playlists/iptv_{country.lower()}.m3u" class="download" download>Скачать M3U</a>
</div>''')
        
        f.write(f'''</div>
<div class="info">
<h2>📱 Как смотреть</h2>
<ul>
<li><b>VLC Media Player:</b> Медиа → Открыть файл → выберите M3U. Телепрограмма (EPG) подгрузится автоматически.</li>
<li><b>Android:</b> IPTV Pro, Perfect Player, Televizo. В настройках включите EPG если не загрузилось.</li>
<li><b>iOS:</b> VLC, nPlayer. Поддерживают плейлисты с группами.</li>
<li><b>Smart TV:</b> OTT Player, SS IPTV — загрузите M3U по ссылке или с USB.</li>
<li><b>Kodi:</b> PVR IPTV Simple Client → загрузите M3U, укажите XMLTV URL для EPG.</li>
</ul>
<p style="margin-top:20px"><b>Всего каналов:</b> {total} | <b>Обновлено:</b> {now}</p>
<p style="font-size:0.9em;color:#888">В плейлистах: группы каналов, логотипы (если есть в источнике), EPG</p>
</div>
</div>
</body>
</html>''')

if __name__ == "__main__":
    main()
