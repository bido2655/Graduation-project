"""
PlantUML Service - Encoding, decoding, and rendering.
"""
import base64
import zlib
import io
import time
import traceback
import requests
from typing import Optional
from PIL import Image, ImageDraw, ImageFont


def encode_plantuml(plantuml_code: str) -> str:
    """Encode PlantUML code for URL using manual bit-wise encoding."""
    try:
        # Compress the PlantUML code using raw DEFLATE
        zlib_obj = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        compressed = zlib_obj.compress(plantuml_code.encode('utf-8'))
        compressed += zlib_obj.flush()
        
        return _puml_encode64(compressed)
    except Exception as e:
        print(f"Encoding error: {e}")
        return ""


def _puml_encode64(data: bytes) -> str:
    """Custom Base64 encoding for PlantUML with correct padding/chunking."""
    res = ""
    for i in range(0, len(data), 3):
        chunk = data[i:i+3]
        if len(chunk) == 3:
            res += _puml_encode3bytes(chunk[0], chunk[1], chunk[2])
        elif len(chunk) == 2:
            res += _puml_encode2bytes(chunk[0], chunk[1])
        elif len(chunk) == 1:
            res += _puml_encode1byte(chunk[0])
    return res


def _puml_encode1byte(b1: int) -> str:
    c1 = b1 >> 2
    c2 = (b1 & 0x3) << 4
    res = ""
    res += _puml_encode6bit(c1 & 0x3F)
    res += _puml_encode6bit(c2 & 0x3F)
    return res


def _puml_encode2bytes(b1: int, b2: int) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = (b2 & 0xF) << 2
    res = ""
    res += _puml_encode6bit(c1 & 0x3F)
    res += _puml_encode6bit(c2 & 0x3F)
    res += _puml_encode6bit(c3 & 0x3F)
    return res


def _puml_encode3bytes(b1, b2, b3) -> str:
    c1 = b1 >> 2
    c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
    c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
    c4 = b3 & 0x3F
    res = ""
    res += _puml_encode6bit(c1 & 0x3F)
    res += _puml_encode6bit(c2 & 0x3F)
    res += _puml_encode6bit(c3 & 0x3F)
    res += _puml_encode6bit(c4 & 0x3F)
    return res


def _puml_encode6bit(b) -> str:
    if b < 10: return chr(48 + b)
    b -= 10
    if b < 26: return chr(65 + b)
    b -= 26
    if b < 26: return chr(97 + b)
    b -= 26
    if b == 0: return '-'
    if b == 1: return '_'
    return '?'


def decode_plantuml(encoded: str) -> str:
    """Decode PlantUML from URL format."""
    try:
        # Remove ~1 prefix
        if encoded.startswith('~1'):
            encoded = encoded[2:]
        
        # Translate back from URL-safe format
        translated = encoded.translate(str.maketrans(
            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_',
            'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        ))
        
        # Add padding if needed
        padding = 4 - len(translated) % 4
        if padding != 4:
            translated += '=' * padding
        
        # Decode
        decoded = base64.b64decode(translated)
        
        # Try to decompress
        try:
            return zlib.decompress(decoded).decode('utf-8')
        except:
            return decoded.decode('utf-8')
            
    except Exception as e:
        print(f"Decode error: {e}")
        return "@startuml\nnote: Error decoding diagram\n@enduml"


def render_plantuml_to_png(plantuml_code: str) -> Optional[str]:
    """Render PlantUML code to PNG and return as base64."""
    try:
        print(f"Rendering PlantUML code, length: {len(plantuml_code)}")
        
        if not plantuml_code.strip():
            print("Error: Empty PlantUML code")
            return None
        
        # Encode the PlantUML code
        encoded = encode_plantuml(plantuml_code)
        
        # Try multiple PlantUML servers
        plantuml_servers = [
            'https://www.plantuml.com/plantuml/png/',
            'https://plantuml.com/plantuml/png/',
            'https://kroki.io/plantuml/png/',
        ]
        
        for i, plantuml_server in enumerate(plantuml_servers):
            try:
                print(f"Trying server {i+1}: {plantuml_server}")
                url = f'{plantuml_server}{encoded}'
                
                response = requests.get(
                    url, 
                    timeout=30,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'image/png,image/*;q=0.8,*/*;q=0.5'
                    }
                )
                
                print(f"Server {i+1} response: {response.status_code}, size: {len(response.content)}")
                
                if response.status_code == 200 and len(response.content) > 100:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'image' in content_type or response.content[:4] == b'\x89PNG':
                        print(f"Success with server {i+1}")
                        return base64.b64encode(response.content).decode('utf-8')
                    
            except requests.exceptions.RequestException as e:
                print(f"Error connecting to server {i+1}: {e}")
                continue
        
        print("All PlantUML servers failed. Trying Kroki with direct API...")
        
        # Try with Kroki direct API
        try:
            kroki_response = requests.post(
                'https://kroki.io/plantuml/png',
                json={
                    "diagram_source": plantuml_code,
                    "diagram_type": "plantuml"
                },
                timeout=30
            )
            
            if kroki_response.status_code == 200 and len(kroki_response.content) > 100:
                print("Success with Kroki API")
                return base64.b64encode(kroki_response.content).decode('utf-8')
        except Exception as e:
            print(f"Kroki API also failed: {e}")
        
        # Create a fallback diagram
        print("Creating fallback diagram...")
        return create_fallback_diagram(plantuml_code)
            
    except Exception as e:
        print(f"Critical error in render_plantuml_to_png: {e}")
        print(traceback.format_exc())
        return create_fallback_diagram(plantuml_code)


def create_fallback_diagram(plantuml_code: str) -> Optional[str]:
    """Create a simple fallback diagram when rendering fails."""
    try:
        # Create a simple text-based diagram
        img = Image.new('RGB', (800, 600), color='#0f172a')
        d = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 16)
            font_bold = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
            font_bold = ImageFont.load_default()
        
        # Add title
        d.text((20, 20), "PlantUML Diagram Preview", fill='#818cf8', font=font_bold)
        d.text((20, 50), "(Rendering service unavailable)", fill='#94a3b8', font=font)
        
        # Draw a box for the diagram
        d.rectangle([10, 10, 790, 590], outline='#4f46e5', width=2)
        
        # Show the first few lines of PlantUML code
        lines = plantuml_code.split('\n')
        y = 100
        for i, line in enumerate(lines[:18]):
            if y < 550:
                if line.strip().startswith('@'):
                    color = '#f472b6'
                elif line.strip().startswith('!'):
                    color = '#60a5fa'
                elif line.strip().startswith('skinparam'):
                    color = '#60a5fa'
                elif '->' in line or '-->' in line or '..>' in line:
                    color = '#34d399'
                elif 'class ' in line or 'actor ' in line or 'usecase ' in line:
                    color = '#fbbf24'
                else:
                    color = '#c7d2fe'
                
                d.text((20, y), line[:90], fill=color, font=font)
                y += 25
        
        # Add note at bottom
        d.text((20, 560), "Note: Try viewing at https://plantuml.com/editor", fill='#94a3b8', font=font)
        
        # Save to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return base64.b64encode(img_byte_arr).decode('utf-8')
        
    except Exception as e:
        print(f"Fallback diagram creation failed: {e}")
        return None


def create_diagram_image(plantuml_code: str) -> Optional[bytes]:
    """Create a simple diagram image from PlantUML code."""
    try:
        img = Image.new('RGB', (1000, 800), color='#0f172a')
        d = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 14)
            font_title = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
            font_title = ImageFont.load_default()
        
        # Add title
        d.text((20, 20), "NEXUS UML Diagram", fill='#818cf8', font=font_title)
        d.text((20, 60), f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", fill='#94a3b8', font=font)
        
        # Draw border
        d.rectangle([10, 10, 990, 790], outline='#4f46e5', width=3)
        
        # Display PlantUML code
        lines = plantuml_code.split('\n')
        y = 120
        for i, line in enumerate(lines):
            if y < 750:
                # Syntax highlighting
                if line.strip().startswith('@'):
                    color = '#f472b6'
                elif line.strip().startswith('!'):
                    color = '#60a5fa'
                elif 'skinparam' in line:
                    color = '#60a5fa'
                elif '->' in line or '-->' in line or '..>' in line:
                    color = '#34d399'
                elif 'class ' in line or 'actor ' in line or 'usecase ' in line:
                    color = '#fbbf24'
                elif line.strip().startswith('#'):
                    color = '#94a3b8'
                else:
                    color = '#c7d2fe'
                
                d.text((30, y), line[:120], fill=color, font=font)
                y += 28
        
        # Add footer
        d.text((20, 770), "NEXUS AI PlantUML Generator", fill='#c7d2fe', font=font)
        
        # Save to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
        
    except Exception as e:
        print(f"Create diagram image error: {e}")
        return None
