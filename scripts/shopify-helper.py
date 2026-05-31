#!/usr/bin/env python3
"""
Shopify API Helper for Stellar Station Agents
Usage: python shopify-helper.py <command> [args]

Commands:
  products list                  - List all products
  products get <id>              - Get product details
  products update <id> <field> <value> - Update product (title, description, price)
  orders list                    - List recent orders
  analytics traffic              - Get traffic stats
  
Mock mode: Set SHOPIFY_MOCK=true to use fake data for testing
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/root/stellar-station/.env')

MOCK_MODE = os.getenv('SHOPIFY_MOCK', 'false').lower() == 'true'
STORE_URL = os.getenv('SHOPIFY_STORE_URL')
ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2024-01')

if MOCK_MODE:
    print("⚠️  WARNING: SHOPIFY_MOCK=true — USING FAKE DATA, NOT REAL STORE ⚠️", file=sys.stderr)

def shopify_request(endpoint, method='GET', data=None):
    """Make Shopify API request"""
    if MOCK_MODE:
        return mock_response(endpoint)
    
    url = f"https://{STORE_URL}/admin/api/{API_VERSION}/{endpoint}"
    headers = {
        'X-Shopify-Access-Token': ACCESS_TOKEN,
        'Content-Type': 'application/json'
    }
    
    if method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'PUT':
        response = requests.put(url, headers=headers, json=data)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f"Shopify API error {response.status_code}: {response.text}")

def mock_response(endpoint):
    """Mock Shopify responses for testing"""
    if 'products.json' in endpoint:
        return {
            'products': [
                {
                    'id': 1001,
                    'title': 'Kegel Exercise Weight - Premium Pelvic Floor Trainer',
                    'status': 'active',
                    'variants': [{'id': 2001, 'price': '29.99', 'inventory_quantity': 45}],
                    'body_html': '<p>Strengthen your pelvic floor with our medical-grade trainer.</p>',
                    'images': []
                },
                {
                    'id': 1002,
                    'title': 'Pelvic Floor Therapy Kit - Complete Set',
                    'status': 'active',
                    'variants': [{'id': 2002, 'price': '49.99', 'inventory_quantity': 23}],
                    'body_html': '<p>Complete kit for pelvic floor rehabilitation.</p>',
                    'images': []
                }
            ]
        }
    elif 'orders.json' in endpoint:
        return {
            'orders': [
                {
                    'id': 5001,
                    'created_at': (datetime.now() - timedelta(hours=2)).isoformat(),
                    'total_price': '29.99',
                    'financial_status': 'paid',
                    'line_items': [{'title': 'Kegel Exercise Weight', 'quantity': 1}]
                },
                {
                    'id': 5002,
                    'created_at': (datetime.now() - timedelta(hours=5)).isoformat(),
                    'total_price': '49.99',
                    'financial_status': 'paid',
                    'line_items': [{'title': 'Pelvic Floor Therapy Kit', 'quantity': 1}]
                }
            ]
        }
    return {}

def cmd_products_list():
    data = shopify_request('products.json?limit=50')
    products = data.get('products', [])
    
    result = {
        'count': len(products),
        'products': []
    }
    
    if MOCK_MODE:
        result['_warning'] = '[MOCK DATA — NOT REAL STORE]'
    
    for p in products:
        result['products'].append({
            'id': p['id'],
            'title': p['title'],
            'status': p['status'],
            'price': p['variants'][0]['price'] if p['variants'] else 'N/A',
            'inventory': p['variants'][0].get('inventory_quantity', 0) if p['variants'] else 0
        })
    
    print(json.dumps(result, indent=2))

def cmd_products_get(product_id):
    data = shopify_request(f'products/{product_id}.json')
    print(json.dumps(data.get('product', {}), indent=2))

def cmd_orders_list():
    data = shopify_request('orders.json?limit=50&status=any')
    orders = data.get('orders', [])
    
    result = {
        'count': len(orders),
        'total_revenue': sum(float(o.get('total_price', 0)) for o in orders),
        'orders': []
    }
    
    if MOCK_MODE:
        result['_warning'] = '[MOCK DATA — NOT REAL STORE]'
    
    for o in orders:
        result['orders'].append({
            'id': o['id'],
            'created_at': o['created_at'],
            'total': o['total_price'],
            'status': o.get('financial_status'),
            'items': len(o.get('line_items', []))
        })
    
    print(json.dumps(result, indent=2))

def cmd_analytics_traffic():
    """Traffic/session analytics.

    The Shopify Admin API does NOT expose visit/session/conversion data — that
    lives in a separate analytics layer (Microsoft Clarity, GA4, or Shopify's
    ShopifyQL/Analytics API). No such source is wired in yet, so this command
    returns an explicit 'unavailable' instead of inventing numbers.
    DO NOT estimate or fabricate traffic figures from this output.
    """
    result = {
        'status': 'unavailable',
        'data_source': None,
        'reason': ('No analytics/traffic source is connected. The Shopify Admin '
                   'API does not provide sessions, visitors, or conversion rate.'),
        'sessions': None,
        'unique_visitors': None,
        'page_views': None,
        'conversion_rate': None,
        'top_pages': None,
        'how_to_enable': ('Connect Microsoft Clarity (free) or GA4 and wire its '
                          'export API into this command. Until then, traffic '
                          'cannot be reported and must not be estimated.')
    }
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == 'products':
            if len(sys.argv) < 3:
                print("Usage: shopify-helper.py products <list|get> [id]")
                sys.exit(1)
            
            action = sys.argv[2]
            if action == 'list':
                cmd_products_list()
            elif action == 'get':
                if len(sys.argv) < 4:
                    print("Usage: shopify-helper.py products get <id>")
                    sys.exit(1)
                cmd_products_get(sys.argv[3])
        
        elif command == 'orders':
            if len(sys.argv) < 3:
                print("Usage: shopify-helper.py orders <list>")
                sys.exit(1)
            
            action = sys.argv[2]
            if action == 'list':
                cmd_orders_list()
        
        elif command == 'analytics':
            if len(sys.argv) < 3:
                print("Usage: shopify-helper.py analytics <traffic>")
                sys.exit(1)
            
            action = sys.argv[2]
            if action == 'traffic':
                cmd_analytics_traffic()
        
        else:
            print(f"Unknown command: {command}")
            print(__doc__)
            sys.exit(1)
    
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)
