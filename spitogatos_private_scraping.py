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
        
        # 7. Extract and analyze image information
        image_info = extract_tile_image_info(tile)
        
        # 8. Check data attributes
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
        
        # Additional scoring for image alt text
        if image_info.get('alt'):
            alt_lower = image_info['alt'].lower()
            if any(term in alt_lower for term in ['ιδιώτη', 'ιδιώτης', 'private']):
                score += 2
                indicators['other_patterns'].append('private_in_image_alt')
        
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
            
            # Show image information
            if image_info:
                print(f"    📷 Image info:")
                if image_info.get('listing_id'):
                    print(f"       - Listing ID: {image_info['listing_id']}")
                if image_info.get('alt'):
                    print(f"       - Alt text: {image_info['alt'][:100]}...")
                if image_info.get('parsed_alt'):
                    parsed = image_info['parsed_alt']
                    print(f"       - Property: {parsed.get('property_type', 'N/A')}, {parsed.get('size', 'N/A')}, {parsed.get('price', 'N/A')}")
            
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
                    'title': link.get('title', 'No title'),
                    'image_info': image_info
                })
                print(f"    Link: {href}")
        else:
            print(f"  No private indicators detected")
            
            # Still show image info for debugging even if no private indicators
            if image_info and image_info.get('alt'):
                print(f"    📷 Image alt: {image_info['alt'][:80]}...")
    
    return private_listings

def find_max_page(base_url, session, max_check=10):
    """Find the maximum page number for a location"""
    print(f"  Finding max page for {base_url}...")
    
    # Try some high page numbers to find the limit
    test_pages = [354, 300, 250, 200, 150, 100, 50, 25]
    
    for page_num in test_pages:
        test_url = f"{base_url}/selida_{page_num}"
        try:
            resp = session.get(test_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                tiles = soup.select(".tile")
                if len(tiles) > 0:
                    print(f"    Max page found: {page_num} (has {len(tiles)} listings)")
                    return page_num
            time.sleep(0.5)
        except:
            continue
    
    print(f"    Max page: 1 (only first page accessible)")
    return 1

def test_comprehensive_pages(max_pages_per_location=354, delay=1):
    """Test all pages up to specified maximum for each location"""
    
    base_locations = [
        "https://www.spitogatos.gr/pwliseis-katoikies/glyfada",
        "https://www.spitogatos.gr/enikiaseis-katoikies/glyfada", 
        "https://www.spitogatos.gr/pwliseis-katoikies/athens",
        "https://www.spitogatos.gr/pwliseis-katoikies/thessaloniki",
        "https://www.spitogatos.gr/pwliseis-katoikies/patras",
    ]
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_private_listings = []
    total_pages_processed = 0
    
    for base_url in base_locations:
        print(f"\n{'='*80}")
        print(f"PROCESSING LOCATION: {base_url}")
        print(f"{'='*80}")
        
        # Find actual max page for this location
        actual_max_page = find_max_page(base_url, session)
        pages_to_check = min(max_pages_per_location, actual_max_page)
        
        print(f"Will check pages 1 to {pages_to_check}")
        location_private_count = 0
        
        for page_num in range(1, pages_to_check + 1):
            if page_num == 1:
                url = base_url
            else:
                url = f"{base_url}/selida_{page_num}"
            
            print(f"\nPage {page_num}/{pages_to_check}: {url}")
            
            try:
                resp = session.get(url)
                total_pages_processed += 1
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    tiles = soup.select(".tile")
                    
                    if len(tiles) == 0:
                        print(f"  No tiles found - might have reached end at page {page_num}")
                        break
                    
                    print(f"  Found {len(tiles)} tiles", end=" ")
                    
                    # Quick check for private indicators (simplified for speed)
                    private_listings = quick_private_check(tiles, page_num, url)
                    
                    if private_listings:
                        print(f"-> 🎉 {len(private_listings)} PRIVATE LISTINGS FOUND!")
                        all_private_listings.extend(private_listings)
                        location_private_count += len(private_listings)
                        
                        # Show the private listings found
                        for listing in private_listings:
                            print(f"     - Score {listing['score']}: {listing['url']}")
                    else:
                        print("-> No private listings")
                        
                elif resp.status_code == 404:
                    print(f"  Page {page_num} not found - reached end")
                    break
                else:
                    print(f"  HTTP {resp.status_code} - skipping")
                    
            except Exception as e:
                print(f"  Error: {e}")
                
            # Progress update every 10 pages
            if page_num % 10 == 0:
                print(f"  Progress: {page_num}/{pages_to_check} pages checked, {location_private_count} private listings found so far")
            
            time.sleep(delay)  # Be respectful to the server
        
        print(f"\nLocation Summary: {location_private_count} private listings found across {page_num} pages")
    
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE SCAN COMPLETE")
    print(f"{'='*80}")
    print(f"Total pages processed: {total_pages_processed}")
    print(f"Total locations scanned: {len(base_locations)}")
    print(f"Total private listings found: {len(all_private_listings)}")
    
    if all_private_listings:
        print(f"\n🎉 SUCCESS! Found private listings:")
        
        # Group by location
        by_location = {}
        for listing in all_private_listings:
            location = listing['url'].split('/')[4] if len(listing['url'].split('/')) > 4 else 'unknown'
            if location not in by_location:
                by_location[location] = []
            by_location[location].append(listing)
        
        for location, listings in by_location.items():
            print(f"\n{location.upper()}: {len(listings)} private listings")
            # Show top 5 for each location
            sorted_listings = sorted(listings, key=lambda x: x['score'], reverse=True)
            for listing in sorted_listings[:5]:
                print(f"  Score {listing['score']}: {listing['url']}")
        
        # Save results to file
        save_results_to_file(all_private_listings)
        
    else:
        print(f"\n❌ No private listings found across all {total_pages_processed} pages")
        print("This suggests private listings might be:")
        print("1. Very rare on this platform")
        print("2. Located in different sections")
        print("3. Using different indicators than expected")
    
    return all_private_listings

def extract_tile_image_info(tile):
    """Extract image information from a tile"""
    image_info = {}
    
    # Look for the main tile image
    img = tile.select_one('img[id*="tile__image"]') or tile.select_one('img[alt*="Πώληση"], img[alt*="Ενοικίαση"]')
    
    if img:
        image_info = {
            'id': img.get('id', ''),
            'src': img.get('src', ''),
            'data_src': img.get('data-src', ''),
            'alt': img.get('alt', ''),
            'width': img.get('width', ''),
            'height': img.get('height', ''),
        }
        
        # Extract listing ID from image ID if possible
        img_id = img.get('id', '')
        if 'tile__image__' in img_id:
            try:
                listing_id = img_id.split('tile__image__')[1].split('__')[0]
                image_info['listing_id'] = listing_id
            except:
                image_info['listing_id'] = ''
        
        # Parse alt text for property details
        alt_text = img.get('alt', '')
        if alt_text:
            image_info['parsed_alt'] = parse_alt_text(alt_text)
    
    return image_info

def parse_alt_text(alt_text):
    """Parse the Greek alt text to extract property information"""
    parsed = {
        'transaction_type': '',  # Πώληση/Ενοικίαση
        'property_type': '',     # Κατοικία/Διαμέρισμα etc
        'size': '',              # τ.μ.
        'price': '',             # €
        'location': ''           # Area name
    }
    
    try:
        # Split by commas
        parts = [part.strip() for part in alt_text.split(',')]
        
        for part in parts:
            if 'Πώληση' in part:
                parsed['transaction_type'] = 'Πώληση'
            elif 'Ενοικίαση' in part:
                parsed['transaction_type'] = 'Ενοικίαση'
            elif 'τ.μ.' in part:
                parsed['size'] = part
            elif '€' in part:
                parsed['price'] = part
            elif any(prop_type in part for prop_type in ['Κατοικία', 'Διαμέρισμα', 'Μονοκατοικία', 'Μαιζονέτα']):
                parsed['property_type'] = part
            elif '(' in part and ')' in part:
                # Likely location in parentheses
                parsed['location'] = part
    except:
        pass
    
    return parsed

def quick_private_check(tiles, page_num, page_url):
    """Faster private listing detection for bulk scanning with image info"""
    private_listings = []
    
    for i, tile in enumerate(tiles, 1):
        tile_text = tile.get_text().lower()
        tile_html = str(tile).lower()
        
        score = 0
        indicators = []
        
        # Extract image information
        image_info = extract_tile_image_info(tile)
        
        # Quick checks for efficiency
        if tile.select_one('[class*="private"]'):
            score += 3
            indicators.append("private_class")
        
        greek_terms = ['ιδιώτη', 'ιδιώτης', 'ιδιωτικό']
        if any(term in tile_text or term in tile_html for term in greek_terms):
            score += 3
            indicators.append("greek_private")
        
        if not tile.select('.tile__logo'):
            score += 1
            indicators.append("no_logo")
        
        # Check SVG quickly
        uses = tile.select('use')
        for use in uses:
            href = str(use.get('href', '')) + str(use.get('xlink:href', ''))
            if 'private' in href.lower() or 'person' in href.lower():
                score += 2
                indicators.append("svg_private")
                break
        
        # Additional check: image alt text for private indicators
        if image_info.get('alt'):
            alt_lower = image_info['alt'].lower()
            if any(term in alt_lower for term in ['ιδιώτη', 'ιδιώτης', 'private']):
                score += 2
                indicators.append("private_in_alt")
        
        if score > 0:  # Lower threshold for bulk scanning
            link = tile.select_one("a.tile__link") or tile.select_one("a[href*='/aggelies/']")
            if link:
                href = link.get("href", "")
                if href.startswith('/'):
                    href = "https://www.spitogatos.gr" + href
                
                private_listings.append({
                    'tile_number': i,
                    'page_number': page_num,
                    'page_url': page_url,
                    'score': score,
                    'url': href,
                    'indicators': indicators,
                    'title': link.get('title', 'No title'),
                    'image_info': image_info
                })
    
    return private_listings

def save_results_to_file(private_listings):
    """Save results to a JSON file"""
    filename = f"private_listings_{int(time.time())}.json"
    
    # Convert to serializable format
    results = {
        'scan_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_found': len(private_listings),
        'listings': private_listings
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {filename}")
    except Exception as e:
        print(f"\n❌ Could not save results: {e}")

def test_sample_pages(pages_per_location=5):
    """Test just a few pages per location for quick results"""
    print("Running SAMPLE test (few pages per location)...")
    return test_comprehensive_pages(max_pages_per_location=pages_per_location, delay=0.5)

if __name__ == "__main__":
    print("🏠 SPITOGATOS PRIVATE LISTING COMPREHENSIVE SCANNER")
    print("=" * 60)
    
    choice = input("""
Choose scanning mode:
1. SAMPLE (5 pages per location - quick test)
2. COMPREHENSIVE (up to 354 pages per location - full scan)
3. CUSTOM (specify number of pages)

Enter choice (1/2/3): """).strip()
    
    if choice == "1":
        print("\n🚀 Starting SAMPLE scan...")
        private_listings = test_sample_pages(pages_per_location=5)
        
    elif choice == "2":
        print("\n🚀 Starting COMPREHENSIVE scan...")
        print("⚠️  This will check up to 354 pages per location")
        print("⚠️  This may take 30+ minutes and make 1000+ requests")
        confirm = input("Continue? (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y']:
            private_listings = test_comprehensive_pages(max_pages_per_location=354, delay=1)
        else:
            print("Scan cancelled.")
            private_listings = []
            
    elif choice == "3":
        try:
            pages = int(input("Enter number of pages per location: "))
            delay = float(input("Enter delay between requests (seconds, recommended: 0.5-2): "))
            print(f"\n🚀 Starting CUSTOM scan ({pages} pages per location)...")
            private_listings = test_comprehensive_pages(max_pages_per_location=pages, delay=delay)
        except ValueError:
            print("Invalid input. Using sample mode instead.")
            private_listings = test_sample_pages(pages_per_location=5)
    
    else:
        print("Invalid choice. Using sample mode instead.")
        private_listings = test_sample_pages(pages_per_location=5)
    
    # Final summary
    if private_listings:
        print(f"\n✅ SCAN COMPLETE! Found {len(private_listings)} potential private listings")
        print("📄 Results saved to JSON file")
        print("🎯 You can now focus your scraping on these URLs or similar patterns")
    else:
        print(f"\n❌ No private listings found in scanned pages")
        print("This might indicate that:")
        print("1. Private listings are very rare on Spitogatos")
        print("2. They use different indicators than expected")
        print("3. Private listings might be in different sections of the site")
        print("4. Try different search terms or categories")