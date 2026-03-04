#!/usr/bin/env python3
"""
Scraping hebdomadaire Signatory Vintage Islay — France
Scrappe whisky.fr et prestigewhisky.fr, met à jour data/bottles.json
puis régénère index.html avec les données à jour embarquées.
"""
import json, re, time, urllib.request, urllib.error
from datetime import date

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
}

ISLAY_DISTILLERIES = ['bowmore','caol-ila','ardbeg','laphroaig','bunnahabhain','kilchoman','bruichladdich','port-charlotte','ardnahoe']

def fetch(url, delay=1.0):
    time.sleep(delay)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  ⚠️  {url}: {e}")
        return ""

def is_islay(text):
    text = text.lower()
    return 'islay' in text or any(d in text for d in ISLAY_DISTILLERIES)

def parse_price(text):
    m = re.search(r'(\d{2,4})[,.]?(\d{0,2})\s*€', text)
    if m:
        try:
            return float(m.group(1) + ('.' + m.group(2) if m.group(2) else ''))
        except:
            return None
    return None

# ---- LMDW whisky.fr ----
def scrape_lmdw():
    print("\n📡 Scraping La Maison du Whisky (whisky.fr)...")
    index_url = "https://www.whisky.fr/en/independant-bottlers/signatory-vintage.html"
    html = fetch(index_url)
    # Extraire les URLs de bouteilles Islay
    urls = re.findall(r'https://www\.whisky\.fr/en/[a-z0-9\-]+\.html', html)
    urls = list(dict.fromkeys(urls))  # dédoublonner
    results = []
    for url in urls:
        if not any(d in url for d in ISLAY_DISTILLERIES):
            continue
        page = fetch(url, 0.8)
        if not page: continue
        title_m = re.search(r'<title>([^<]+)</title>', page)
        price_m = re.search(r'([\d]+[,.]?[\d]*)\s*€\s*\n.*?i\.e\.', page, re.S)
        if not price_m:
            price_m = re.search(r'class="[^"]*price[^"]*"[^>]*>([\d]+[,.]?[\d]*)\s*€', page)
        in_stock = not re.search(r'out.of.stock|rupture|sold.out|épuisé', page, re.I)
        abv_m = re.search(r'(\d{2,3}[,.]?\d?)%', page)
        vintage_m = re.search(r'\b(19|20)\d{2}\b', url)
        age_m = re.search(r'(\d{1,2})[- ]?ans|(\d{1,2})[- ]?year', page, re.I)
        if title_m:
            name = title_m.group(1).strip().replace(' - 0.7 - Scotland', '').replace(' - Scotland', '')
            price = None
            if price_m:
                try: price = float(price_m.group(1).replace(',','.'))
                except: pass
            # Déterminer distillerie
            dist = None
            url_lower = url.lower()
            if 'bowmore' in url_lower: dist = 'Bowmore'
            elif 'caol-ila' in url_lower: dist = 'Caol Ila'
            elif 'ardbeg' in url_lower: dist = 'Ardbeg'
            elif 'laphroaig' in url_lower: dist = 'Laphroaig'
            elif 'bunnahabhain' in url_lower: dist = 'Bunnahabhain'
            elif 'kilchoman' in url_lower: dist = 'Kilchoman'
            elif 'bruichladdich' in url_lower: dist = 'Bruichladdich'
            if not dist: continue
            results.append({
                'distillery': dist,
                'name': name,
                'subtitle': 'Signatory Vintage',
                'vintage': int(vintage_m.group(0)) if vintage_m else None,
                'age': int(age_m.group(1) or age_m.group(2)) if age_m else None,
                'abv': float(abv_m.group(1).replace(',','.')) if abv_m else None,
                'cask': None,
                'peated': True,
                'price': price,
                'shipping': 'offert dès 130€',
                'in_stock': in_stock,
                'site': 'La Maison du Whisky',
                'url': url,
                'note': 'Signatory Vintage · non chillfiltered'
            })
            stock_str = '✅' if in_stock else '❌'
            price_str = f"{price}€" if price else "N/A"
            print(f"  {stock_str} {dist} — {name[:50]} — {price_str}")
    return results

# ---- Prestige Whisky ----
def scrape_prestige():
    print("\n📡 Scraping Prestige Whisky (prestigewhisky.fr)...")
    index_url = "https://www.prestigewhisky.fr/35-signatory"
    html = fetch(index_url)
    urls = re.findall(r'https://www\.prestigewhisky\.fr/whisky-ecossais/[a-z0-9\-]+\.html', html)
    urls = list(dict.fromkeys(urls))
    results = []
    for url in urls:
        page = fetch(url, 0.8)
        if not is_islay(page) and not is_islay(url): continue
        title_m = re.search(r'<title>([^|<]+)', page)
        price_m = re.search(r'(\d{2,4})[,.](\d{2})\s*€|(\d{2,4})\s*€', page)
        in_stock = not re.search(r'épuisé|out.of.stock|rupture', page, re.I)
        abv_m = re.search(r'(\d{2,3}[,.]?\d?)%', page)
        vintage_m = re.search(r'\b(19|20)\d{2}\b', url)
        age_m = re.search(r'(\d{1,2})[- ]?ans', page, re.I)
        if title_m:
            name = title_m.group(1).strip()
            price = None
            if price_m:
                try:
                    if price_m.group(1): price = float(price_m.group(1) + '.' + price_m.group(2))
                    else: price = float(price_m.group(3))
                except: pass
            dist = None
            page_lower = page.lower()
            if 'bowmore' in page_lower or 'bowmore' in url: dist = 'Bowmore'
            elif 'caol ila' in page_lower or 'caol-ila' in url: dist = 'Caol Ila'
            elif 'ardbeg' in page_lower: dist = 'Ardbeg'
            elif 'laphroaig' in page_lower: dist = 'Laphroaig'
            elif 'bunnahabhain' in page_lower: dist = 'Bunnahabhain'
            if not dist: continue
            results.append({
                'distillery': dist,
                'name': name[:80],
                'subtitle': 'Signatory Vintage',
                'vintage': int(vintage_m.group(0)) if vintage_m else None,
                'age': int(age_m.group(1)) if age_m else None,
                'abv': float(abv_m.group(1).replace(',','.')) if abv_m else None,
                'cask': None,
                'peated': True,
                'price': price,
                'shipping': 'offert dès 130€',
                'in_stock': in_stock,
                'site': 'Prestige Whisky',
                'url': url,
                'note': 'Signatory Vintage'
            })
            stock_str = '✅' if in_stock else '❌'
            price_str = f"{price}€" if price else "N/A"
            print(f"  {stock_str} {dist} — {name[:50]} — {price_str}")
    return results

# ---- Build index.html ----
def rebuild_html(bottles):
    print("\n🔨 Régénération index.html...")
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    # Remplacer le bloc DATA dans le JS
    new_data = json.dumps({
        'updated': str(date.today()),
        'bottles': bottles
    }, ensure_ascii=False, indent=2)
    # Remplacer entre "const DATA = {" et le ";" suivant
    pattern = r'(const DATA = )\{[\s\S]+?\}(\s*;)'
    replacement = r'\g<1>' + new_data + r'\2'
    new_html = re.sub(pattern, replacement, html)
    if new_html == html:
        print("  ⚠️  Pattern DATA non trouvé dans index.html — vérifier le template")
    else:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(new_html)
        print("  ✅ index.html régénéré")

def main():
    today = str(date.today())
    print(f"🔄 Mise à jour Signatory Islay — {today}")

    # Charger données existantes (fallback si scraping vide)
    with open('data/bottles.json', 'r', encoding='utf-8') as f:
        existing = json.load(f)

    # Scraper
    bottles = []
    try:
        bottles += scrape_lmdw()
    except Exception as e:
        print(f"  ❌ LMDW échoué : {e}")

    try:
        bottles += scrape_prestige()
    except Exception as e:
        print(f"  ❌ Prestige échoué : {e}")

    # Si scraping vide → garder existant, juste mettre à jour la date
    if not bottles:
        print("\n⚠️  Scraping vide — conservation des données existantes")
        bottles = existing['bottles']

    # Dédoublonner par URL
    seen_urls = set()
    unique = []
    for b in bottles:
        if b['url'] not in seen_urls:
            seen_urls.add(b['url'])
            unique.append(b)
    # Trier : en stock d'abord, puis par distillerie, puis par prix
    unique.sort(key=lambda b: (not b.get('in_stock'), b.get('distillery',''), b.get('price') or 9999))

    # Sauvegarder JSON
    data = {'updated': today, 'source': f'Scrape automatique — {today}', 'bottles': unique}
    with open('data/bottles.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n✅ data/bottles.json — {len(unique)} bouteilles ({sum(1 for b in unique if b.get('in_stock'))} en stock)")

    # Régénérer HTML
    rebuild_html(unique)

if __name__ == '__main__':
    main()
