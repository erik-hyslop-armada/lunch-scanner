#!/usr/bin/env python3
"""
Generate QR codes from a plain CSV — **no Google Cloud, no API keys**.

Input CSV (header row required):
  full_name   – personens namn (obligatorisk)
  email       – frivillig
  token       – frivillig (om saknas skapas slumpsträng)

Utdata:
  • PNG- eller SVG-filer i vald mapp
  • Ett nytt CSV (default "output.csv") med token & filnamn ‑ färdigt att
    klistra in i Google‑arket
  • (flagga --zip) en ZIP‑fil med alla bilder

Exempel:
  python generate_qr.py \
      --csv people.csv \
      --webapp-url "https://script.google.com/macros/s/XXXX/exec" \
      --out qr_codes \
      --format png \
      --zip

Kräver:
  pip install qrcode[pil] pandas
"""

from __future__ import annotations

import argparse
import random
import string
import sys
import zipfile
from pathlib import Path

import pandas as pd
import qrcode

# --------------------------- helper functions --------------------------- #

def random_token(length: int = 8) -> str:
    """Return a random alnum token of given length."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=length))


def make_qr(data: str, out_path: Path, fmt: str = "png") -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% tolerans
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    if fmt == "svg":
        from qrcode.image.svg import SvgImage  # lazy‑import

        img = qr.make_image(image_factory=SvgImage)
    else:
        img = qr.make_image(fill_color="black", back_color="white")

    img.save(out_path)


# ------------------------------- main ---------------------------------- #

def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Generate QR codes from a CSV file.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--csv", required=True, help="Input CSV path")
    p.add_argument("--webapp-url", required=True, help="Apps Script webapp URL (without ?token=)")
    p.add_argument("--out", default="qr_out", help="Directory to write QR images")
    p.add_argument("--format", choices=["png", "svg"], default="png")
    p.add_argument("--token-len", type=int, default=8, help="Length of random token if missing")
    p.add_argument("--zip", action="store_true", help="Also create ZIP with all images")
    p.add_argument("--output-csv", default="output.csv", help="Path for augmented CSV")

    args = p.parse_args(argv)

    df = pd.read_csv(args.csv)
    if "full_name" not in df.columns:
        sys.exit("[error] CSV måste ha kolumnen 'full_name'")

    if "token" not in df.columns:
        df["token"] = ""

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    filenames: list[str] = []
    digits = len(str(len(df)))

    for idx, row in df.iterrows():
        token = str(row["token"]).strip()
        if not token or token.lower() == "nan":  # ny token
            token = random_token(args.token_len)
            df.at[idx, "token"] = token

        url = f"{args.webapp_url.rstrip('?')}?token={token}"
        fname = f"{str(idx + 1).zfill(digits)}_{token}.{args.format}"
        make_qr(url, out_dir / fname, fmt=args.format)
        filenames.append(fname)
        print(f"✔ {fname}")

    df["qr_file"] = filenames
    df.to_csv(args.output_csv, index=False)
    print(f"[done] Wrote {args.output_csv}")

    if args.zip:
        zip_path = out_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in filenames:
                zf.write(out_dir / name, arcname=name)
        print(f"[done] Created {zip_path}")


if __name__ == "__main__":
    main()
