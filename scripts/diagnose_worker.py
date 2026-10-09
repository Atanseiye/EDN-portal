"""Read-only deployed Worker diagnostics through authenticated CI."""
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
import urllib.error


def redact(message):
    for name, value in os.environ.items():
        if value and any(word in name for word in ("TOKEN", "SECRET", "KEY")):
            message = message.replace(value, "[redacted]")
    message = re.sub(r"postgres(?:ql)?://\S+", "[redacted database URL]", message)
    return message.replace("%", "%25").replace("\n", " ").replace("\r", " ")[:1000]


account = os.environ['CLOUDFLARE_ACCOUNT_ID']
request = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{account}/workers/subdomain',
    headers={'Authorization': 'Bearer ' + os.environ['CLOUDFLARE_API_TOKEN']})
with urllib.request.urlopen(request) as response:
    subdomain = json.load(response)['result']['subdomain']
origin = f'https://ednai.{subdomain}.workers.dev'
print(f'::notice::Live Worker: {origin}', flush=True)
request = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{account}/workers/scripts/ednai/subdomain',
    headers={'Authorization': 'Bearer ' + os.environ['CLOUDFLARE_API_TOKEN']})
with urllib.request.urlopen(request) as response:
    settings = json.load(response)['result']
print('::notice::Worker public endpoint settings: ' + redact(json.dumps(settings)), flush=True)
with tempfile.TemporaryFile(mode='w+') as logfile:
    tail = subprocess.Popen(['npx', 'wrangler', 'tail', 'ednai', '--format', 'json'], stdout=logfile, stderr=subprocess.STDOUT)
    try:
        time.sleep(8)
        for path in ['/health/live', '/health/ready']:
            try:
                probe = urllib.request.Request(origin + path, headers={'User-Agent': 'Mozilla/5.0 (compatible; EDNAi-Deployment-Check/1.0)', 'Accept': 'application/json'})
                with urllib.request.urlopen(probe, timeout=35) as response:
                    print(f'::notice::{path} HTTP {response.status}', flush=True)
            except urllib.error.HTTPError as error:
                body=error.read().decode(errors='replace')
                code=re.search(r'\b(1101|1102)\b', body)
                print(f'::error::{path} HTTP {error.code}' + (f' Cloudflare {code.group(1)}' if code else ''), flush=True)
                details = {name: error.headers.get(name) for name in ['server', 'content-type', 'cf-ray', 'location']}
                print('::notice::Response details: ' + redact(json.dumps(details) + ' body=' + body[:700]), flush=True)
            except urllib.error.URLError:
                print(f'::error::{path} connection failed', flush=True)
        time.sleep(5)
    finally:
        tail.terminate()
        try: tail.wait(timeout=10)
        except subprocess.TimeoutExpired: tail.kill(); tail.wait()
    logfile.seek(0)
    text=logfile.read()
    # Wrangler pretty-prints each JSON event. Extract concatenated objects.
    decoder=json.JSONDecoder()
    index=0
    while index < len(text):
        start=text.find('{', index)
        if start < 0: break
        try: event,end=decoder.raw_decode(text[start:])
        except json.JSONDecodeError: index=start+1; continue
        index=start+end
        for error in event.get('exceptions', []):
            print('::error::Runtime: ' + redact(str(error.get('message', 'Unknown runtime error'))), flush=True)
        for log in event.get('logs', []):
            message=' '.join(str(part) for part in log.get('message', []))
            if 'EDNAI_DATABASE_ERROR' in message:
                print('::error::' + redact(message), flush=True)
