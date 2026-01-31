#!/usr/bin/env python3
import requests
import json
import os
import sys
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup

print("🚀 Starting IPTV Hunter...")

# Fallback sources (известные рабочие репозитории)
FALLBACK_URLS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/uk.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/de.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/fr.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/it.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/es.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ua.m3u",
]

def get_random_headers():
    """Rotate User-Agents to avoid blocking"""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
    ]
    return {
        "User-Agent": random.choice(agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }

def search_duckduckgo():
    """Try to search via DuckDuckGo"""
    print("🔍 Trying DuckDuckGo...")
    try:
        query = "site:raw.githubusercontent.com iptv m3u"
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        
        r = requests.get(url, headers=get_random_headers(), timeout=30)
        print(f"   Status: {r.status_code}")
        
        if r.status_code != 200:
            return []
            
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        
        # Look for result links
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if "raw.githubusercontent.com" in href and ".m3u" in href:
                urls.append(href)
                print(f"   Found: {href[:60]}...")
        
        return list(set(urls))
    except Exception as e:
        print(f"   Error: {e}")
        return []

def search_bing():
    """Fallback to Bing search"""
    print("🔍 Trying Bing...")
    try:
        query = "site:raw.githubusercontent.com iptv ext:m3u"
        url = f"https://www.bing.com/search?q={query.replace(' ', '+')}&count=30"
        
        r = requests.get(url, headers=get_random_headers(), timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        urls = []
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "raw.githubusercontent.com" in href and ".m3u" in href:
                urls.append(href)
        
        return list(set(urls))[:20]
    except Exception as e:
        print(f"   Error: {e}")
        return []

def get_all_sources():
    """Combine search results with fallback"""
    sources = []
    
    # Try search engines
    sources.extend(search_duckduckgo())
    time.sleep(2)
    sources.extend(search_bing())
    
    # Add fallbacks if search failed
    if len(sources) < 5:
        print("⚠️  Search found few results, using fallback sources...")
        sources.extend(FALLBACK_URLS)
    
    # Clean URLs
    clean_urls = []
    for url in sources:
        # Remove tracking parameters
        url = url.split("?")[0]
        if url not in clean_urls:
            clean_urls.append(url)
    
    print(f"📋 Total sources to process: {len(clean_urls)}")
    return clean_urls[:25]  # Limit to 25

def parse_m3u(url):
    """Parse M3U playlist"""
    try:
        print(f"📡 Processing: {url[:50]}...")
        r = requests.get(url, headers=get_random_headers(), timeout=15)
        
        if r.status_code != 200:
            print(f"   ❌ HTTP {r.status_code}")
            return []
        
        content = r.text
        if "#EXTM3U" not in content:
            print(f"   ❌ Not a valid M3U")
            return []
        
        channels = []
        lines = content.split("\n")
        current = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("#EXTINF:"):
                # Parse name
                if "," in line:
                    name = line.split(",")[-1].strip()
                else:
                    name = "Channel"
                
                # Detect country from attributes or name
                country = "INT"
                low = line.lower()
                if any(x in low for x in ["tvg-country=\"ru\"", "tvg-country=\"russia\""]): country = "RU"
                elif any(x in low for x in ["tvg-country=\"us\"", "tvg-country=\"usa\""]): country = "US"
                elif any(x in low for x in ["tvg-country=\"uk\"", "tvg-country=\"gb\""]): country = "UK"
                elif any(x in low for x in ["tvg-country=\"de\""]): country = "DE"
                elif any(x in low for x in ["tvg-country=\"fr\""]): country = "FR"
                elif any(x in low for x in ["tvg-country=\"it\""]): country = "IT"
                elif any(x in low for x in ["tvg-country=\"es\""]): country = "ES"
                elif any(x in low for x in ["tvg-country=\"ua\""]): country = "UA"
                # Guess from name if not in attributes
                elif any(x in low for x in [" ru ", "russia", "russian", "россия"]): country = "RU"
                elif any(x in low for x in [" usa ", " us ", "american"]): country = "US"
                
                current = {"name": name, "country": country}
            
            elif line.startswith("http") and current:
                current["url"] = line
                channels.append(current.copy())
                current = {}
        
        print(f"   ✅ {len(channels)} channels")
        return channels
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:50]}")
        return []

def main():
    # Get sources
    urls = get_all_sources()
    
    if not urls:
        print("❌ No sources found at all!")
        # Create empty files to prevent workflow failure
        os.makedirs("playlists", exist_ok=True)
        create_html([], {})
        with open("metadata.json", "w") as f:
            json.dump({"total": 0, "countries": 0, "error": "No sources"}, f)
        sys.exit(0)  # Don't fail workflow
    
    # Parse all
    all_channels = []
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}]", end=" ")
        channels = parse_m3u(url)
        all_channels.extend(channels)
        time.sleep(0.5)  # Be nice to servers
    
    # Deduplicate by URL
    seen = set()
    unique = []
    for ch in all_channels:
        if ch["url"] not in seen:
            seen.add(ch["url"])
            unique.append(ch)
    
    print(f"\n🔄 Unique channels: {len(unique)}")
    
    if not unique:
        print("❌ No valid channels found")
        create_html([], {})
        with open("metadata.json", "w") as f:
            json.dump({"total": 0, "countries": 0}, f)
        sys.exit(0)
    
    # Group by country
    by_country = {}
    for ch in unique:
        co = ch.get("country", "INT")
        by_country.setdefault(co, []).append(ch)
    
    # Create output
    os.makedirs("playlists", exist_ok=True)
    
    for country, chans in by_country.items():
        fname = f"playlists/iptv_{country.lower()}.m3u"
        with open(fname, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for c in chans:
                f.write(f'#EXTINF:-1 tvg-name="{c["name"]}" group-title="{country}",{c["name"]}\n')
                f.write(f'{c["url"]}\n')
        print(f"💾 {fname}: {len(chans)} channels")
    
    # Create HTML
    create_html(unique, by_country)
    
    # Metadata
    meta = {
        "total": len(unique),
        "countries": len(by_country),
        "countries_list": list(by_country.keys()),
        "time": datetime.now().isoformat()
    }
    with open("metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"\n🎉 Success! {meta['total']} channels from {meta['countries']} countries")

def create_html(channels, by_country):
    """Generate HTML files"""
    total = len(channels)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    countries = len(by_country)
    
    flags = {
        "RU": "🇷🇺", "US": "🇺🇸", "UK": "🇬🇧", "DE": "🇩🇪", 
        "FR": "🇫🇷", "IT": "🇮🇹", "ES": "🇪🇸", "UA": "🇺🇦", "INT": "🌍"
    }
    
    # Index with iframe
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IPTV Aggregator</title>
<style>
body{{margin:0;padding:20px;font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;color:white}}
.container{{max-width:900px;margin:0 auto;background:rgba(255,255,255,0.95);padding:30px;border-radius:20px;color:#333;text-align:center}}
.iframe-box{{width:100%;height:450px;border:3px solid #667eea;border-radius:15px;margin:20px 0;background:#f5f5f5}}
.btn{{display:inline-block;padding:15px 30px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;text-decoration:none;border-radius:25px;font-weight:bold;margin:10px}}
.stats{{font-size:28px;color:#667eea;margin:10px 0;font-weight:bold}}
.update{{margin-top:20px;color:#999;font-size:14px}}
</style>
</head>
<body>
<div class="container">
<h1>🌍 IPTV Aggregator</h1>
<div class="stats">{total} каналов | {countries} стран</div>
<iframe class="iframe-box" src="full.html" frameborder="0"></iframe>
<br>
<a href="full.html" class="btn">🔗 Открыть полную версию</a>
<a href="iptv-playlists.zip" class="btn" download>📦 Скачать ZIP</a>
<div class="update">Обновлено: {now} UTC</div>
</div>
</body>
</html>""")
    
    # Full page
    with open("full.html", "w", encoding="utf-8") as f:
        f.write("""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Полный каталог IPTV</title>
<style>
body{margin:0;padding:20px;font-family:Arial;background:#1a1a2e;color:white}
.container{max-width:1200px;margin:0 auto}
.back{display:inline-block;margin-bottom:20px;color:#64ffda;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
.card{background:#16213e;padding:20px;border-radius:15px;border:1px solid #0f3460;text-align:center}
.flag{font-size:40px;margin-bottom:10px}
.count{font-size:32px;color:#64ffda;font-weight:bold}
a.download{display:inline-block;margin-top:15px;padding:10px 20px;background:#e94560;color:white;text-decoration:none;border-radius:20px}
</style>
</head>
<body>
<div class="container">
<a href="index.html" class="back">← Назад на главную</a>
<h1>📺 Все плейлисты</h1>
<div class="grid">""")
        
        for country in sorted(by_country.keys()):
            count = len(by_country[country])
            flag = flags.get(country, "📡")
            f.write(f'<div class="card"><div class="flag">{flag}</div><h2>{country}</h2><div class="count">{count}</div><p>каналов</p><a href="playlists/iptv_{country.lower()}.m3u" class="download" download>Скачать M3U</a></div>')
        
        f.write(f"""</div>
<div style="margin-top:40px;padding:30px;background:#16213e;border-radius:15px;line-height:1.8">
<h2>📱 Как смотреть</h2>
<ul style="text-align:left">
<li><b>VLC:</b> Медиа → Открыть файл → выбрать M3U</li>
<li><b>Android:</b> IPTV Pro, Perfect Player, Televizo</li>
<li><b>iOS:</b> VLC, nPlayer</li>
<li><b>Smart TV:</b> OTT Player, SS IPTV</li>
</ul>
<p>Всего каналов: {total} | Обновлено: {now}</p>
</div>
</div>
</body>
</html>""")

if __name__ == "__main__":
    main()
