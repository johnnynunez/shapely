"""Isolated native Windows ARM64 Shapely 2.1.2 acceptance."""
import json
import email
import zipfile
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig

assert sys.platform == 'win32' and sysconfig.get_platform() == 'win-arm64', 'Native Windows ARM64 only'
root = Path(os.environ['GITHUB_WORKSPACE'])
source = root / 'source'
out = root / 'evidence'
out.mkdir(exist_ok=True)
work = Path(os.environ['RUNNER_TEMP']) / 'geometry-shapely'
work.mkdir(exist_ok=True)
for key in ('PIP_CACHE_DIR', 'CIBW_CACHE_PATH', 'NUGET_PACKAGES', 'NUGET_HTTP_CACHE_PATH', 'NUGET_PLUGINS_CACHE_PATH', 'VIRTUALENV_OVERRIDE_APP_DATA', 'UV_CACHE_DIR', 'UV_PYTHON_INSTALL_DIR', 'UV_PYTHON_BIN_DIR'):
    os.environ[key] = str(work / key)
log = (out / 'commands.log').open('a', encoding='utf-8')

def run(args, cwd=work):
    print('RUN', args, flush=True)
    log.write('RUN ' + repr(args) + '\n'); log.flush()
    proc = subprocess.Popen([str(a) for a in args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    for line in proc.stdout:
        print(line, end='', flush=True); log.write(line); log.flush()
    code = proc.wait()
    if code:
        raise subprocess.CalledProcessError(code, args)

sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
assert sha == '5fb639d1056888d135fe56bfaf750c9648addeec'
(out / 'provenance.json').write_text(json.dumps({'source_sha': sha, 'python': sys.version, 'platform': platform.platform(), 'python_platform': sysconfig.get_platform(), 'gpu': False, 'GEOS': '3.13.1', 'GEOS_source': '431568d6e311e0bbfb057b4ec3d44d0d3ba3335f'}, indent=2))
run([sys.executable, '-m', 'pip', 'install', 'build', 'cmake==3.31.6', 'ninja', 'delvewheel', 'pefile', 'numpy', 'pytest', 'pytest-cov', 'scipy-doctest'])
run(['git', 'clone', '--depth', '1', '--branch', '3.13.1', 'https://github.com/libgeos/geos.git', work / 'geos'])
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=work/'geos', text=True).strip() == '431568d6e311e0bbfb057b4ec3d44d0d3ba3335f'
run(['cmake', '-S', work/'geos', '-B', work/'geos-build', '-GNinja', '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON', '-DBUILD_TESTING=OFF', f'-DCMAKE_INSTALL_PREFIX={work / "geos-install"}'])
run(['cmake', '--build', work/'geos-build', '--parallel', '4'])
run(['cmake', '--install', work/'geos-build'])
os.environ['GEOS_INCLUDE_PATH'] = str(work/'geos-install/include')
os.environ['GEOS_LIBRARY_PATH'] = str(work/'geos-install/lib')
for name in ('LICENSE_GEOS', 'LICENSE_win32'):
    shutil.copy(source/'ci/wheelbuilder'/name, source/name)
run([sys.executable, '-m', 'build', '--wheel', '--outdir', out/'raw'], source)
wheel = next((out/'raw').glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    metadata = email.message_from_bytes(z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))))
    assert metadata['Version'] == '2.1.2', metadata['Version']
run([sys.executable, '-m', 'delvewheel', 'repair', '--add-path', work/'geos-install/bin', '-w', out/'wheels', wheel])
run([sys.executable, root/'ci/native/wheel_audit.py', out/'wheels', out/'wheel-audit.json'])
run([sys.executable, '-m', 'venv', work/'test-venv'])
py = work/'test-venv/Scripts/python.exe'
wheel = next((out/'wheels').glob('*.whl'))
run([py, '-m', 'pip', 'install', wheel, 'pytest', 'pytest-cov', 'scipy-doctest', 'matplotlib'])
run([py, '-m', 'pip', 'freeze'])
run([py, '-m', 'pytest', '--pyargs', 'shapely.tests', '-ra', f'--junitxml={out / "upstream.xml"}'])
run([py, '-m', 'pytest', root/'ci/native/test_shapely_oracles.py', '-v', f'--junitxml={out / "oracles.xml"}'])
(out/'PASS').write_text('Installed repaired wheel: upstream suite, geometry oracles, PE and RECORD passed; CPU only.\n')
