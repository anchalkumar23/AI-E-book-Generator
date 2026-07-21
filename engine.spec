# PyInstaller spec — freezes the Python engine into one executable.
#
# uvicorn, fastapi and the providers load implementations dynamically, so
# PyInstaller's static analysis cannot see them. Anything missed here works in
# dev and dies only in the frozen binary — which is why Task 17 smoke-runs this
# executable directly rather than trusting the build to succeed.
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "app.main",
    # Providers are resolved by name at runtime via the factories, so nothing
    # imports them statically.
    "app.services.llm.ollama",
    "app.services.llm.groq",
    "app.services.knowledge.duckduckgo",
    "app.services.knowledge.none",
    "app.services.images.placeholder",
] + collect_submodules("duckduckgo_search")

a = Analysis(
    ["backend/app/engine.py"],
    pathex=["backend"],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "PIL", "groq"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    # The target-triple suffix is REQUIRED — Tauri appends it when resolving the
    # sidecar, and a name without it is silently not found.
    # Get yours with: rustc --print host-tuple
    name="pageforge-engine-x86_64-pc-windows-msvc",
    debug=False,
    strip=False,
    upx=False,      # UPX compression trips Windows antivirus false positives
    console=True,   # the engine must keep stdout for the handshake line
)
