import time
import requests
from bs4 import BeautifulSoup
import json

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,el;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def enhanced_private_detection(tiles):
    """Enhanced method to detect private listings"""
    print(f"\n=== ENHANCED PRIVATE DETECTION FOR {len(tiles)} TILES ===")
    
    private_listings = []
    
    for i, tile in enumerate(tiles, 1):
        print(f"\nTile {i} Analysis:")
        
        # Get all text content for analysis
        tile_text = tile.get_text().lower()
        tile_html = str(tile).lower()
        
        indicators = {
            'private_class': False,
            'greek_private': False,
            'no_logo': False,
            'private_text': False,
            'svg_indicators': [],
            'contact_patterns': [],
            'other_patterns': []
        }
        
        # 1. Check for private-related classes
        if tile.select_one('[class*="private"]') or tile.select_one('[class*="ιδιώτ"]'):
            indicators['private_class'] = True
        
        # 2. Check for Greek private indicators
        greek_terms = ['ιδιώτη', 'ιδιώτης', 'ιδιωτικό', 'άτομο']
        for term in greek_terms:
            if term in tile_text or term in tile_html:
                indicators['greek_private'] = True
                break
        
        # 3. Check if there's NO agency logo (could indicate private)
        logos = tile.select('.tile__logo')
        if not logos:
            indicators['no_logo'] = True
        
        # 4. Look for private-related text patterns
        private_patterns = ['private', 'owner', 'by owner', 'direct', 'personal']
        for pattern in private_patterns:
            if pattern in tile_text:
                indicators['private_text'] = True
                indicators['other_patterns'].append(pattern)
        
        # 5. Analyze SVG use elements more thoroughly
        uses = tile.select('use')
        for use in uses:
            href = use.get('href', '') + ' ' + use.get('xlink:href', '')
            if any(term in href.lower() for term in ['private', 'person', 'individual', 'owner']):
                indicators['svg_indicators'].append(href.strip())
        
        # 6. Look for contact patterns that might indicate private sellers
        contact_elements = tile.select('[class*="contact"], [class*="phone"], [class*="tel"]')
        for el in contact_elements:
            el_text = el.get_text().strip()
            if el_text and len(el_text) < 50:  # Short contact info might be private
                indicators['contact_patterns'].append(el_text)
        
        # 7. Check data attributes
        data_attrs = []
        for attr in tile.attrs:
            if attr.startswith('data-') and 'private' in str(tile.attrs[attr]).lower():
                data_attrs.append(f"{attr}={tile.attrs[attr]}")
        
        # Scoring system
        score = 0
        if indicators['private_class']: score += 3
        if indicators['greek_private']: score += 3
        if indicators['no_logo']: score += 1
        if indicators['private_text']: score += 2
        if indicators['svg_indicators']: score += 2
        if len(indicators['contact_patterns']) > 0: score += 1
        
        print(f"  Score: {score}/12")
        
        # Report findings
        if score > 0:
            print(f"  Potential private indicators:")
            if indicators['private_class']:
                print(f"    ✓ Private class found")
            if indicators['greek_private']:
                print(f"    ✓ Greek private terms found")
            if indicators['no_logo']:
                print(f"    ✓ No agency logo")
            if indicators['private_text']:
                print(f"    ✓ Private text patterns: {indicators['other_patterns']}")
            if indicators['svg_indicators']:
                print(f"    ✓ SVG indicators: {indicators['svg_indicators']}")
            if indicators['contact_patterns']:
                print(f"    ✓ Contact patterns: {indicators['contact_patterns']}")
            
            # Get listing details
            link = tile.select_one("a.tile__link") or tile.select_one("a[href*='/aggelies/']")
            if link:
                href = link.get("href", "")
                if href.startswith('/'):
                    href = "https://www.spitogatos.gr" + href
                
                private_listings.append({
                    'tile_number': i,
                    'score': score,
                    'url': href,
                    'indicators': indicators,
                    'title': link.get('title', 'No title')
                })
                print(f"    Link: {href}")
        else:
            print(f"  No private indicators detected")
    
    return private_listings

def test_multiple_pages():
    """Test multiple pages to find private listings"""
    
    test_urls = [
        "https://www.spitogatos.gr/pwliseis-katoikies/glyfada",
        "https://www.spitogatos.gr/enikiaseis-katoikies/glyfada", 
        "https://www.spitogatos.gr/pwliseis-katoikies/athens",
        "https://www.spitogatos.gr/pwliseis-katoikies/thessaloniki",
        "https://www.spitogatos.gr/pwliseis-katoikies/patras",
    ]
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_private_listings = []
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"TESTING: {url}")
        print(f"{'='*60}")
        
        try:
            resp = session.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                tiles = soup.select(".tile")
                print(f"Found {len(tiles)} tiles")
                
                if tiles:
                    private_listings = enhanced_private_detection(tiles)
                    all_private_listings.extend(private_listings)
                    
                    if private_listings:
                        print(f"\n🎉 FOUND {len(private_listings)} POTENTIAL PRIVATE LISTINGS!")
                        for listing in private_listings:
                            print(f"  - Score {listing['score']}: {listing['url']}")
                else:
                    print("No tiles found on this page")
            else:
                print(f"Failed to access page: {resp.status_code}")
                
        except Exception as e:
            print(f"Error accessing {url}: {e}")
        
        time.sleep(2)  # Be respectful to the server
    
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total pages tested: {len(test_urls)}")
    print(f"Total potential private listings found: {len(all_private_listings)}")
    
    if all_private_listings:
        print(f"\nTop candidates (highest scores):")
        sorted_listings = sorted(all_private_listings, key=lambda x: x['score'], reverse=True)
        for listing in sorted_listings[:10]:  # Top 10
            print(f"  Score {listing['score']}: {listing['url']}")
    
    return all_private_listings

if __name__ == "__main__":
    # Run the enhanced detection on multiple pages
    private_listings = test_multiple_pages()
    
    if private_listings:
        print(f"\n✅ SUCCESS! Found {len(private_listings)} potential private listings")
        print("You can now focus your scraping on these URLs or similar patterns")
    else:
        print(f"\n❌ No private listings found across all tested pages")
        print("This might indicate that:")
        print("1. Private listings are rare on Spitogatos")
        print("2. They use a different indicator system")
        print("3. Private listings might be in a different section of the site")