# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CloudDriveManager
Generates two executables:
  - cloud-drive-manager    (HTTP API server, main.py)
  - cloud-drive-mcp       (MCP server, src/mcp/server.py)
"""
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ── Common configuration ───────────────────────────────────────────────────────

datas = [
    ('config/config_dev.yaml', 'config'),
    ('config/config_prod.yaml', 'config'),
]

hiddenimports = [
    # uvicorn
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    # fastapi
    'fastapi',
    'fastapi.applications',
    'fastapi.routing',
    'fastapi.middleware.cors',
    'fastapi.responses',
    # pydantic
    'pydantic',
    'pydantic.fields',
    'pydantic.main',
    'pydantic.schema',
    'pydantic.validators',
    'pydantic.env_settings',
    # database
    'pymysql',
    'pymysql.connections',
    'pymysql.cursors',
    # crypto
    'cryptography',
    'cryptography.fernet',
    # config
    'yaml',
    # http client
    'httpx',
    'httpcore',
    # mcp
    'fastmcp',
    'fastmcp.server',
    'fastmcp.protocol',
    'fastmcp.utilities',
    # starlette (needed by fastapi)
    'starlette.middleware.cors',
    'starlette.middleware.gzip',
    'starlette.responses',
    'starlette.routing',
]

# ── API server (main.py) ──────────────────────────────────────────────────────

api_a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

api_pyz = PYZ(api_a.pure, api_a.zipped_data, cipher=block_cipher)

api_exe = EXE(
    api_pyz,
    api_a.scripts,
    api_a.binaries,
    api_a.zipfiles,
    api_a.datas,
    [],
    name='cloud-drive-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ── MCP server (src/mcp/server.py) ────────────────────────────────────────────

# Collect all data files from fastmcp
fastmcp_datas = collect_all('fastmcp')

mcp_a = Analysis(
    ['src/mcp/server.py'],
    pathex=[],
    binaries=[],
    datas=datas + fastmcp_datas[0],
    hiddenimports=hiddenimports + [
        'mcp.server',
        'mcp.protocol',
        'importlib.metadata',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

mcp_pyz = PYZ(mcp_a.pure, mcp_a.zipped_data, cipher=block_cipher)

mcp_exe = EXE(
    mcp_pyz,
    mcp_a.scripts,
    mcp_a.binaries,
    mcp_a.zipfiles,
    mcp_a.datas,
    [],
    name='cloud-drive-mcp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
