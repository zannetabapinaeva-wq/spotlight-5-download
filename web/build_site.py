"""Publish the verified course from the public APK as a standalone responsive site."""
import hashlib
import io
import json
import os
import struct
from pathlib import Path, PurePosixPath
from urllib.request import urlopen
from zipfile import ZipFile

SOURCE_URL = 'https://github.com/zannetabapinaeva-wq/spotlight-5-download/releases/download/v1.0.0/Spotlight-5.apk'
EXPECTED_SHA256 = '13b733c36e327dcc62bd3c4fcb6e93a97053241644891dd24df9170fc2b2407f'

def build(apk: bytes, output: Path):
    assert hashlib.sha256(apk).hexdigest() == EXPECTED_SHA256, 'Unexpected course source'
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(io.BytesIO(apk)) as archive:
        for name in archive.namelist():
            if not name.startswith('assets/web/') or name.endswith('/'):
                continue
            relative = PurePosixPath(name.removeprefix('assets/web/'))
            assert not relative.is_absolute() and '..' not in relative.parts
            if relative.name == 'android-bridge.js':
                continue
            path = output.joinpath(*relative.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
        # Android resource optimisation renames paths; select the full-size launcher art.
        icons = [archive.read(name) for name in archive.namelist()
                 if name.startswith('res/') and name.endswith('.png')]
        icon = max(icons, key=lambda data: struct.unpack('>II', data[16:24])[0])
        assert struct.unpack('>II', icon[16:24]) == (768, 768)
        (output / 'app-icon.png').write_bytes(icon)
    index = output / 'index.html'
    html = index.read_text(encoding='utf-8')
    html = html.replace('<script src="android-bridge.js"></script>', '')
    html = html.replace('</head>', '<meta name="description" content="Spotlight 5: английский язык для 5 класса. Уроки, словарь с картинками, задания и озвучка. Для компьютера, планшета и телефона."><link rel="icon" href="app-icon.png" type="image/png"><link rel="apple-touch-icon" href="app-icon.png"></head>')
    index.write_text(html, encoding='utf-8')
    (output / '.nojekyll').touch()
    assert 'android-bridge.js' not in html
    assert len(list((output / 'assets').glob('*.png'))) == 21
    assert 'grid-column:2' in (output / 'style.css').read_text()
    print(json.dumps({'site': str(output), 'illustration_assets': 21, 'responsive': True}))

if __name__ == '__main__':
    local_apk = os.getenv('SPOTLIGHT_APK')
    if local_apk:
        apk = Path(local_apk).read_bytes()
    else:
        with urlopen(SOURCE_URL, timeout=90) as response:
            apk = response.read()
    build(apk, Path('_site'))
