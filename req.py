import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8080/api/chat',
    data=json.dumps({'user_id': 'demo_user', 'message': 'i need a saree'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req) as f:
        print(f.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode('utf-8')}")
