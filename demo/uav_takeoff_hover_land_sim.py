#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无人机任务逻辑 Demo · 强化可视化（对齐 Sunray takeoff_hover_land.py）"""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

import matplotlib

matplotlib.use(os.environ.get("MPLBACKEND", "Agg"))
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parents[1] / "output"
TAKEOFF_H = 1.2
# 图里用英文，避免云主机缺中文字体变成方框；中文放网页 HTML
PHASE_CN = {
    "WAIT_CONNECT": "WAIT",
    "CMD_CONTROL": "CMD_MODE",
    "ARM": "ARM",
    "TAKEOFF": "TAKEOFF",
    "HOVER": "HOVER",
    "LAND": "LAND",
    "LANDED": "LANDED",
}


def simulate(dt: float = 0.04):
    t = x = y = z = 0.0
    phase = "WAIT_CONNECT"
    timer = 0.0
    rows = []

    def log():
        rows.append((round(t, 3), x, y, z, phase))

    for phase, dur in [("WAIT_CONNECT", 1.0), ("CMD_CONTROL", 0.8), ("ARM", 1.0)]:
        timer = 0.0
        while timer < dur:
            t += dt
            timer += dt
            log()

    phase = "TAKEOFF"
    while z < TAKEOFF_H - 0.01:
        t += dt
        z = min(TAKEOFF_H, z + 0.45 * dt)
        # 轻微侧向扰动（真实感），幅度很小
        x = 0.03 * math.sin(2.2 * t)
        log()

    phase = "HOVER"
    timer = 0.0
    while timer < 3.5:
        t += dt
        timer += dt
        z = TAKEOFF_H + 0.025 * math.sin(3.0 * t)
        x = 0.02 * math.sin(1.5 * t)
        log()

    phase = "LAND"
    while z > 0.02:
        t += dt
        z = max(0.0, z - 0.4 * dt)
        x *= 0.96
        log()

    phase = "LANDED"
    x = z = 0.0
    for _ in range(20):
        t += dt
        log()
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = simulate()
    ts = [r[0] for r in rows]
    xs = [r[1] for r in rows]
    zs = [r[3] for r in rows]
    phases = [r[4] for r in rows]

    with (OUT / "uav_takeoff_hover_land.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "x", "y", "z", "phase"])
        w.writerows(rows)

    # ---- 静态总览：高度-时间 + 阶段色带 ----
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.35, 1]})
    ax, ax2 = axes
    colors = {
        "WAIT_CONNECT": "#6b7280",
        "CMD_CONTROL": "#8b5cf6",
        "ARM": "#f59e0b",
        "TAKEOFF": "#3b82f6",
        "HOVER": "#10b981",
        "LAND": "#ef4444",
        "LANDED": "#64748b",
    }
    for i in range(len(ts) - 1):
        ax.plot(ts[i : i + 2], zs[i : i + 2], color=colors.get(phases[i], "#3b82f6"), lw=2.8, solid_capstyle="round")
    ax.axhline(TAKEOFF_H, color="#94a3b8", ls="--", lw=1)
    ax.set_xlabel("time (s)", fontsize=11)
    ax.set_ylabel("altitude z (m)", fontsize=11)
    ax.set_title("Altitude by phase", fontsize=13, pad=10)
    ax.set_ylim(-0.05, TAKEOFF_H + 0.35)
    ax.grid(True, alpha=0.25)
    ax.text(ts[-1] * 0.02, TAKEOFF_H + 0.08, f"target {TAKEOFF_H} m", color="#64748b", fontsize=9)

    # 阶段图例（去重）
    seen = []
    for p in phases:
        if p not in seen:
            seen.append(p)
            ax.plot([], [], color=colors[p], lw=3, label=PHASE_CN[p])
    ax.legend(loc="lower right", fontsize=8, framealpha=0.92)

    # 右侧：最终侧视轨迹
    ax2.fill_between([-1.6, 1.6], -0.08, 0, color="#334155", alpha=0.9)
    ax2.plot(xs, zs, color="#60a5fa", lw=2.2)
    ax2.plot([xs[-1]], [zs[-1]], "o", color="#ef4444", ms=10)
    ax2.set_xlim(-1.5, 1.5)
    ax2.set_ylim(-0.15, TAKEOFF_H + 0.4)
    ax2.set_aspect("equal")
    ax2.set_xlabel("x (m)")
    ax2.set_ylabel("z (m)")
    ax2.set_title("Side view", fontsize=13)
    ax2.grid(True, alpha=0.25)
    fig.suptitle("UAV Demo · Takeoff → Hover → Land (Sunray-aligned)", fontsize=14, y=1.02)
    fig.tight_layout()
    static = OUT / "uav_takeoff_hover_land.png"
    fig.savefig(static, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---- GIF：双面板动画 ----
    fig2, (axa, axb) = plt.subplots(1, 2, figsize=(10, 4.8))
    fig2.patch.set_facecolor("#0b1220")
    for a in (axa, axb):
        a.set_facecolor("#111827")
        a.tick_params(colors="#cbd5e1")
        for spine in a.spines.values():
            spine.set_color("#334155")
        a.xaxis.label.set_color("#e2e8f0")
        a.yaxis.label.set_color("#e2e8f0")
        a.title.set_color("#f8fafc")

    axa.set_xlim(0, max(ts))
    axa.set_ylim(-0.05, TAKEOFF_H + 0.35)
    axa.set_xlabel("time (s)")
    axa.set_ylabel("altitude (m)")
    axa.set_title("Altitude vs time")
    axa.axhline(TAKEOFF_H, color="#64748b", ls="--", lw=1)
    axa.grid(True, alpha=0.2, color="#475569")
    (line_h,) = axa.plot([], [], color="#38bdf8", lw=2.5)
    (dot_h,) = axa.plot([], [], "o", color="#fbbf24", ms=8)

    axb.set_xlim(-1.5, 1.5)
    axb.set_ylim(-0.15, TAKEOFF_H + 0.4)
    axb.set_aspect("equal")
    axb.set_xlabel("x (m)")
    axb.set_ylabel("z (m)")
    axb.set_title("Side view")
    axb.add_patch(Rectangle((-1.6, -0.08), 3.2, 0.08, color="#1e293b"))
    axb.grid(True, alpha=0.2, color="#475569")
    (trail,) = axb.plot([], [], color="#38bdf8", lw=2)
    (drone,) = axb.plot([], [], marker="o", color="#f43f5e", ms=12)
    banner = fig2.text(0.5, 0.02, "", ha="center", color="#f8fafc", fontsize=14, fontweight="bold")
    fig2.suptitle("UAV · Takeoff / Hover / Land", color="#f8fafc", fontsize=13)

    n_frames = 90
    step = max(1, (len(rows) - 1) // (n_frames - 1))

    def update(i):
        idx = min(i * step, len(rows) - 1)
        line_h.set_data(ts[: idx + 1], zs[: idx + 1])
        dot_h.set_data([ts[idx]], [zs[idx]])
        trail.set_data(xs[: idx + 1], zs[: idx + 1])
        drone.set_data([xs[idx]], [zs[idx]])
        p = phases[idx]
        banner.set_text(f"{PHASE_CN.get(p, p)}  ·  t={ts[idx]:.1f}s  z={zs[idx]:.2f}m")
        banner.set_color(colors.get(p, "#f8fafc"))
        return line_h, dot_h, trail, drone, banner

    anim = FuncAnimation(fig2, update, frames=n_frames, interval=70, blit=False)
    gif = OUT / "uav_takeoff_hover_land.gif"
    anim.save(gif, writer=PillowWriter(fps=14), dpi=120)
    plt.close(fig2)

    print(f"[OK] {static}")
    print(f"[OK] {gif}")
    print("Phases:", " → ".join(PHASE_CN[p] for p in dict.fromkeys(phases)))


if __name__ == "__main__":
    main()
