from flask import Flask, request, jsonify
from flask_cors import CORS
from spitogatos_private_scraping import SpitoogatosPrivateScraper

app = Flask(__name__)
CORS(app)  # enable CORS for all routes
scraper = SpitoogatosPrivateScraper()

@app.route('/api/scrape', methods=['GET'])
def scrape_listings():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing `url` parameter'}), 400
    try:
        listings = scraper.scrape_multiple_pages(url, max_pages=3)
        # Optionally drop description here
        for item in listings:
            item.pop('description', None)
        return jsonify({'count': len(listings), 'listings': listings})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)