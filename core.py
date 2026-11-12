"""Backend for EasyEDA -> KiCad converter.

Fetches a public EasyEDA component by UUID (community components included)
and writes KiCad symbol, footprint and 3D model files.

Uses the conversion engine from easyeda2kicad.py (MIT), but bypasses its
LCSC-only API layer: the component JSON is fetched directly by UUID.
"""

from __future__ import annotations

import gzip
import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from easyeda2kicad.easyeda.easyeda_api import EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import (
    EasyedaFootprintImporter,
    EasyedaSymbolImporter,
)
from easyeda2kicad.kicad.export_kicad_3d_model import Exporter3dModelKicad
from easyeda2kicad.kicad.export_kicad_footprint import ExporterFootprintKicad
from easyeda2kicad.kicad.export_kicad_symbol import ExporterSymbolKicad
from easyeda2kicad.kicad.parameters_kicad_symbol import (
    KICAD_SYM_VERSION_20231120,
)

API_URL = "https://easyeda.com/api/components/{uuid}"
UUID_RE = re.compile(r"[0-9a-fA-F]{32}")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class ConversionError(Exception):
    """User-facing conversion error."""


def parse_uuid(text: str) -> str:
    """Extract a 32-hex EasyEDA UUID from a link or raw id."""
    text = (text or "").strip()
    if not text:
        raise ConversionError("Paste an EasyEDA component link.")
    match = UUID_RE.search(text)
    if not match:
        raise ConversionError(
            "No component UUID found in the link. Expected a link like "
            "https://easyeda.com/component/<32 hex characters>."
        )
    return match.group(0).lower()


def safe_name(value: str, fallback: str, limit: int = 60) -> str:
    """Make a filesystem/KiCad friendly name."""
    value = (value or "").strip()
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("._-")
    if not value:
        value = fallback
    return value[:limit]


def _fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": USER_AGENT,
            "Referer": "https://easyeda.com/",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ConversionError("Component not found (404). Check the link.") from exc
        raise ConversionError(f"EasyEDA returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise ConversionError(
            f"Could not connect to EasyEDA: {exc.reason}"
        ) from exc

    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConversionError("EasyEDA returned an unexpected response (not JSON).") from exc

    if not data.get("success") or not data.get("result"):
        raise ConversionError(
            "EasyEDA did not return component data. The component may be private or deleted."
        )
    return data["result"]


def _prepare(result: dict[str, Any], uuid: str) -> dict[str, Any]:
    """Normalise the API response into easyeda2kicad's expected shape."""
    data_str = result.get("dataStr") or {}
    head = data_str.get("head") or {}
    c_para = head.get("c_para") or {}

    package = result.get("packageDetail") or {}
    package_data = package.get("dataStr") if package else None

    has_symbol = bool(c_para.get("name"))
    is_device = has_symbol and bool(package_data)
    kind = "device" if is_device else ("symbol" if has_symbol else "footprint")
    footprint_data = package_data or data_str
    fp_head = footprint_data.get("head") or {}
    fp_para = fp_head.get("c_para") or {}

    title = (
        result.get("title")
        or fp_para.get("package")
        or c_para.get("name")
        or f"part_{uuid[:8]}"
    )
    footprint_name = safe_name(
        fp_para.get("package") or title, f"part_{uuid[:8]}"
    )

    # Normalise names so both exporters and the files agree.
    fp_para["package"] = footprint_name
    symbol_name = None
    if is_device:
        symbol_name = safe_name(c_para.get("name") or title, f"part_{uuid[:8]}")
        c_para["name"] = symbol_name
        c_para["package"] = footprint_name

    lcsc = result.get("lcsc") or {}
    cad: dict[str, Any] = {
        "packageDetail": {"dataStr": footprint_data, "title": footprint_name},
        "lcsc": lcsc,
        "description": result.get("description") or "",
        "tags": result.get("tags") or [],
    }
    if is_device:
        cad["dataStr"] = data_str

    return {
        "cad": cad,
        "is_device": is_device,
        "kind": kind,
        "title": title,
        "symbol_name": symbol_name,
        "footprint_name": footprint_name,
        "shape": footprint_data.get("shape") or [],
    }


def modernize_footprint(path: Path) -> None:
    """Rewrite the legacy ``(module ...)`` header into KiCad 7+ ``(footprint ...)``.

    easyeda2kicad still emits the KiCad 5 style header. KiCad itself upgrades it,
    but Fusion's KiCad importer expects a modern footprint file.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    if text.lstrip().startswith("(footprint"):
        return
    match = re.match(
        r"\s*\(module\s+(\S+)\s+\(layer\s+([^)]+)\)\s*(?:\(tedit\s+\S+\))?",
        text,
    )
    if not match:
        return
    name = match.group(1).split(":")[-1].strip('"')
    layer = match.group(2).strip().strip('"')
    header = (
        f'(footprint "{name}"\n'
        f"\t(version 20240108)\n"
        f'\t(generator "easyeda2kicad")\n'
        f'\t(layer "{layer}")'
    )
    path.write_text(header + text[match.end():], encoding="utf-8")


def convert(
    link: str,
    out_dir: str | Path,
    want_symbol: bool = True,
    want_footprint: bool = True,
    want_3d: bool = True,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Convert one EasyEDA component link into KiCad files."""
    emit = log or (lambda _m: None)

    uuid = parse_uuid(link)
    emit(f"UUID: {uuid}")
    emit("Fetching component data…")
    result = _fetch_json(API_URL.format(uuid=uuid))
    prepared = _prepare(result, uuid)

    title = prepared["title"]
    symbol_name = prepared["symbol_name"]
    footprint_name = prepared["footprint_name"]
    kind = prepared["kind"]
    is_device = kind == "device"
    emit(f"Component: {title}")
    emit(
        "Type: "
        + {
            "device": "symbol + footprint",
            "symbol": "symbol only",
            "footprint": "footprint only",
        }[kind]
    )

    display_name = symbol_name or footprint_name
    root = Path(out_dir).expanduser().resolve()
    target = root / f"{display_name}_{uuid[:8]}"
    target.mkdir(parents=True, exist_ok=True)

    sym_path = target / f"{display_name}.kicad_sym"
    fp_dir = target / f"{footprint_name}.pretty"
    fp_path = fp_dir / f"{footprint_name}.kicad_mod"
    shapes_dir = target / f"{footprint_name}.3dshapes"

    result_info: dict[str, Any] = {
        "uuid": uuid,
        "title": title,
        "name": display_name,
        "kind": kind,
        "dir": str(target),
        "symbol": None,
        "footprint": None,
        "step": None,
        "wrl": None,
        "warnings": [],
    }

    if want_symbol:
        if kind in ("device", "symbol"):
            emit("Converting symbol…")
            symbol = EasyedaSymbolImporter(
                easyeda_cp_cad_data=prepared["cad"]
            ).get_symbol()
            if sym_path.exists():
                sym_path.unlink()
            ExporterSymbolKicad(
                symbol=symbol,
                lib_path=str(sym_path),
                version=KICAD_SYM_VERSION_20231120,
            ).save_to_lib(
                lib_path=str(sym_path),
                footprint_lib_name=footprint_name,
                overwrite=True,
            )
            if sym_path.is_file():
                result_info["symbol"] = str(sym_path)
                emit(f"  symbol: {sym_path.name}")
        else:
            msg = "This component has no symbol — footprint only."
            result_info["warnings"].append(msg)
            emit("  " + msg)

    if kind == "symbol":
        if want_footprint:
            msg = "This component has no footprint — symbol only."
            result_info["warnings"].append(msg)
            emit("  " + msg)
        if want_3d:
            msg = "No 3D model: the component has no footprint."
            result_info["warnings"].append(msg)
            emit("  " + msg)

    if kind != "symbol" and (want_footprint or want_3d):
        emit("Converting footprint…")
        footprint = EasyedaFootprintImporter(
            easyeda_cp_cad_data=prepared["cad"]
        ).get_footprint()
        if footprint.pads:
            has_smd = any(pad.hole_radius <= 0 for pad in footprint.pads)
            footprint.info.fp_type = "smd" if has_smd else "tht"

        model = footprint.model_3d
        if want_3d and model is not None:
            emit(f"Downloading 3D model “{model.name or model.uuid}”…")
            api = EasyedaApi()
            raw_obj = api.get_raw_3d_model_obj(uuid=model.uuid)
            step_bytes = api.get_step_3d_model(uuid=model.uuid)
            if not raw_obj and not step_bytes:
                msg = "The footprint references a 3D model, but it could not be downloaded."
                result_info["warnings"].append(msg)
                emit("  " + msg)
                footprint.model_3d = None
            else:
                model_name = safe_name(
                    model.name or f"model_{model.uuid[:8]}",
                    f"model_{model.uuid[:8]}",
                )
                try:
                    model.name = model_name
                except Exception:
                    model = replace(model, name=model_name)
                model.raw_obj = raw_obj
                model.step = step_bytes
                footprint.model_3d = model

                Exporter3dModelKicad(model).export(str(shapes_dir), overwrite=True)
                if step_bytes and not (shapes_dir / f"{model_name}.step").is_file():
                    shapes_dir.mkdir(parents=True, exist_ok=True)
                    (shapes_dir / f"{model_name}.step").write_bytes(step_bytes)

                if (shapes_dir / f"{model_name}.step").is_file():
                    result_info["step"] = str(shapes_dir / f"{model_name}.step")
                if (shapes_dir / f"{model_name}.wrl").is_file():
                    result_info["wrl"] = str(shapes_dir / f"{model_name}.wrl")
                emit("  3D: " + (model_name + ".step"))
        elif want_3d:
            msg = "This component has no 3D model (no SVGNODE in the footprint)."
            result_info["warnings"].append(msg)
            emit("  " + msg)

        if want_footprint:
            ExporterFootprintKicad(footprint=footprint).export(
                footprint_full_path=str(fp_path),
                model_3d_path=str(shapes_dir).replace("\\", "/"),
                model_3d_extension="wrl",
            )
            modernize_footprint(fp_path)
            if fp_path.is_file():
                result_info["footprint"] = str(fp_path)
                emit(f"  footprint: {fp_path.name}")

    if not result_info["symbol"] and not result_info["footprint"]:
        raise ConversionError(
            "Could not create a symbol or a footprint. "
            "Make sure the component is public and is a part, not a schematic sheet."
        )

    emit("Done.")
    return result_info
