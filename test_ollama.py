import urllib.request
import json

# Test 1 - koneksi ke Ollama
urls = [
    "http://host.docker.internal:11434/api/tags",
    "http://172.17.0.1:11434/api/tags",
]

for url in urls:
    try:
        r = urllib.request.urlopen(url, timeout=5)
        data = json.loads(r.read())
        models = [m["name"] for m in data.get("models", [])]
        print(f"OK {url}")
        print(f"   Models: {models}")
        break
    except Exception as e:
        print(f"FAIL {url}: {e}")

# Test 2 - embedding
try:
    req = urllib.request.Request(
        "http://host.docker.internal:11434/api/embeddings",
        data=json.dumps({"model": "nomic-embed-text", "prompt": "test"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    r = urllib.request.urlopen(req, timeout=30)
    result = json.loads(r.read())
    dim = len(result.get("embedding", []))
    print(f"Embedding OK - dimensi: {dim}")
except Exception as e:
    print(f"Embedding FAIL: {e}")
