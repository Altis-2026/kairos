import argparse
import json
import os
import struct
import sys
import urllib.request

# COMET-LiCSAR moved off JASMIN in October 2025. The products now live in the
# CEDA archive, and the layout changed with the move: interferogram pairs sit
# directly under the frame directory rather than in an `interferograms/`
# subfolder, and the per-frame `-poly.txt` corner file is gone. The frame
# extent is read out of the GeoTIFF header instead — see `frame_bbox`.
BASE = "https://dap.ceda.ac.uk/neodc/comet/data/licsar_products"
BROWSE = "https://data.ceda.ac.uk/neodc/comet/data/licsar_products"

USAGE = """
Installs a real COMET-LiCSAR interferogram for the Kairos InSAR viewer.

The defaults are a working Mexico City subsidence pair, so from the repo root:

    python tools/get_insar_demo.py

is enough. Everything it downloads is a published, research-grade product;
Kairos displays it with attribution and does not modify it.

To install a different frame or pair, browse the CEDA archive:

    https://data.ceda.ac.uk/neodc/comet/data/licsar_products

Tracks are top-level directories, frames sit inside them, and each frame lists
its interferogram pairs as `YYYYMMDD_YYYYMMDD` directories. Then:

    python tools/get_insar_demo.py --frame 005A_07021_131313 \\
        --pair 20240311_20240919 --site mexico-city

Picking a pair: the fringes ARE the measurement, so a pair needs enough time
between acquisitions for the ground to have moved a visible fraction of a
fringe (2.8 cm). Over Mexico City a 12-day pair moves well under one fringe
and looks like noise; the 192-day default gives roughly half a dozen, which is
what makes the subsidence bowl legible.
"""

#: Known-good defaults, verified against the CEDA archive.
SITES = {
    "mexico-city": {
        "frame": "005A_07021_131313",
        "pair": "20240311_20240919",
    },
}


def fetch(url: str, dest: str) -> bool:
    try:
        print(f"  {url}")
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"  not found ({e})")
        return False


def frame_bbox(track: str, frame: str) -> list | None:
    """
    Read the frame's geographic extent from a product GeoTIFF's header.

    The corner file the old JASMIN layout provided is gone, but every frame
    ships georeferenced metadata rasters. Only the header is needed, so this
    asks for the first chunk of the file with a Range request rather than
    pulling a whole raster down for four numbers.
    """
    for kind in ("hgt", "E", "U"):
        url = f"{BASE}/{track}/{frame}/metadata/{frame}.geo.{kind}.tif"
        try:
            req = urllib.request.Request(url, headers={"Range": "bytes=0-300000"})
            buf = urllib.request.urlopen(req, timeout=90).read()
        except Exception:
            continue
        try:
            return _geotiff_bbox(buf)
        except Exception:
            continue
    return None


def _geotiff_bbox(buf: bytes) -> list:
    """Pull width/height, pixel scale and tiepoint out of a (Big)TIFF header."""
    endian = "<" if buf[:2] == b"II" else ">"
    version = struct.unpack(endian + "H", buf[2:4])[0]

    if version == 42:
        offset = struct.unpack(endian + "I", buf[4:8])[0]
        count = struct.unpack(endian + "H", buf[offset:offset + 2])[0]
        entry_size, header = 12, 2

        def entry(at):
            tag, typ = struct.unpack(endian + "HH", buf[at:at + 4])
            n = struct.unpack(endian + "I", buf[at + 4:at + 8])[0]
            return tag, typ, n, struct.unpack(endian + "I", buf[at + 8:at + 12])[0]
    elif version == 43:                       # BigTIFF
        offset = struct.unpack(endian + "Q", buf[8:16])[0]
        count = struct.unpack(endian + "Q", buf[offset:offset + 8])[0]
        entry_size, header = 20, 8

        def entry(at):
            tag, typ = struct.unpack(endian + "HH", buf[at:at + 4])
            n = struct.unpack(endian + "Q", buf[at + 4:at + 12])[0]
            return tag, typ, n, struct.unpack(endian + "Q", buf[at + 12:at + 20])[0]
    else:
        raise ValueError(f"not a TIFF (version {version})")

    tags = {}
    for i in range(count):
        tag, typ, n, value = entry(offset + header + i * entry_size)
        tags[tag] = (typ, n, value)

    def read(tag):
        typ, n, value = tags[tag]
        if typ == 12:                          # DOUBLE, stored out of line
            return struct.unpack(endian + f"{n}d", buf[value:value + 8 * n])
        return value

    width, height = read(256), read(257)
    scale_x, scale_y, _ = read(33550)
    tiepoint = read(33922)
    left, top = tiepoint[3], tiepoint[4]
    return [
        round(left, 4),
        round(top - height * scale_y, 4),
        round(left + width * scale_x, 4),
        round(top, 4),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Install a LiCSAR interferogram for the Kairos InSAR viewer",
        epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--site", default="mexico-city",
                        help="Kairos site id to install into")
    parser.add_argument("--frame", help="LiCSAR frame id, like 005A_07021_131313")
    parser.add_argument("--pair", help="date pair, like 20240311_20240919")
    parser.add_argument("--bbox",
                        help="min_lon,min_lat,max_lon,max_lat, if the frame "
                             "extent cannot be read from the product metadata")
    args = parser.parse_args()

    known = SITES.get(args.site, {})
    frame = args.frame or known.get("frame")
    pair = args.pair or known.get("pair")
    if not frame or not pair:
        print(f"No default frame/pair for site '{args.site}'. "
              f"Pass --frame and --pair; see --help for how to find them.")
        return 1

    # Track directories are zero-padded to at least two digits in the archive
    # ("05", "41", "143"), while the frame id always uses three ("005A_...").
    track = f"{int(frame[:3]):02d}"
    pair_base = f"{BASE}/{track}/{frame}/{pair}"

    out_dir = os.path.join("backend", "data", "insar", args.site)
    os.makedirs(out_dir, exist_ok=True)

    print("Downloading wrapped interferogram:")
    ifg_ok = fetch(
        f"{pair_base}/{pair}.geo.diff.png",
        os.path.join(out_dir, "interferogram.png"),
    )

    print("Downloading coherence (optional, skipped on failure):")
    cc_ok = fetch(
        f"{pair_base}/{pair}.geo.cc.png",
        os.path.join(out_dir, "coherence.png"),
    )
    if not cc_ok:
        stale = os.path.join(out_dir, "coherence.png")
        if os.path.exists(stale):
            os.remove(stale)

    if not ifg_ok:
        print(f"\nDownload failed. Check that the pair exists:")
        print(f"  {BROWSE}/{track}/{frame}")
        return 1

    if args.bbox:
        bbox = [float(x) for x in args.bbox.split(",")]
    else:
        print("Reading the frame extent from the product metadata:")
        bbox = frame_bbox(track, frame)
    if not bbox:
        print("\nCould not read the frame extent. Rerun with "
              "--bbox min_lon,min_lat,max_lon,max_lat")
        return 1

    meta = {
        "bbox": bbox,
        "frame": frame,
        "dates": [
            f"{pair[:4]}-{pair[4:6]}-{pair[6:8]}",
            f"{pair[9:13]}-{pair[13:15]}-{pair[15:17]}",
        ],
        "source": "COMET-LiCSAR (University of Leeds / NERC)",
    }
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nInstalled into {out_dir}")
    print(f"Frame {frame}, pair {meta['dates'][0]} to {meta['dates'][1]}")
    print(f"Extent {bbox}")
    print("Restart the backend and the InSAR section in Research tools goes live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
