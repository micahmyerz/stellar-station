#!/usr/bin/env python3
"""
Image Generation Helper for Stellar Station Agents
Uses Replicate API (Flux Schnell model - $0.003 per image)

Usage: python image-gen.py "<prompt>" [output_path]

Example:
  python image-gen.py "Product photo of pelvic floor trainer, clean white background, professional lighting" product-image.png

Mock mode: Set REPLICATE_MOCK=true to skip actual generation
"""

import sys
import os
import json
import time
from dotenv import load_dotenv

load_dotenv('/root/stellar-station/.env')

MOCK_MODE = os.getenv('REPLICATE_MOCK', 'true').lower() == 'true'
API_TOKEN = os.getenv('REPLICATE_API_TOKEN')

def generate_image(prompt, output_path=None):
    """Generate image using Replicate Flux Schnell"""
    
    if MOCK_MODE:
        result = {
            'status': 'mock',
            'prompt': prompt,
            'cost': 0.003,
            'message': 'MOCK MODE: Image generation skipped. Set REPLICATE_MOCK=false and add API token to generate real images.',
            'output_path': output_path or '/root/stellar-station/media-cache/mock-image.png'
        }
        print(json.dumps(result, indent=2))
        return
    
    if not API_TOKEN or API_TOKEN == 'your-replicate-token-here':
        print(json.dumps({'error': 'REPLICATE_API_TOKEN not configured in .env'}), file=sys.stderr)
        sys.exit(1)
    
    try:
        import replicate
        
        # Use Flux Schnell (fast + cheap)
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={"prompt": prompt}
        )
        
        # Download image
        import requests
        image_url = output[0] if isinstance(output, list) else output
        
        if not output_path:
            timestamp = int(time.time())
            output_path = f"/root/stellar-station/media-cache/image-{timestamp}.png"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Download
        response = requests.get(image_url)
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        result = {
            'status': 'success',
            'prompt': prompt,
            'output_path': output_path,
            'cost': 0.003,
            'image_url': image_url
        }
        
        print(json.dumps(result, indent=2))
        
        # Log cost
        os.system(f"/root/stellar-station/scripts/log-cost.sh replicate 0.003 $(whoami) 0 'Image generation: {prompt[:50]}'")
        
    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    prompt = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    generate_image(prompt, output_path)
