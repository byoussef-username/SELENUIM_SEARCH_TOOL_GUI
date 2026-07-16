import argparse
import csv
import re
import sys
import time
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# CONFIGURATION DES SITES (sélecteurs vérifiés sur de vrais fichiers HTML)
# ---------------------------------------------------------------------------
SITES = {
    "pcmaroc": {
        "name": "Pcmaroc",
        "search_url": "https://pcmaroc.com/?s={query}&post_type=product",
        "wait_selector": "div.wd-product",
        "item_selector": "div.wd-product",
        "title_selector": "h3.wd-entities-title a",
        "link_selector": "h3.wd-entities-title a",
        "price_selectors": [
            "ins .woocommerce-Price-amount.amount bdi",
            ".price .woocommerce-Price-amount.amount bdi",
        ],
        "price_pick": "first",
        "base_url": "https://pcmaroc.com",
    },
    "electroplanet": {
        "name": "Electroplanet",
        "search_url": "https://www.electroplanet.ma/recherche?q={query}",
        "wait_selector": "li.product-item, .product-item-info",
        "item_selector": "li.product-item",
        "title_selector": "a.product-item-link",
        "link_selector": "a.product-item-link",
        "price_selectors": [
            ".special-price .price",
            ".price-box .price",
        ],
        "price_pick": "last",
        "base_url": "https://www.electroplanet.ma",
    },
    "pcmarrakech": {
        "name": "Pcmarrakech",
        "search_url": "https://pcmarrakech.com/recherche?controller=search&s={query}",
        "wait_selector": "div.product-miniature",
        "item_selector": "div.product-miniature",
        "title_selector": "h5.product-name a, h3.product-name a",
        "link_selector": "h5.product-name a, h3.product-name a",
        "price_selectors": [
            "span.product-price",
        ],
        "price_pick": "first",
        "base_url": "https://pcmarrakech.com",
    },
}



def make_driver():
    """Lance Chrome en mode headless (sans fenêtre visible)."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1400,1000")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def parse_price(text):
    """Extrait un nombre (float) d'un texte de prix du genre '8 499 DH' ou '6 900,00 MAD'."""
    if not text:
        return None
    cleaned = text.replace("\xa0", " ").strip()
    # Garder chiffres, espaces, virgules, points
    cleaned = re.sub(r"[^\d,\. ]", "", cleaned)
    cleaned = cleaned.replace(" ", "")
    # Format  :"6900,00" virgule = décimal  "8 499"  pas de décimale
    if "," in cleaned and cleaned.count(",") == 1 and len(cleaned.split(",")[-1]) == 2:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    match = re.search(r"\d+(\.\d+)?", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def title_matches(title, query_words):
    title_lower = title.lower()
    return all(word.lower() in title_lower for word in query_words)


def fetch_site_results(driver, site_cfg, query):
    url = site_cfg["search_url"].format(query=quote_plus(query))
    print(f"[{site_cfg['name']}] Chargement: {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, site_cfg["wait_selector"]))
        )
    except TimeoutException:
        print(
            f"[{site_cfg['name']}] Aucun résultat trouvé (ou sélecteur à corriger).")
        return None

    time.sleep(1)
    return driver.page_source


def extract_price(item, price_selectors, pick):
    """Essaie chaque sélecteur de prix dans l'ordre; renvoie le premier ou dernier match."""
    for selector in price_selectors:
        matches = item.select(selector)
        if matches:
            chosen = matches[0] if pick == "first" else matches[-1]
            return parse_price(chosen.get_text(strip=True))
    return None


def parse_results(html, site_cfg):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(site_cfg["item_selector"])
    results = []

    for item in items:
        title_el = item.select_one(site_cfg["title_selector"])
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        price = extract_price(
            item, site_cfg["price_selectors"], site_cfg["price_pick"])

        link_el = item.select_one(site_cfg["link_selector"])
        link = link_el.get("href", "") if link_el else ""
        if link and link.startswith("/"):
            link = site_cfg["base_url"] + link

        results.append({"titre": title, "prix": price, "lien": link})

    return results


def scrape_site(driver, site_cfg, query):
    html = fetch_site_results(driver, site_cfg, query)
    if html is None:
        return []
    raw_results = parse_results(html, site_cfg)
    print(f"[{site_cfg['name']}] {len(raw_results)} produit(s) brut(s) trouvé(s).")
    return raw_results


def filter_results(results, query_words, min_price, max_price):
    filtered = []
    for r in results:
        if not title_matches(r["titre"], query_words):
            continue
        if r["prix"] is None:
            continue
        if min_price is not None and r["prix"] < min_price:
            continue
        if max_price is not None and r["prix"] > max_price:
            continue
        filtered.append(r)
    return filtered


def write_csv(all_results, output_path):
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["site", "titre", "prix", "lien"])
        writer.writeheader()
        for row in all_results:
            writer.writerow(row)



def main():
    parser = argparse.ArgumentParser(
        description="Comparateur de prix Pcmaroc / Electroplanet / Pcmarrakech")
    parser.add_argument(
        "query", help='Terme de recherche, ex: "pc portable hp"')
    parser.add_argument("--min-price", type=float,
                        default=None, help="Prix minimum")
    parser.add_argument("--max-price", type=float,
                        default=None, help="Prix maximum")
    parser.add_argument("--output", default="resultats.csv",
                        help="Nom du fichier CSV de sortie")
    parser.add_argument(
        "--sites",
        default="pcmaroc,electroplanet,pcmarrakech",
        help="Liste de sites à interroger, séparés par des virgules",
    )
    args = parser.parse_args()

    query_words = args.query.split()
    requested_sites = [s.strip() for s in args.sites.split(",")]

    driver = make_driver()
    all_results = []

    try:
        for site_key in requested_sites:
            site_cfg = SITES.get(site_key)
            if not site_cfg:
                print(f"Site inconnu ignoré: {site_key}")
                continue

            raw_results = scrape_site(driver, site_cfg, args.query)
            kept = filter_results(raw_results, query_words,
                                  args.min_price, args.max_price)
            print(
                f"[{site_cfg['name']}] {len(kept)} produit(s) retenu(s) après filtrage.\n")

            for r in kept:
                all_results.append({"site": site_cfg["name"], **r})
    finally:
        driver.quit()

    if not all_results:
        print("Aucun résultat ne correspond aux critères sur les sites interrogés.")
        sys.exit(0)

    write_csv(all_results, args.output)
    print(
        f"Terminé. {len(all_results)} résultat(s) écrit(s) dans {args.output}")


if __name__ == "__main__":
    main()
