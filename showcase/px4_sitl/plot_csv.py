"""Plot PX4 SITL mission CSV for demo screenshots."""
from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

CSV = Path(__file__).resolve().parent / "sunray_mission_run_opt.csv"
OUT = Path(__file__).resolve().parent / "10_px4_mission_trajectory_opt.png"

COLORS = {
    "WAIT_CONNECT": "#6b7280",
    "SET_MODE": "#8b5cf6",
    "ARM": "#f59e0b",
    "TAKEOFF": "#3b82f6",
    "GOTO": "#06b6d4",
    "WAIT_WP": "#10b981",
    "RTL": "#a855f7",
    "LAND": "#ef4444",
    "ABORT": "#b91c1c",
    "DONE": "#64748b",
}


def main() -> None:
    ts, xs, ys, zs, phases = [], [], [], [], []
    with CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ts.append(float(row["t"]))
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))
            zs.append(float(row["z"]))
            phases.append(row["phase"])

    fig = plt.figure(figsize=(12.2, 5.2))
    ax3 = fig.add_subplot(1, 2, 1, projection="3d")
    axh = fig.add_subplot(1, 2, 2)

    for i in range(len(ts) - 1):
        c = COLORS.get(phases[i], "#334155")
        ax3.plot(xs[i : i + 2], ys[i : i + 2], zs[i : i + 2], color=c, lw=2.0)
        axh.plot(ts[i : i + 2], zs[i : i + 2], color=c, lw=2.2)

    ax3.scatter([xs[0]], [ys[0]], [zs[0]], c="#22c55e", s=40, label="start")
    ax3.scatter([xs[-1]], [ys[-1]], [zs[-1]], c="#ef4444", s=40, label="end")
    ax3.set_xlabel("x (m)")
    ax3.set_ylabel("y (m)")
    ax3.set_zlabel("z (m)")
    ax3.set_title("PX4 SITL · 3D path")
    ax3.legend(loc="upper left", fontsize=8)

    axh.axhline(1.2, color="#94a3b8", ls="--", lw=1, label="takeoff 1.2 m")
    axh.set_xlabel("time (s)")
    axh.set_ylabel("z (m)")
    axh.set_title("Altitude by phase")
    axh.grid(True, alpha=0.3)

    seen = list(OrderedDict.fromkeys(phases))
    for p in seen:
        axh.plot([], [], color=COLORS.get(p, "#334155"), lw=3, label=p)
    axh.legend(loc="lower left", fontsize=8, ncol=2, framealpha=0.92)

    fig.suptitle("Sunray secondary mission on PX4 SITL  ·  takeoff → waypoints → land", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT, dpi=160, bbox_inches="tight", facecolor="white")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
