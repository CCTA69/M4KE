"""Read-only offline readiness inventory. Never installs, downloads, or restarts anything."""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Redirect refused; local service only")


def read_local(url):
    parsed = urlparse(url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1") or parsed.username or parsed.password:
        raise ValueError("Loopback HTTP only")
    with build_opener(ProxyHandler({}), NoRedirect()).open(url, timeout=4) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("Inventory response too large")
    return json.loads(data)


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=8, check=False)
        return {"ok": result.returncode == 0, "output": result.stdout[:4000].strip()}
    except (OSError, subprocess.TimeoutExpired):
        return {"ok": False, "output": "Unavailable"}


def inventory(root):
    root = Path(root).resolve()
    memory = {}
    if Path('/proc/meminfo').exists():
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, value = line.split(':', 1)
            if key in ('MemTotal', 'MemAvailable', 'SwapTotal'):
                memory[key + 'GiB'] = round(int(value.split()[0]) / 1024**2, 2)
    report = {"schemaVersion": 1, "machineArchitecture": platform.machine(), "platform": platform.system(),
              "memory": memory, "diskFreeGiB": round(shutil.disk_usage(root).free / 2**30, 2),
              "gpu": command(['nvidia-smi', '--query-gpu=name,driver_version,memory.total,memory.used', '--format=csv,noheader']),
              "node": command(['node', '--version']), "python": platform.python_version(),
              "cadqueryInstalled": importlib.util.find_spec('cadquery') is not None,
              "frontendBuilt": (root / 'dist/index.html').is_file(),
              "designSkill": (root / 'skills/prompt-to-cad/runtime-design.md').is_file(),
              "verificationSkill": (root / 'skills/engineering-verification/SKILL.md').is_file(),
              "localServices": {}, "offlineAcceptance": "NOT_RUN"}
    for name, url in [('ollama', 'http://127.0.0.1:11434/api/tags'), ('vllm', 'http://127.0.0.1:8000/v1/models')]:
        try:
            data = read_local(url)
            models = data.get('models', []) if name == 'ollama' else data.get('data', [])
            report['localServices'][name] = {"reachable": True, "models": [
                {"id": m.get('name', m.get('id')), "sizeBytes": m.get('size'), "digest": m.get('digest'), "quantization": m.get('details', {}).get('quantization_level')} for m in models]}
        except Exception:
            report['localServices'][name] = {"reachable": False}
    report['notes'] = ['Readiness inventory is not an inference or offline acceptance test.',
                       'Unified memory may be N/A in nvidia-smi; use MemAvailable plus measured process use.',
                       'No hostnames, addresses, credentials, user prompts or project records included.']
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument('--output')
    args = parser.parse_args()
    result = inventory(args.root)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(encoded + '\n', encoding='utf-8')
    print(encoded)
