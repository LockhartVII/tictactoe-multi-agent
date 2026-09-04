from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ


ROOT = Path(SPECPATH).parent.resolve()


def data_file(relative_path):
    path = ROOT / relative_path
    return (str(path), str(Path(relative_path).parent))


datas = [
    data_file("models/alphazero/alphazero_3x3_best.pt"),
    data_file("models/alphazero/alphazero_4x4_best.pt"),
    data_file("models/alphazero/alphazero_5x5_best.pt"),
    data_file("models/alphazero/alphazero_9x9_best.pt"),
    data_file("models/go/kata9x9-b18c384nbt-20231025.bin.gz"),
    data_file("engines/pikafish/runtime/pikafish.nnue"),
    data_file("engines/pikafish/runtime/Windows/pikafish-avx2.exe"),
]

# KataGo ships several DLLs and its default GTP configuration next to the
# executable. Keep the complete runtime files, but leave local engine logs out.
for path in (ROOT / "engines/katago/runtime").iterdir():
    if path.is_file():
        datas.append((str(path), "engines/katago/runtime"))

for relative_path in (
    "engines/pikafish/runtime/AUTHORS",
    "engines/pikafish/runtime/Copying.txt",
    "engines/pikafish/runtime/NNUE-License.md",
    "engines/pikafish/runtime/README.md",
):
    datas.append(data_file(relative_path))


a = Analysis(
    [str(ROOT / "upgrade.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["pygame"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    icon=str(ROOT / "packaging/qizhi_agent.ico"),
    name="QizhiAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="QizhiAgent",
)
