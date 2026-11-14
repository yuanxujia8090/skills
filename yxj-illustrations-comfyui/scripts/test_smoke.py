"""离线验证：不连接真实 ComfyUI、不生成图片、不操作后端进程。"""
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def main():
    for script in sorted((ROOT / 'scripts').glob('*.py')):
        ast.parse(script.read_text(), filename=str(script))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for name in ['generate.py', 'add_labels.py', 'free_comfy.py']:
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / name), '--help'],
                                capture_output=True, text=True, env=env, timeout=30)
        assert result.returncode == 0, (name, result.stderr)
    spec = importlib.util.spec_from_file_location('generate', ROOT / 'scripts/generate.py')
    assert spec is not None and spec.loader is not None
    generate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate)
    for mode in ['none', 'vision', 'latent']:
        graph = generate.build('test scene', 7, 'test/sample', 'ref.jpg', mode, 1536, 1024, 25)
        assert graph['9']['class_type'] == 'SaveImage'
        assert graph['7']['inputs']['positive'] == ['4', 0]
        assert graph['7']['inputs']['negative'] == ['4', 1]
        assert ('10' in graph) == (mode != 'none')
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        image = Image.new('RGB', (768, 512), '#F5F0E6')
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        payload = buf.getvalue()
        calls = []

        def fake_download(url, timeout):
            calls.append(url)
            return io.BytesIO(payload)

        with patch.object(generate.urllib.request, 'urlopen', fake_download):
            dest = generate.fetch_image(8000, {'filename': '图片 a.png',
                                       'subfolder': 'folder/带 空格', 'type': 'output'}, td / 'nested/base.png')
        assert dest.read_bytes() == payload
        query = parse_qs(urlparse(calls[0]).query)
        assert query == {'filename': ['图片 a.png'], 'subfolder': ['folder/带 空格'], 'type': ['output']}
        before = hashlib.sha256(dest.read_bytes()).hexdigest()
        out = td / 'labels.png'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/add_labels.py'), str(dest),
                                 '--out', str(out), '--no-snap',
                                 '--labels', '检查@0.10,0.30,#E8552D;通过@0.60,0.70,#1A1A1A'],
                                capture_output=True, text=True, env=env, timeout=90)
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert [x['text'] for x in report['labels']] == ['检查', '通过']
        assert Image.open(out).size == image.size
        assert out.read_bytes() != dest.read_bytes()
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == before
    print('PASS：脚本语法、三个参数入口、三种任务图、模拟下载与中文叠字；真实后端调用0次。')


if __name__ == '__main__':
    main()
