#!/usr/bin/env python3
import requests
import json
import os
import sys
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

print("🚀 Starting IPTV Hunter Pro...")

# Fallback sources (надежные репозитории)
FALLBACK_URLS = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ru.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/uk.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/de.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/fr.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/it.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/es.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/pl.m3u",
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ua.m3u",
]

EPG_URLS = {
    'RU': 'https://iptvx.one/epg/epg.xml.gz',
    'US': 'https://epgshare01.online/epgshare01/epg_ripper_US1.xml.gz',
    'UK': 'https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz',
    'DE': 'https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz',
    'FR': 'https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz',
    'IT': 'https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz',
    'ES': 'https://epgshare01.online/epgshare01/epg_ripper_ES1.xml.gz',
    'UA': 'https://epg.sharecenter.io/ua.xml',
    'PL': 'https://epgshare01.online/epgshare01/epg_ripper_PL1.xml.gz',
    'INT': 'https://epgshare01.online/epgshare01/epg_ripper_ALL.xml.gz'
}

def search_github():
    """Поиск свежих источников через DuckDuckGo"""
    print("🔍 Ищу свежие плейлисты...")
    urls = []
    try:
        query = "site:raw.githubusercontent.com iptv m3u"
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        r = requests.get(url, headers=headers, timeout=25)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        for link in soup.select('a.result__a'):
            href = link.get('href', '')
            if 'raw.githubusercontent.com' in href and '.m3u' in href:
                clean = href.split('?')[0]
                if clean not in urls:
                    urls.append(clean)
        
        print(f"   Найдено {len(urls)} новых источников")
        return urls[:15]  # Берем первые 15 чтобы не перегружать
    except Exception as e:
        print(f"   Ошибка поиска: {e}")
        return []

def check_source_alive(url):
    """Быстрая проверка - работает ли источник (первые 3 канала)"""
    try:
        r = requests.get(url, timeout=15, headers={'User-Agent': 'VLC/3.0'})
        if r.status_code == 200 and '#EXTM3U' in r.text:
            # Считаем количество http ссылок
            http_count = len([line for line in r.text.split('\n') if line.strip().startswith('http')])
            if http_count > 0:
                return True
    except:
        pass
    return False

def parse_m3u(url):
    """Парсит плейлист с сохранением групп и метаданных"""
    try:
        r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
        content = r.text
        
        if '#EXTM3U' not in content:
            return []
        
        channels = []
        lines = content.split('\n')
        current = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('#EXTINF:'):
                # Имя канала
                name = line.split(',')[-1] if ',' in line else 'Unknown Channel'
                
                # Группа (категория)
                group_match = re.search(r'group-title="([^"]*)"', line)
                group = group_match.group(1) if group_match else 'General'
                
                # Логотип
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                logo = logo_match.group(1) if logo_match else ''
                
                # ID для EPG
                id_match = re.search(r'tvg-id="([^"]*)"', line)
                tvg_id = id_match.group(1) if id_match else ''
                
                # Страна (определение по тегам или названию)
                country = 'INT'  # International по умолчанию
                low = line.lower()
                
                if any(x in low for x in ['tvg-country="ru"', 'russia', ' рус ', 'россия']): country = 'RU'
                elif any(x in low for x in ['tvg-country="us"', 'usa', 'america']): country = 'US'
                elif any(x in low for x in ['tvg-country="uk"', 'united kingdom', 'british']): country = 'UK'
                elif any(x in low for x in ['tvg-country="de"', 'germany', 'deutschland']): country = 'DE'
                elif any(x in low for x in ['tvg-country="fr"', 'france', 'française']): country = 'FR'
                elif any(x in low for x in ['tvg-country="it"', 'italy', 'italia']): country = 'IT'
                elif any(x in low for x in ['tvg-country="es"', 'spain', 'españa']): country = 'ES'
                elif any(x in low for x in ['tvg-country="ua"', 'ukraine', 'украина']): country = 'UA'
                elif any(x in low for x in ['tvg-country="pl"', 'poland', 'polska']): country = 'PL'
                
                # Если в атрибутах не нашли, пробуем по названию
                if country == 'INT':
                    name_low = name.lower()
                    if any(x in name_low for x in [' ru', 'russia', 'russian']): country = 'RU'
                    elif any(x in name_low for x in [' us', 'usa', 'american']): country = 'US'
                    elif any(x in name_low for x in [' uk', 'british', 'england']): country = 'UK'
                    elif any(x in name_low for x in [' fr', 'france', 'french']): country = 'FR'
                
                current = {
                    'name': name,
                    'group': group,
                    'logo': logo,
                    'tvg_id': tvg_id,
                    'country': country,
                    'url': ''  # Заполним позже
                }
                
            elif line.startswith('http') and current:
                current['url'] = line
                if line.startswith(('http://', 'https://')):
                    channels.append(current.copy())
                current = {}
        
        return channels
        
    except Exception as e:
        print(f"   Ошибка парсинга: {e}")
        return []

def main():
    # 1. Ищем свежие источники
    search_urls = search_github()
    
    # 2. Добавляем fallback если мало найдено
    if len(search_urls) < 3:
        print("⚠️  Мало источников в поиске, добавляю надежные репозитории...")
        urls = list(set(FALLBACK_URLS + search_urls))
    else:
        urls = search_urls + FALLBACK_URLS[:3]  # Свежие + 3 надежных
    
    print(f"\n📡 Обработка {len(urls)} источников...")
    
    # 3. Парсим все источники
    all_channels = []
    for i, url in enumerate(urls, 1):
        print(f"   [{i}/{len(urls)}] {url[:50]}...")
        ch = parse_m3u(url)
        if ch:
            print(f"      +{len(ch)} каналов")
            all_channels.extend(ch)
        time.sleep(0.3)  # Небольшая пауза
    
    if not all_channels:
        print("❌ Каналы не найдены!")
        sys.exit(1)
    
    print(f"\n📊 Найдено: {len(all_channels)} каналов (до проверки дубликатов)")
    
    # 4. Убираем дубликаты по URL
    seen_urls = set()
    unique_channels = []
    for c in all_channels:
        url = c['url']
        if url not in seen_urls:
            seen_urls.add(url)
            unique_channels.append(c)
    
    print(f"🔄 Уникальных каналов: {len(unique_channels)}")
    
    # 5. Группировка по странам
    by_country = {}
    for c in unique_channels:
        co = c.get('country', 'INT')
        by_country.setdefault(co, []).append(c)
    
    print(f"🌍 Стран: {len(by_country)} ({', '.join(sorted(by_country.keys()))})")
    
    # 6. Создание папок и сохранение M3U
    os.makedirs('playlists', exist_ok=True)
    
    for country, channels in by_country.items():
        fname = f'playlists/iptv_{country.lower()}.m3u'
        epg_url = EPG_URLS.get(country, EPG_URLS['INT'])
        
        with open(fname, 'w', encoding='utf-8') as f:
            # Заголовок с EPG
            f.write(f'#EXTM3U url-tvg="{epg_url}" x-tvg-url="{epg_url}"\n')
            
            for c in channels:
                # Строка EXTINF с метаданными
                extinf = f'#EXTINF:-1'
                
                if c['tvg_id']:
                    extinf += f' tvg-id="{c["tvg_id"]}"'
                
                extinf += f' tvg-name="{c["name"]}"'
                
                if c['logo']:
                    extinf += f' tvg-logo="{c["logo"]}"'
                
                extinf += f' group-title="{c["group"]}"'
                extinf += f',{c["name"]}\n'
                
                f.write(extinf)
                f.write(f'{c["url"]}\n')
        
        print(f"💾 {fname}: {len(channels)} каналов (групп: {len(set(ch['group'] for ch in channels))})")
    
    # 7. Создание HTML сайта
    create_website(unique_channels, by_country)
    
    # 8. Метаданные
    meta = {
        'total': len(unique_channels),
        'countries': {k: len(v) for k, v in by_country.items()},
        'groups': list(set(c['group'] for c in unique_channels)),
        'time': datetime.now().isoformat()
    }
    
    with open('metadata.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Готово! {meta['total']} каналов по странам")

def create_website(channels, by_country):
    """Создает красивый сайт с iframe"""
    total = len(channels)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    countries = len(by_country)
    
    flags = {
        'RU': '🇷🇺', 'US': '🇺🇸', 'UK': '🇬🇧', 'DE': '🇩🇪', 
        'FR': '🇫🇷', 'IT': '🇮🇹', 'ES': '🇪🇸', 'UA': '🇺🇦', 
        'PL': '🇵🇱', 'INT': '🌍'
    }
    
    # index.html - главная с окошком
    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IPTV Aggregator - {total} каналов</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }}
        .container {{ 
            max-width: 1000px; 
            margin: 0 auto; 
            background: rgba(255,255,255,0.98);
            border-radius: 20px;
            padding: 40px;
            color: #333;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{ text-align: center; color: #667eea; margin-bottom: 10px; font-size: 2.5em; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em; }}
        .stats {{ 
            display: flex; 
            justify-content: center; 
            gap: 30px; 
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        .stat {{ 
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px 30px;
            border-radius: 15px;
            text-align: center;
        }}
        .stat-number {{ font-size: 36px; font-weight: bold; display: block; }}
        .stat-label {{ font-size: 14px; opacity: 0.9; }}
        
        .preview-box {{ 
            width: 100%; 
            height: 500px; 
            border: 3px solid #667eea;
            border-radius: 15px;
            margin: 30px 0;
            background: #f8f9fa;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        
        .buttons {{ text-align: center; margin: 30px 0; }}
        .btn {{ 
            display: inline-block;
            padding: 15px 35px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            text-decoration: none;
            border-radius: 30px;
            font-weight: bold;
            font-size: 16px;
            margin: 10px;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        .btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6); }}
        
        .features {{ 
            text-align: center; 
            margin: 20px 0;
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .badge {{ 
            display: inline-block;
            padding: 8px 16px;
            background: #10b981;
            color: white;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        
        .update {{ 
            text-align: center; 
            color: #999; 
            margin-top: 20px; 
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌍 IPTV Aggregator</h1>
        <p class="subtitle">Автоматически обновляемые плейлисты со всего мира</p>
        
        <div class="stats">
            <div class="stat">
                <span class="stat-number">{total}</span>
                <span class="stat-label">Каналов</span>
            </div>
            <div class="stat">
                <span class="stat-number">{countries}</span>
                <span class="stat-label">Стран</span>
            </div>
            <div class="stat">
                <span class="stat-number">24/7</span>
                <span class="stat-label">Автообновление</span>
            </div>
        </div>
        
        <div class="features">
            <span class="badge">✓ Группы каналов</span>
            <span class="badge">✓ EPG (телепрограмма)</span>
            <span class="badge">✓ Логотипы</span>
        </div>
        
        <div class="preview-box">
            <iframe src="full.html" title="IPTV Preview"></iframe>
        </div>
        
        <div class="buttons">
            <a href="full.html" class="btn">🔗 Открыть полную версию сайта</a>
            <a href="iptv-playlists.zip" class="btn" download>📦 Скачать все плейлисты (ZIP)</a>
        </div>
        
        <div class="update">
            <p>🤖 Последнее обновление: {now} UTC | GitHub Actions</p>
            <p style="margin-top: 5px; font-size: 11px;">
                Плейлисты обновляются каждые 6 часов. Каналы отсортированы по странам и категориям.
            </p>
        </div>
    </div>
</body>
</html>'''
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    # full.html - полная версия
    full = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Полный каталог IPTV - {total} каналов</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        .back {{
            display: inline-block;
            margin-bottom: 25px;
            color: #64ffda;
            text-decoration: none;
            font-size: 16px;
            padding: 8px 16px;
            border: 1px solid #64ffda;
            border-radius: 20px;
            transition: all 0.3s;
        }}
        .back:hover {{ background: rgba(100, 255, 218, 0.1); }}
        
        h1 {{ font-size: 2.2em; margin-bottom: 10px; color: #e2e8f0; }}
        .subtitle {{ color: #94a3b8; margin-bottom: 30px; }}
        
        .grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
            gap: 25px;
            margin: 30px 0;
        }}
        .card {{ 
            background: #1e293b; 
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            border: 1px solid #334155;
            transition: all 0.3s;
        }}
        .card:hover {{
            transform: translateY(-5px);
            border-color: #667eea;
            box-shadow: 0 10px 40px rgba(0,0,0,0.4);
        }}
        .flag {{ font-size: 50px; margin-bottom: 10px; display: block; }}
        .country {{ font-size: 24px; color: #60a5fa; font-weight: bold; margin-bottom: 5px; }}
        .epg-badge {{
            display: inline-block;
            background: #10b981;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            margin: 10px 0;
        }}
        .epg-badge.disabled {{ background: #6b7280; }}
        .count {{ font-size: 42px; color: #34d399; font-weight: bold; margin: 15px 0; }}
        .count-label {{ color: #94a3b8; font-size: 14px; }}
        .download {{
            display: inline-block;
            margin-top: 20px;
            padding: 12px 30px;
            background: #3b82f6;
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: bold;
            transition: all 0.2s;
        }}
        .download:hover {{ background: #2563eb; transform: scale(1.05); }}
        
        .info {{
            background: #1e293b;
            border-radius: 20px;
            padding: 35px;
            margin-top: 40px;
            border: 1px solid #334155;
        }}
        .info h2 {{ color: #60a5fa; margin-bottom: 25px; font-size: 1.8em; }}
        .info h3 {{ color: #fbbf24; margin: 25px 0 15px 0; }}
        .info ul {{ margin-left: 25px; }}
        .info li {{ margin-bottom: 12px; color: #cbd5e1; }}
        .info strong {{ color: #fbbf24; }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 25px;
            color: #64748b;
            border-top: 1px solid #334155;
        }}
    </style>
</head>
<body>
    <div class="container">
        <a href="index.html" class="back">← Назад на главную</a>
        
        <h1>📺 Полный каталог IPTV</h1>
        <p class="subtitle">Все каналы отсортированы по странам с поддержкой EPG</p>
        
        <div class="grid">'''
    
    for country in sorted(by_country.keys()):
        count = len(by_country[country])
        flag = flags.get(country, '🌐')
        has_epg = country in EPG_URLS
        epg_class = "epg-badge" if has_epg else "epg-badge disabled"
        epg_text = "📅 EPG доступно" if has_epg else "EPG недоступно"
        
        full += f'''
        <div class="card">
            <span class="flag">{flag}</span>
            <div class="country">{country}</div>
            <span class="{epg_class}">{epg_text}</span>
            <div class="count">{count}</div>
            <div class="count-label">телеканалов</div>
            <a href="playlists/iptv_{country.lower()}.m3u" class="download" download>
                📥 Скачать M3U
            </a>
        </div>'''
    
    full += f'''
        </div>
        
        <div class="info">
            <h2>📱 Как смотреть IPTV</h2>
            
            <h3>💻 На компьютере:</h3>
            <ul>
                <li><strong>VLC Media Player:</strong> Медиа → Открыть файл → выберите M3U. 
                    Телепрограмма (EPG) загрузится автоматически если доступна для страны.</li>
                <li><strong>Kodi:</strong> Установите PVR IPTV Simple Client → Настройки → 
                    Укажите путь к M3U файлу.</li>
            </ul>
            
            <h3>📱 На телефоне:</h3>
            <ul>
                <li><strong>Android:</strong> IPTV Pro, Perfect Player, Televizo</li>
                <li><strong>iOS (iPhone/iPad):</strong> VLC, nPlayer, GSE Smart IPTV</li>
            </ul>
            
            <h3>📺 На телевизоре:</h3>
            <ul>
                <li><strong>Samsung/LG Smart TV:</strong> OTT Player, SS IPTV</li>
                <li><strong>Android TV:</strong> Приложения из Play Market (IPTV, Televizo)</li>
            </ul>
            
            <h3 style="color: #ef4444;">⚠️ Важная информация:</h3>
            <ul>
                <li>Плейлисты обновляются <strong>автоматически каждые 6 часов</strong></li>
                <li>Каналы разделены по <strong>группам</strong> (News, Sport, Movies и т.д.)</li>
                <li>Для активации телепрограммы (EPG) может потребоваться настройка в плеере</li>
                <li>Если канал не работает - попробуйте обновить плейлист позже</li>
            </ul>
        </div>
        
        <div class="footer">
            <p><strong>Всего каналов:</strong> {total} | <strong>Стран:</strong> {countries}</p>
            <p>Обновлено: {now} UTC | Создано автоматически</p>
        </div>
    </div>
</body>
</html>'''
    
    with open('full.html', 'w', encoding='utf-8') as f:
        f.write(full)

if __name__ == "__main__":
    main()
