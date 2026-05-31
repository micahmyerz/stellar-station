#!/usr/bin/env python3
"""
Shopify OAuth one-time token grabber
Starts a local server, prints the auth URL, waits for callback, exchanges code for token
"""
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import load_dotenv

load_dotenv('/root/stellar-station/.env')

SHOP = os.getenv('SHOPIFY_SHOP')
CLIENT_ID = os.getenv('SHOPIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SHOPIFY_CLIENT_SECRET')
REDIRECT_URI = 'http://2.24.126.194:3999/callback'
SCOPES = 'read_products,read_orders,read_customers,read_analytics'

if not all([SHOP, CLIENT_ID, CLIENT_SECRET]):
    print("❌ Missing env vars: SHOPIFY_SHOP, SHOPIFY_CLIENT_ID, SHOPIFY_CLIENT_SECRET")
    sys.exit(1)

# Remove https:// or .myshopify.com if present
shop_name = SHOP.replace('https://', '').replace('http://', '')
if not shop_name.endswith('.myshopify.com'):
    shop_name = f"{shop_name}.myshopify.com"

AUTH_URL = f"https://{shop_name}/admin/oauth/authorize?client_id={CLIENT_ID}&scope={SCOPES}&redirect_uri={REDIRECT_URI}"

class OAuthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/callback':
            params = parse_qs(parsed.query)
            
            if 'code' in params:
                code = params['code'][0]
                print(f"\n✅ Got authorization code: {code[:20]}...")
                
                # Exchange code for token
                token_url = f"https://{shop_name}/admin/oauth/access_token"
                payload = {
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'code': code
                }
                
                resp = requests.post(token_url, json=payload)
                
                if resp.status_code == 200:
                    data = resp.json()
                    token = data.get('access_token')
                    
                    print(f"\n🎉 SUCCESS! Access token: {token}\n")
                    print(f"Add this to /root/stellar-station/.env:\n")
                    print(f"SHOPIFY_ACCESS_TOKEN={token}\n")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b'<h1>Success!</h1><p>Token received. Check your terminal and close this window.</p>')
                    
                    # Shutdown server after success
                    import threading
                    threading.Thread(target=self.server.shutdown).start()
                else:
                    print(f"❌ Token exchange failed: {resp.status_code} {resp.text}")
                    self.send_response(500)
                    self.end_headers()
            else:
                print("❌ No code in callback")
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

print("🚀 Shopify OAuth Token Grabber")
print(f"📍 Shop: {shop_name}")
print(f"🔑 Client ID: {CLIENT_ID[:10]}...")
print(f"\n🌐 VISIT THIS URL IN YOUR BROWSER:\n")
print(f"{AUTH_URL}\n")
print("Waiting for callback on port 3999...")

server = HTTPServer(('0.0.0.0', 3999), OAuthHandler)
server.serve_forever()
