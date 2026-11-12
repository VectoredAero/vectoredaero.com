#!/usr/bin/env python3
"""Correct digit 1 in the custom Vectored Aero display fonts.

Preserves the original glyph name, advance width, Unicode mapping, and
all other character outlines. The upstream font archive is retained as
a historical source; deployable OTF/TTF assets are updated in fonts/.
Copyright of original font design: 2026 Paul Heinrich.
"""
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile

from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.recordingPen import RecordingPen

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "Vectored Aero Fonts copy.zip"
OUTDIR = ROOT / "fonts"

# Geometric, unmistakable numeral one with angled flag, upright stem, and foot.
# Coordinates use the font's existing 1000-unit em. Existing sidebearings,
# advances, and full numeral height are unchanged.
WIDE = [(56,515),(230,700),(350,700),(350,120),(494,120),(494,0),
        (56,0),(56,120),(230,120),(230,525),(136,426)]
REGULAR = [(49,522),(178,700),(294,700),(294,122),(371,122),(371,0),
           (49,0),(49,122),(178,122),(178,525),(113,438)]

def recorded_outline(font, name):
    p = RecordingPen()
    font.getGlyphSet()[name].draw(p)
    return p.value

def change_one(srcbytes, points):
    font = TTFont(BytesIO(srcbytes))
    cmap = font.getBestCmap()
    name = cmap[ord("1")]
    advance, lsb = font["hmtx"].metrics[name]
    baseline = {k: recorded_outline(font, cmap[ord(k)]) for k in "02456789"}
    old_one = recorded_outline(font, name)
    if "CFF " in font:
        cff = font["CFF "].cff
        top = cff.topDictIndex[0]
        pen = T2CharStringPen(width=advance, glyphSet=None)
        pen.moveTo(points[0])
        for pt in points[1:]:
            pen.lineTo(pt)
        pen.closePath()
        top.CharStrings[name] = pen.getCharString(private=top.Private, globalSubrs=cff.GlobalSubrs)
    else:
        pen = TTGlyphPen(None)
        pen.moveTo(points[0])
        for pt in points[1:]:
            pen.lineTo(pt)
        pen.closePath()
        font["glyf"][name] = pen.glyph()
    out = BytesIO()
    font.save(out)
    verified = TTFont(BytesIO(out.getvalue()))
    assert verified.getBestCmap() == cmap, "Unicode mapping changed"
    assert verified["hmtx"].metrics[name] == (advance, lsb), "Glyph spacing changed"
    assert recorded_outline(verified, name) != old_one, "Numeral unchanged"
    for k, original in baseline.items():
        assert recorded_outline(verified, verified.getBestCmap()[ord(k)]) == original, "Unrelated digit changed: " + k
    return out.getvalue()

def main():
    OUTDIR.mkdir(exist_ok=True)
    with ZipFile(ARCHIVE) as z:
        for basename, points in [("VectoredAeroWide-Bold", WIDE), ("VectoredAero-Regular", REGULAR)]:
            for ext in (".otf", ".ttf"):
                file = basename + ext
                source = z.read("Vectored Aero Fonts copy/Fonts/" + file)
                patched = change_one(source, points)
                (OUTDIR / file).write_bytes(patched)
                print(file, len(patched), "bytes; revised glyph 1 validated")

if __name__ == "__main__":
    main()
