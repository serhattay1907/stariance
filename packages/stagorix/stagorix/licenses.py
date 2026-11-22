"""Dependency license check (Python and npm) and the asset register (ASSETS.md).

Only permissively licensed dependencies and assets are allowed (AGENTS.md). This module
reads the licenses of what is actually installed (the uv environment and render/node_modules),
so a new transitive dependency is caught too, and writes ASSETS.md from the model, sound and
font catalogs, so the register cannot drift from the code.
"""

from __future__ import annotations

import json
import re
from importlib import metadata
from pathlib import Path

from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
NODE_MODULES = ROOT / "render" / "node_modules"
ASSETS_FILE = ROOT / "ASSETS.md"

# SPDX ids (and the spellings packages actually use) that need no more than attribution.
ALLOWED = {
    "MIT",
    "MIT-0",
    "BSD",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "0BSD",
    "Apache-2.0",
    "Apache Software License",
    "Apache License 2.0",
    "ISC",
    "PSF-2.0",
    "Python-2.0",
    "Python Software Foundation License",
    "Unlicense",
    "CC0-1.0",
    "CC-BY-4.0",
    "BlueOak-1.0.0",
    "OFL-1.1",
    "MPL-2.0",  # file-level copyleft: fine to use unmodified (certifi, tqdm)
    "Zlib",
    "HPND",
}
# Known non-SPDX licenses, each reviewed and recorded in docs/DECISIONS.md.
REVIEWED = {
    "remotion": "Remotion license: free for individuals and companies up to 3 people (DECISIONS 2026-11-21)",
    "@remotion/": "Remotion license (DECISIONS 2026-11-21)",
}


class Finding(BaseModel):
    ecosystem: str
    package: str
    version: str
    license: str
    ok: bool
    note: str = ""


def _ids(expr: str) -> list[str]:
    """License ids in an expression like '(MIT OR Apache-2.0)' or 'MIT AND BSD-3-Clause'."""
    return [t for t in re.split(r"\s+(?:OR|AND|WITH)\s+|[()]|;|,|/", expr) if t.strip()]


ALIASES = {"3-Clause BSD License": "BSD-3-Clause", "BSD License": "BSD-3-Clause", "MIT License": "MIT"}


def _allowed(expr: str) -> bool:
    expr = ALIASES.get(expr.strip(), expr)
    if not expr:
        return False
    parts = [p.strip() for p in _ids(expr)]
    if " OR " in expr:
        return any(p in ALLOWED for p in parts)
    return all(p in ALLOWED for p in parts)


def _python_license(dist: metadata.Distribution) -> str:
    meta = dist.metadata
    expr = meta.get("License-Expression")
    if expr:
        return expr.strip()
    classifiers = [
        c.split(" :: ")[-1] for c in meta.get_all("Classifier") or [] if c.startswith("License ::")
    ]
    named = [c.replace(" License", "").strip() for c in classifiers if c != "OSI Approved"]
    mapping = {
        "MIT": "MIT",
        "BSD": "BSD-3-Clause",
        "3-Clause BSD": "BSD-3-Clause",
        "Apache Software": "Apache-2.0",
        "ISC (ISCL)": "ISC",
    }
    mapped = [mapping.get(n, n) for n in named]
    if mapped:
        return " OR ".join(mapped)
    raw = (meta.get("License") or "").strip()
    return raw.splitlines()[0][:60] if raw else ""


def python_findings() -> list[Finding]:
    out = []
    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"] or "?"
        lic = _python_license(dist)
        out.append(
            Finding(ecosystem="python", package=name, version=dist.version, license=lic, ok=_allowed(lic))
        )
    return out


def npm_findings(node_modules: Path = NODE_MODULES) -> list[Finding]:
    out = []
    for pkg in sorted(node_modules.glob("**/package.json")):
        up = pkg.parent.parent
        top = up.name == "node_modules"
        scoped = up.name.startswith("@") and up.parent.name == "node_modules"
        if not (top or scoped):
            continue  # a package.json inside a package (lib/, dist/), not a package root
        data = json.loads(pkg.read_text(encoding="utf-8"))
        name = data.get("name") or (f"{up.name}/{pkg.parent.name}" if scoped else pkg.parent.name)
        lic = data.get("license") or ""
        if isinstance(lic, dict):
            lic = lic.get("type", "")
        if not lic and isinstance(data.get("licenses"), list):
            lic = " OR ".join(x.get("type", "") for x in data["licenses"])
        note = next(
            (v for k, v in REVIEWED.items() if name == k or (k.endswith("/") and name.startswith(k))), ""
        )
        out.append(
            Finding(
                ecosystem="npm",
                package=name,
                version=str(data.get("version", "")),
                license=str(lic),
                ok=bool(note) or _allowed(str(lic)),
                note=note,
            )
        )
    unique = {(f.package, f.version): f for f in out}
    return sorted(unique.values(), key=lambda f: f.package)


# --- asset register -----------------------------------------------------------------------


def assets_markdown() -> str:
    """ASSETS.md: every model, sound pack and font the engine ships or downloads, with its license."""
    from stagorix import models
    from stagorix.assets.sounds import load_catalog

    lines = [
        "# Assets and licenses",
        "",
        "Generated by `stagorix licenses --write-assets` from the model, sound and font catalogs;",
        "CI fails when this file and the catalogs disagree. Do not edit by hand.",
        "",
        "## Models (downloaded on first use, never committed)",
        "",
        "| Model | Source | License | Size |",
        "| --- | --- | --- | --- |",
    ]
    registry = [*models.WHISPER_MODELS.values(), models.YUNET, models.U2NET, models.SELFIE]
    for m in registry:
        lines.append(f"| {m.name} | {m.repo} | {m.license} | {m.size_mb} MB |")

    catalog = load_catalog()
    counts: dict[str, int] = {}
    for s in catalog.sounds:
        counts[s.pack] = counts.get(s.pack, 0) + 1
    lines += ["", "## Sounds (built by `stagorix sounds build`, never committed)", ""]
    lines += ["| Pack | Author | License | Sounds | Source |", "| --- | --- | --- | --- | --- |"]
    for pid, p in catalog.packs.items():
        lines.append(f"| {p.name} | {p.author} | {p.license} | {counts.get(pid, 0)} | {p.source} |")

    pkg = json.loads((ROOT / "render" / "package.json").read_text(encoding="utf-8"))
    fonts = sorted(k for k in pkg["dependencies"] if k.startswith("@fontsource/"))
    lines += ["", "## Fonts (bundled through Fontsource)", ""]
    lines += ["| Font | Package | License |", "| --- | --- | --- |"]
    for f in fonts:
        family = f.split("/", 1)[1].replace("-", " ").title()
        lines.append(f"| {family} | `{f}@{pkg['dependencies'][f]}` | OFL-1.1 |")
    lines += [
        "",
        "## Code dependencies",
        "",
        "Checked by `stagorix licenses` against an allowlist of permissive licenses; "
        "the Remotion license is reviewed separately (docs/DECISIONS.md, 2026-11-21).",
        "",
    ]
    return "\n".join(lines)
