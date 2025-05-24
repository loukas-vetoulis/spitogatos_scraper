import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin


class SpitoogatosPrivateScraper:
    def __init__(self):
        self.base_url = "https://www.spitogatos.gr"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'el-GR,el;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def extract_property_data(self, article):
        """Extract data from a single property article element"""
        data = {}

        try:
            # Check if it's a private listing
            private_logo = article.find('div', class_='tile__logo--private')
            if not private_logo:
                return None  # Skip non-private listings

            # Title and size
            title_elem = article.find('h3', class_='tile__title')
            data['title'] = title_elem.get_text(strip=True) if title_elem else ''

            # Location
            location_elem = article.find('h3', class_='tile__location')
            data['location'] = location_elem.get_text(strip=True) if location_elem else ''


            # Price
            price_elem = article.find('p', class_='price__text')
            data['price'] = price_elem.get_text(strip=True) if price_elem else ''

            # Property details (floor, bedrooms, bathrooms)
            info_items = article.find_all('li', title=True)
            data['floor'] = ''
            data['bedrooms'] = ''
            data['bathrooms'] = ''

            for item in info_items:
                title_attr = item.get('title', '')
                span_text = item.find('span')
                if span_text:
                    text_content = span_text.get_text(strip=True)

                    if 'Όροφος' in title_attr:
                        data['floor'] = text_content
                    elif 'Υπνοδωμάτια' in title_attr:
                        data['bedrooms'] = text_content.replace('υ/δ', '').strip()
                    elif 'Μπάνια' in title_attr:
                        data['bathrooms'] = text_content.replace('μπ', '').strip()

            # Property link
            link_elem = article.find('a', class_='tile__link')
            if link_elem and link_elem.get('href'):
                data['property_url'] = urljoin(self.base_url, link_elem['href'])
            else:
                data['property_url'] = ''

            # Update date
            time_elem = article.find('time')
            data['updated_date'] = time_elem.get('datetime', '') if time_elem else ''

            # Number of photos
            photo_elem = article.find('div', class_='header__rest')
            if photo_elem:
                photo_span = photo_elem.find('span')
                data['photos_count'] = photo_span.get_text(strip=True) if photo_span else '0'
            else:
                data['photos_count'] = '0'

            # Extract square meters from title
            if data['title']:
                sqm_match = re.search(r'(\d+)τ\.μ\.', data['title'])
                data['square_meters'] = sqm_match.group(1) if sqm_match else ''
            else:
                data['square_meters'] = ''

            return data

        except Exception as e:
            print(f"Error extracting property data: {e}")
            return None

    def scrape_page(self, url):
        """Scrape a single page and return private listings data"""
        try:
            print(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all property articles
            articles = soup.find_all('article', class_='ordered-element')

            private_listings = []
            for article in articles:
                property_data = self.extract_property_data(article)
                if property_data:  # Only add if it's a private listing
                    private_listings.append(property_data)

            print(f"Found {len(private_listings)} private listings on this page")
            return private_listings

        except requests.RequestException as e:
            print(f"Error fetching page {url}: {e}")
            return []
        except Exception as e:
            print(f"Error parsing page {url}: {e}")
            return []

    def scrape_multiple_pages(self, base_url, max_pages=5):
        """Scrape multiple pages starting from the given URL"""
        all_listings = []

        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                # Construct URL for subsequent pages
                if 'selida_' in base_url:
                    url = re.sub(r'selida_\d+', f'selida_{354 + page - 1}', base_url)
                else:
                    url = f"{base_url}/selida_{page}"

            listings = self.scrape_page(url)
            all_listings.extend(listings)

            # Be respectful to the server
            time.sleep(2)

            # Stop if no listings found (might have reached the end)
            if not listings:
                print("No more listings found, stopping...")
                break

        return all_listings

    def save_to_csv(self, listings, filename='spitogatos_private_listings.csv'):
        """Save listings to CSV file"""
        if not listings:
            print("No listings to save")
            return

        df = pd.DataFrame(listings)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Saved {len(listings)} private listings to {filename}")

        # Display summary
        print("\n=== SUMMARY ===")
        print(f"Total private listings: {len(listings)}")
        if len(listings) > 0:
            print(f"Price range: {df['price'].min()} - {df['price'].max()}")
            print(f"Average bedrooms: {df['bedrooms'].mode().iloc[0] if not df['bedrooms'].empty else 'N/A'}")
            print(f"Most common location: {df['location'].mode().iloc[0] if not df['location'].empty else 'N/A'}")


def main():
    # Initialize scraper
    scraper = SpitoogatosPrivateScraper()

    # Target URL
    url = "https://www.spitogatos.gr/pwliseis-katoikies/glyfada/selida_353"

    # Scrape multiple pages (adjust max_pages as needed)
    listings = scraper.scrape_multiple_pages(url, max_pages=3)

    # Save to CSV
    scraper.save_to_csv(listings)

    # Display first few listings
    if listings:
        print("\n=== SAMPLE LISTINGS ===")
        for i, listing in enumerate(listings[:3]):
            print(f"\nListing {i + 1}:")
            for key, value in listing.items():
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()