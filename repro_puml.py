import requests
import zlib
import base64

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

def _puml_encode64(data: bytes) -> str:
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

def encode_plantuml(plantuml_code: str) -> str:
    zlib_obj = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    compressed = zlib_obj.compress(plantuml_code.encode('utf-8'))
    compressed += zlib_obj.flush()
    return _puml_encode64(compressed)

plantuml_code = """@startuml
!theme plain
skinparam class {
  BackgroundColor #f0fdfa
  BorderColor #2dd4bf
  ArrowColor #f43f5e
  FontColor #134e4a
  ActorBackgroundColor #99f6e4
  ActorBorderColor #0d9488
}

class Entity {
  - id: int
  + save()
}

@enduml"""

encoded = encode_plantuml(plantuml_code)
print(f"Encoded: {encoded}")

plantuml_servers = [
    'https://www.plantuml.com/plantuml/png/',
    'https://plantuml.com/plantuml/png/',
    'https://kroki.io/plantuml/png/',
]

for server in plantuml_servers:
    url = f"{server}{encoded}"
    print(f"Trying {url}")
    try:
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}, Size: {len(resp.content)}")
        if resp.status_code == 200:
            with open(f"test_{server.split('/')[2]}.png", "wb") as f:
                f.write(resp.content)
    except Exception as e:
        print(f"Error: {e}")
