"""Rebuild deterministic CC0 synthetic fixtures. No external market data."""

import csv
import hashlib
import io
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "fixtures"


def main():
    ROOT.mkdir(exist_ok=True)
    dates, day = [], date(2026, 1, 2)
    while len(dates) < 20:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day += timedelta(days=1)
    closes = [100, 101, 102, 103, 104, 106, 108, 107, 112, 110, 114, 113, 117, 116, 120, 118, 123, 122, 126, 124]
    rows = []
    for i, session in enumerate(dates):
        opening = 100 if i == 0 else closes[i - 1]
        closing = closes[i]
        rows.append([session, "SYNTH", opening, max(opening, closing) + 1, min(opening, closing) - 1, closing, 100000])
    fields = ["date", "symbol", "open", "high", "low", "close", "volume"]
    for identity in (
        "clean_momentum",
        "leaky_next_close",
        "timing_trap",
        "missing_open",
        "duplicate_sessions",
        "invalid_ohlc",
    ):
        variant = [list(row) for row in rows]
        if identity == "timing_trap":
            # Alternating moves straddle the default threshold. Future-close
            # selection and lawful trailing selection therefore choose different
            # sessions. All returns are still computed by the same engine.
            trap = [100, 100, 100, 100, 100, 100, 103, 99, 104, 98, 105, 97, 106, 96, 107, 95, 108, 94, 109, 93]
            variant = []
            for i, session in enumerate(dates):
                opening, closing = trap[max(0, i - 1)], trap[i]
                variant.append(
                    [session, "SYNTH", opening, max(opening, closing) + 1, min(opening, closing) - 1, closing, 100000]
                )
        if identity == "missing_open":
            variant[8][2] = ""
        if identity == "duplicate_sessions":
            variant[8][0] = variant[7][0]
        if identity == "invalid_ohlc":
            variant[8][3] = 1
        text = io.StringIO(newline="")
        writer = csv.writer(text, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(variant)
        content = text.getvalue().encode("utf-8")
        (ROOT / f"{identity}.csv").write_bytes(content)
        manifest = {
            "dataset_id": identity,
            "byte_hash": hashlib.sha256(content).hexdigest(),
            "row_count": len(variant),
            "start_session": dates[0],
            "end_session": dates[-1],
        }
        (ROOT / f"{identity}.json").write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")


if __name__ == "__main__":
    main()
