#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UGV circle demo · smoother full-circle visualization (Sunray-aligned)."""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

import matplotlib

matplotlib.use(os.environ.get("MPLBACKEND", "Agg"))
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Circle

OUT = Path(__file__).resolve().parents[1] / "output"
R = 1.0
V = 0.5
CENTER = (0.0, 0.0)
LOOPS = 2.0  # full two loops so the circle is obvious
PHASE_LABEL = {
    "MOVE_TO_CIRCLE": "1) Drive to circle",
    "CIRCLE": "2) Circle track",
    "RETURN_ORIGIN": "3) Return home",
    "HOLD": "4) Hold",
}
PHASE_COLOR = {
    "MOVE_TO_CIRCLE": "#f59e0b",
    "CIRCLE": "#38bdf8",
    "RETURN_ORIGIN": "#34d399",
    "HOLD": "#94a3b8",
}


def simulate(dt: float = 0.02):
    """Exact geometry: straight to (R,0), then perfect circle, then straight home."""
    x = y = t = 0.0
    rows = []

    def log(phase):
        rows.append((round(t, 3), x, y, phase))

    # 1) go to circle entry (R, 0)
    phase = "MOVE_TO_CIRCLE"
    while x < R - 1e-6:
        t += dt
        x = min(R, x + V * dt)
        y = 0.0
        log(phase)

    # 2) perfect circle, CCW, LOOPS revolutions starting at theta=0
    phase = "CIRCLE"
    theta = 0.0
    total = LOOPS * 2 * math.pi
    while theta < total - 1e-9:
        t += dt
        dtheta = (V / R) * dt
        if theta + dtheta > total:
            dtheta = total - theta
        theta += dtheta
        x = CENTER[0] + R * math.cos(theta)
        y = CENTER[1] + R * math.sin(theta)
        log(phase)

    # 3) return to origin along radius
    phase = "RETURN_ORIGIN"
    while math.hypot(x, y) > 0.02:
        t += dt
        dist = math.hypot(x, y) or 1e-9
        step = min(V * dt, dist)
        x -= step * x / dist
        y -= step * y / dist
        log(phase)

    phase = "HOLD"
    x = y = 0.0
    for _ in range(40):
        t += dt
        log(phase)
    return rows


def _draw_static(rows):
    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    phases = [r[3] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_facecolor("#f8fafc")
    ax.add_patch(
        Circle(CENTER, R, fill=False, ls="--", lw=2.0, color="#64748b", label="target r=1m", zorder=1)
    )
    # draw by phase segments
    labeled = set()
    start = 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or phases[i] != phases[start]:
            pname = phases[start]
            label = PHASE_LABEL[pname] if pname not in labeled else None
            labeled.add(pname)
            ax.plot(
                xs[start:i],
                ys[start:i],
                color=PHASE_COLOR[pname],
                lw=3.0,
                solid_capstyle="round",
                zorder=2,
                label=label,
            )
            start = i

    ax.plot(0, 0, "o", color="#16a34a", ms=11, zorder=3, label="home")
    ax.plot(R, 0, "D", color="#ea580c", ms=8, zorder=3, label="circle entry")
    ax.set_aspect("equal")
    ax.set_xlim(-1.55, 1.55)
    ax.set_ylim(-1.55, 1.55)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("UGV Demo · To circle → 2 full loops → Home", fontsize=13, pad=12)
    ax.grid(True, alpha=0.35)
    # dedupe legend
    handles, labels = ax.get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    ax.legend(uniq.values(), uniq.keys(), loc="upper right", fontsize=8, framealpha=0.95)
    path = OUT / "ugv_circle.png"
    fig.tight_layout()
    fig.savefig(path, dpi=170, facecolor="white")
    plt.close(fig)
    return path


def _draw_gif(rows):
    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    ts = [r[0] for r in rows]
    phases = [r[3] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 7))
    fig.patch.set_facecolor("#0b1220")
    ax.set_facecolor("#0f172a")
    ax.add_patch(Circle(CENTER, R, fill=False, ls="--", lw=1.8, color="#94a3b8", zorder=1))
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-1.6, 1.6)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.25, color="#334155")
    ax.tick_params(colors="#cbd5e1")
    ax.set_xlabel("x (m)", color="#e2e8f0")
    ax.set_ylabel("y (m)", color="#e2e8f0")
    ax.set_title("UGV top view · circle mission", color="#f8fafc", fontsize=13)
    for spine in ax.spines.values():
        spine.set_color("#334155")

    (trail_move,) = ax.plot([], [], color=PHASE_COLOR["MOVE_TO_CIRCLE"], lw=3.0, zorder=2)
    (trail_circle,) = ax.plot([], [], color=PHASE_COLOR["CIRCLE"], lw=3.0, zorder=2)
    (trail_back,) = ax.plot([], [], color=PHASE_COLOR["RETURN_ORIGIN"], lw=3.0, zorder=2)
    (car,) = ax.plot([], [], marker="s", markersize=12, color="#f43f5e", zorder=4)
    (heading,) = ax.plot([], [], color="#fbbf24", lw=2.5, zorder=5)
    banner = fig.text(0.5, 0.04, "", ha="center", color="#f8fafc", fontsize=14, fontweight="bold")
    progress = fig.text(0.5, 0.01, "", ha="center", color="#94a3b8", fontsize=10)

    n_frames = 160
    idxs = [int(i * (len(rows) - 1) / (n_frames - 1)) for i in range(n_frames)]

    def segment(phase_name, upto):
        xx, yy = [], []
        for i in range(upto + 1):
            if phases[i] == phase_name:
                xx.append(xs[i])
                yy.append(ys[i])
        return xx, yy

    def update(fi):
        idx = idxs[fi]
        trail_move.set_data(*segment("MOVE_TO_CIRCLE", idx))
        trail_circle.set_data(*segment("CIRCLE", idx))
        trail_back.set_data(*segment("RETURN_ORIGIN", idx))
        car.set_data([xs[idx]], [ys[idx]])

        # heading from last delta
        if idx > 0:
            dx = xs[idx] - xs[idx - 1]
            dy = ys[idx] - ys[idx - 1]
            norm = math.hypot(dx, dy) or 1.0
            hx, hy = 0.28 * dx / norm, 0.28 * dy / norm
        else:
            hx, hy = 0.28, 0.0
        heading.set_data([xs[idx], xs[idx] + hx], [ys[idx], ys[idx] + hy])

        p = phases[idx]
        banner.set_text(PHASE_LABEL[p])
        banner.set_color(PHASE_COLOR[p])
        pct = 100.0 * idx / (len(rows) - 1)
        progress.set_text(f"t = {ts[idx]:.1f}s   progress {pct:.0f}%   pos=({xs[idx]:.2f}, {ys[idx]:.2f})")
        return trail_move, trail_circle, trail_back, car, banner, progress

    anim = FuncAnimation(fig, update, frames=n_frames, interval=50, blit=False)
    path = OUT / "ugv_circle.gif"
    anim.save(path, writer=PillowWriter(fps=18), dpi=130)
    plt.close(fig)
    return path


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = simulate()
    with (OUT / "ugv_circle.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "x", "y", "phase"])
        w.writerows(rows)

    static = _draw_static(rows)
    gif = _draw_gif(rows)
    print(f"[OK] {static}")
    print(f"[OK] {gif}")
    print("Phases:", " -> ".join(dict.fromkeys(r[3] for r in rows)))
    print(f"samples={len(rows)}  loops={LOOPS}")


if __name__ == "__main__":
    main()
