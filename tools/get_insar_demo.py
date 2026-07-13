import argparse
import json
import os
import sys
import urllib.request

BASE = "https://gws-access.jasmin.ac.uk/public/comet_lics/LiCSAR_products"

USAGE = """
Downloads a real COMET-LiCSAR interferogram pair for the Kairos InSAR viewer.

Finding the arguments (about two minutes):
 1. Open https://comet.nerc.ac.uk/comet-lics-portal/ and pan to Mexico City.
 2. Click a frame polygon covering the city. Its id looks like 143D_07709_131313
    (three digits, D or A, then numbers). The track is the first number, so
    143D_... means track 143.
 3. Open the frame page, pick an interferogram pair with clear fringes. The
    pair name is two dates joined: 20240101_20240113.
 4. Run, from the repo root:
    python tools/get_insar_demo.py --frame 143D_07709_131313 --pair 20240101_20240113

The script grabs the wrapped-phase and coherence PNGs plus the frame corner
coordinates, and installs them under backend/data/insar/mexico-city/ so the
InSAR section in Kairos lights up. Everything it downloads is a published,
research-grade product; Kairos displays it with attribution and does not
modify it.
"""


def fetch(url: str, dest: str) -> bool:
    try:
        print(f"  {url}")
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print(f"  not found ({e})")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Install a LiCSAR interferogram for the Kairos InSAR viewer",
        epilog=USAGE,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--frame", required=True, help="LiCSAR frame id, like 143D_07709_131313")
    parser.add_argument("--pair", required=True, help="date pair, like 20240101_20240113")
    parser.add_argument("--site", default="mexico-city", help="Kairos site id to install into")
    parser.add_argument("--bbox", help="min_lon,min_lat,max_lon,max_lat override if the frame polygon fetch fails")
    args = parser.parse_args()

    track = str(int(args.frame[:3]))
    frame_base = f"{BASE}/{track}/{args.frame}"
    pair_base = f"{frame_base}/interferograms/{args.pair}"

    out_dir = os.path.join("backend", "data", "insar", args.site)
    os.makedirs(out_dir, exist_ok=True)

    print("Downloading wrapped interferogram:")
    ifg_ok = fetch(
        f"{pair_base}/{args.frame}_{args.pair}.geo.diff_pha.png",
        os.path.join(out_dir, "interferogram.png"),
    ) or fetch(
        f"{pair_base}/{args.frame}_{args.pair}.geo.diff.png",
        os.path.join(out_dir, "interferogram.png"),
    )

    print("Downloading coherence:")
    cc_ok = fetch(
        f"{pair_base}/{args.frame}_{args.pair}.geo.cc.png",
        os.path.join(out_dir, "coherence.png"),
    )

    bbox = None
    if args.bbox:
        bbox = [float(x) for x in args.bbox.split(",")]
    else:
        poly_path = os.path.join(out_dir, "frame-poly.txt")
        if fetch(f"{frame_base}/metadata/{args.frame}-poly.txt", poly_path):
            lons, lats = [], []
            with open(poly_path) as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            lons.append(float(parts[0]))
                            lats.append(float(parts[1]))
                        except ValueError:
                            continue
            if lons and lats:
                bbox = [min(lons), min(lats), max(lons), max(lats)]

    if not (ifg_ok and cc_ok):
        print("\nDownload incomplete. Check the frame id and pair on the portal.")
        sys.exit(1)
    if not bbox:
        print("\nCould not determine the frame corners. Rerun with --bbox min_lon,min_lat,max_lon,max_lat")
        print("(the frame page on the portal shows its extent).")
        sys.exit(1)

    dates = args.pair.split("_")
    meta = {
        "bbox": bbox,
        "frame": args.frame,
        "dates": [
            f"{dates[0][:4]}-{dates[0][4:6]}-{dates[0][6:]}",
            f"{dates[1][:4]}-{dates[1][4:6]}-{dates[1][6:]}",
        ],
        "source": "COMET-LiCSAR (University of Leeds / NERC)",
    }
    with open(os.path.join(out_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\nInstalled into {out_dir}")
    print(f"Frame {args.frame}, pair {meta['dates'][0]} to {meta['dates'][1]}, bbox {bbox}")
    print("Restart the backend and the InSAR section in Research tools goes live.")


if __name__ == "__main__":
    main()
