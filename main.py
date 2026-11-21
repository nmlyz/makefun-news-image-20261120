#!/usr/bin/env python3
"""Draw a one-image newspaper front page summing up the world news of
20 November 2026, and write it to /output/entry.png.

Standard library only, no network, fully deterministic: the same bytes
come out of every run. All text is drawn with a hand-made 5x7 bitmap
font; all pictures are drawn with code.
"""

import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (247, 243, 232)
INK = (20, 22, 26)
RED = (179, 32, 42)
BLUE = (29, 78, 137)
DARKBLUE = (16, 42, 84)
YELLOW = (240, 192, 32)
GRAY = (110, 110, 110)
LIGHT = (226, 219, 198)
WHITE = (255, 255, 255)
SKY = (188, 214, 235)
SEA = (64, 120, 178)
SAND = (214, 188, 140)
GREEN = (46, 125, 50)
ORANGE = (232, 119, 34)
BROWN = (120, 84, 50)

# ---------------------------------------------------------------- font
# Each glyph is 7 rows of 5 pixels, '#' is ink.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": (".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
}


def text_width(s, scale):
    if not s:
        return 0
    return len(s) * 6 * scale - scale


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def frame(self, x, y, w, h, c, t=3):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=3):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = t // 2
        while True:
            self.rect(x0 - r, y0 - r, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def polyline(self, pts, c, t=3):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, t)

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if fill:
                    if d2 <= r * r:
                        self.set(xx, yy, c)
                else:
                    if r * r - 2 * r <= d2 <= r * r + 2 * r:
                        self.set(xx, yy, c)

    def polygon(self, pts, c):
        ys = [p[1] for p in pts]
        for yy in range(min(ys), max(ys) + 1):
            nodes = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    nodes.append(x0 + (yy - y0) * (x1 - x0) // (y1 - y0))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                self.rect(nodes[i], yy, nodes[i + 1] - nodes[i] + 1, 1, c)

    def text(self, x, y, s, scale, c):
        cx = x
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[" "])
            for ry in range(7):
                row = glyph[ry]
                for rx in range(5):
                    if row[rx] == "#":
                        self.rect(cx + rx * scale, y + ry * scale, scale, scale, c)
            cx += 6 * scale
        return cx

    def text_centered(self, cx, y, s, scale, c):
        return self.text(cx - text_width(s, scale) // 2, y, s, scale, c)

    def text_wrapped(self, x, y, s, scale, c, max_w, line_gap=4):
        words = s.upper().split()
        lines = []
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_width(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        for i, ln in enumerate(lines):
            self.text(x, y + i * (7 * scale + line_gap), ln, scale, c)
        return len(lines)


# ---------------------------------------------------------------- png
def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for yy in range(canvas.h):
        raw.append(0)
        raw += canvas.px[yy * stride:(yy + 1) * stride]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    os.chmod(path, 0o644)


# ---------------------------------------------------------------- pictures
def pic_missile(cv, x, y, w, h):
    """A cruise missile flying down-left into a burst, over a skyline."""
    cv.rect(x, y, w, h, SKY)
    # distant skyline
    base = y + h - 46
    for bx, bw, bh in ((6, 34, 52), (48, 26, 78), (82, 40, 60), (196, 30, 84),
                       (234, 44, 58), (w - 52, 30, 70)):
        cv.rect(x + bx, base - bh, bw, bh, (120, 138, 158))
    cv.rect(x, base, w, 4, INK)
    cv.rect(x, base + 4, w, h - (base - y) - 4, SAND)
    # bridge arc over a river gap
    cv.line(x + 120, base, x + 160, base - 26, INK, 5)
    cv.line(x + 160, base - 26, x + 200, base, INK, 5)
    # explosion burst where the missile lands
    ex, ey = x + 108, base - 6
    for dx, dy in ((0, -34), (24, -24), (34, 0), (24, 22), (0, 30), (-22, 22),
                   (-32, 0), (-22, -24), (12, -32), (-12, -32)):
        cv.line(ex, ey, ex + dx, ey + dy, ORANGE, 6)
    cv.circle(ex, ey, 15, RED)
    cv.circle(ex, ey, 8, YELLOW)
    # missile body, nose down-left, tail up-right with flame
    nose = (x + 138, base - 44)
    tail = (x + 218, base - 118)
    cv.line(tail[0], tail[1], nose[0], nose[1], (90, 96, 104), 17)
    cv.polygon([nose, (nose[0] + 16, nose[1] - 4), (nose[0] + 4, nose[1] + 14)], RED)
    cv.polygon([(tail[0] - 2, tail[1] + 2), (tail[0] + 20, tail[1] + 8),
                (tail[0] + 6, tail[1] - 12)], INK)
    cv.polygon([(tail[0] - 4, tail[1] - 4), (tail[0] - 14, tail[1] + 16),
                (tail[0] + 14, tail[1] + 12)], INK)
    # flame trail
    cv.line(tail[0] + 8, tail[1] - 8, tail[0] + 44, tail[1] - 40, ORANGE, 9)
    cv.line(tail[0] + 8, tail[1] - 8, tail[0] + 62, tail[1] - 54, YELLOW, 5)
    # smoke puffs along the path
    for sx, sy, sr in ((196, 58, 10), (222, 36, 13), (250, 16, 9)):
        cv.circle(x + sx, y + sy, sr, (200, 204, 208))


def pic_chart(cv, x, y, w, h):
    """A stock chart plunging into the red."""
    cv.rect(x, y, w, h, WHITE)
    for gy in range(14, h - 8, 22):
        cv.line(x + 8, y + gy, x + w - 8, y + gy, LIGHT, 2)
    pts = [(x + int(w * f), y + int(h * g)) for f, g in
           ((0.03, 0.28), (0.15, 0.20), (0.27, 0.38), (0.39, 0.32),
            (0.51, 0.55), (0.63, 0.47), (0.77, 0.74), (0.93, 0.88))]
    cv.polyline(pts, RED, 6)
    # big down arrow at the end of the line
    ex, ey = pts[-1]
    cv.polygon([(ex - 20, ey - 16), (ex + 2, ey - 20), (ex - 2, ey + 8)], RED)
    for px, py in pts:
        cv.circle(px, py, 5, INK)


def pic_quake(cv, x, y, w, h):
    """Andes peaks, a cracked ground line and shaking marks."""
    cv.rect(x, y, w, h, SKY)
    cv.rect(x, y + 62, w, h - 62, SAND)
    x = x + (w - 250) // 2  # centre the 250-wide drawing in the band
    # mountains
    cv.polygon([(x, y + 62), (x + 62, y + 14), (x + 124, y + 62)], (105, 116, 128))
    cv.polygon([(x + 88, y + 62), (x + 168, y + 4), (x + 248, y + 62)], (84, 96, 110))
    cv.polygon([(x + 150, y + 24), (x + 168, y + 4), (x + 188, y + 24),
                (x + 178, y + 32), (x + 168, y + 25), (x + 158, y + 32)], WHITE)
    ground = y + 62
    # crack zigzag in the ground
    crack = [(x + 20, ground + 5), (x + 58, ground + 17), (x + 84, ground + 8),
             (x + 118, ground + 21), (x + 150, ground + 10), (x + 186, ground + 19),
             (x + 224, ground + 9)]
    cv.polyline(crack, INK, 5)
    # shaking marks beside the peaks
    for sx in (x + 30, x + 214):
        cv.line(sx, y + 30, sx - 10, y + 44, INK, 4)
        cv.line(sx + 14, y + 26, sx + 6, y + 44, INK, 4)


def pic_flags(cv, x, y, w, h):
    """UK and EU flags on poles, joined by a bridge over water."""
    cv.rect(x, y, w, h, SKY)
    # poles
    cv.rect(x + 34, y + 8, 6, 82, INK)
    cv.rect(x + w - 40, y + 8, 6, 82, INK)
    # UK flag (simplified): blue field, white cross, red cross
    fx, fy, fw, fh = x + 40, y + 8, 92, 52
    cv.rect(fx, fy, fw, fh, DARKBLUE)
    cv.rect(fx, fy + fh // 2 - 7, fw, 14, WHITE)
    cv.rect(fx + fw // 2 - 7, fy, 14, fh, WHITE)
    cv.rect(fx, fy + fh // 2 - 4, fw, 8, RED)
    cv.rect(fx + fw // 2 - 4, fy, 8, fh, RED)
    cv.frame(fx, fy, fw, fh, INK, 2)
    # EU flag: blue field, ring of yellow stars
    ex, ey = x + w - 132, y + 8
    cv.rect(ex, ey, fw, fh, BLUE)
    ccx, ccy = ex + fw // 2, ey + fh // 2
    import math
    for i in range(8):
        ang = i * math.pi / 4
        sx = int(ccx + 17 * math.cos(ang))
        sy = int(ccy + 17 * math.sin(ang))
        cv.rect(sx - 3, sy - 3, 7, 7, YELLOW)
    cv.rect(ccx - 3, ccy - 3, 7, 7, YELLOW)
    cv.frame(ex, ey, fw, fh, INK, 2)
    # bridge arc joining the poles
    pts = []
    for i in range(21):
        t = i / 20.0
        bx = int(x + 40 + t * (w - 80))
        by = int(y + 90 - 20 * (1 - (2 * t - 1) ** 2))
        pts.append((bx, by))
    cv.polyline(pts, INK, 4)
    cv.rect(x, y + 90, w, h - 90, SEA)
    for wx in range(10, w - 10, 46):
        cv.line(x + wx, y + 99, x + wx + 22, y + 99, WHITE, 3)


def pic_tanker(cv, x, y, w, h):
    """An oil tanker on the sea, a flame over its deck, a city tower behind."""
    cv.rect(x, y, w, h, (246, 214, 170))
    sea_y = y + h - 24
    # tower silhouette (Riyadh skyline) on the right
    cv.rect(x + w - 66, y + 6, 30, sea_y - y - 6, (150, 120, 96))
    cv.polygon([(x + w - 66, y + 6), (x + w - 36, y + 6), (x + w - 51, y - 2)],
               (150, 120, 96))
    for wy in range(y + 16, sea_y - 12, 13):
        cv.rect(x + w - 58, wy, 14, 6, YELLOW)
    cv.rect(x + w - 104, y + 34, 22, sea_y - y - 34, (168, 138, 112))
    # sea
    cv.rect(x, sea_y, w, h - (sea_y - y), SEA)
    for wx in range(8, w - 8, 52):
        cv.line(x + wx, sea_y + 10, x + wx + 24, sea_y + 10, WHITE, 3)
    # tanker hull and deck
    hx, hy = x + 18, sea_y - 14
    cv.polygon([(hx, hy), (hx + 190, hy), (hx + 176, hy + 16), (hx + 16, hy + 16)], INK)
    cv.rect(hx + 10, hy - 10, 168, 10, RED)
    cv.rect(hx + 138, hy - 30, 26, 20, WHITE)
    cv.frame(hx + 138, hy - 30, 26, 20, INK, 2)
    cv.rect(hx + 30, hy - 20, 8, 10, INK)
    # flame and smoke over the deck
    fx, fy = hx + 74, hy - 12
    cv.polygon([(fx - 13, fy), (fx + 13, fy), (fx + 5, fy - 18), (fx, fy - 30),
                (fx - 6, fy - 18)], ORANGE)
    cv.polygon([(fx - 6, fy), (fx + 6, fy), (fx + 2, fy - 14), (fx - 2, fy - 21)], YELLOW)
    cv.circle(fx + 16, fy - 38, 9, (198, 190, 178))
    cv.circle(fx + 34, fy - 46, 12, (210, 202, 190))


# ---------------------------------------------------------------- page
def panel(cv, x, y, w, h):
    cv.rect(x, y, w, h, WHITE)
    cv.frame(x, y, w, h, INK, 3)


def build():
    cv = Canvas(W, H, PAPER)

    # masthead
    cv.text_centered(W // 2, 18, "FRIDAY - THE WORLD IN ONE PICTURE", 3, INK)
    cv.rect(24, 56, W - 48, 5, INK)
    cv.text_centered(W // 2, 72, "20 NOVEMBER 2026", 9, RED)
    cv.rect(24, 148, W - 48, 3, INK)
    cv.rect(24, 155, W - 48, 8, INK)

    # ---- top story: Russian missiles in Poland
    ax, ay, aw, ah = 24, 178, W - 48, 296
    panel(cv, ax, ay, aw, ah)
    pic_missile(cv, ax + 14, ay + 14, 300, ah - 28)
    tx = ax + 330
    cv.text(tx, ay + 22, "RUSSIAN MISSILES", 6, INK)
    cv.text(tx, ay + 72, "LAND IN POLAND", 6, RED)
    cv.rect(tx, ay + 122, aw - 344, 3, INK)
    cv.text(tx, ay + 138, "400+ DRONES, 110 MISSILES", 3, INK)
    cv.text(tx, ay + 166, "RAINED ON UKRAINE OVERNIGHT", 3, INK)
    cv.text(tx, ay + 202, "KYIV BRIDGES + EMBASSIES HIT", 3, INK)
    cv.text(tx, ay + 230, "8 KILLED - NATO: GRAVE VIOLATION", 3, INK)

    # ---- row of two: markets, quake
    by = 488
    bh = 248
    bw = (W - 48 - 16) // 2
    panel(cv, 24, by, bw, bh)
    pic_chart(cv, 38, by + 8, bw - 28, 108)
    cv.text(38, by + 126, "AI SELL-OFF", 5, INK)
    cv.text(38, by + 164, "IN CORRECTION", 5, RED)
    cv.rect(38, by + 204, bw - 28, 3, INK)
    cv.text(38, by + 214, "S&P 500 -3.7 - NIKKEI -5.1", 3, INK)

    qx = 24 + bw + 16
    panel(cv, qx, by, bw, bh)
    pic_quake(cv, qx + 14, by + 8, bw - 28, 108)
    cv.text(qx + 14, by + 126, "PERU QUAKE", 5, INK)
    cv.text(qx + 14, by + 164, "MAGNITUDE 6.7", 5, RED)
    cv.rect(qx + 14, by + 204, bw - 28, 3, INK)
    cv.text(qx + 14, by + 214, "FELT IN LIMA - NO DEATHS", 3, INK)

    # ---- row of two: EU-UK deal, Riyadh / Hormuz
    cy = 750
    panel(cv, 24, cy, bw, bh)
    pic_flags(cv, 38, cy + 8, bw - 28, 108)
    cv.text(38, cy + 126, "UK-EU RESET", 5, INK)
    cv.text(38, cy + 164, "DEAL IN BRUSSELS", 5, RED)
    cv.rect(38, cy + 204, bw - 28, 3, INK)
    cv.text(38, cy + 214, "FOOD, CARBON, YOUTH DEALS", 3, INK)

    panel(cv, qx, cy, bw, bh)
    pic_tanker(cv, qx + 14, cy + 8, bw - 28, 108)
    cv.text(qx + 14, cy + 126, "HOUTHI MISSILES", 5, INK)
    cv.text(qx + 14, cy + 164, "HIT RIYADH", 5, RED)
    cv.rect(qx + 14, cy + 204, bw - 28, 3, INK)
    cv.text(qx + 14, cy + 214, "TANKERS BURN IN HORMUZ", 3, INK)

    # footer
    cv.text_centered(W // 2, 1004, "AS REPORTED ON THE DAY - REUTERS - AP - XINHUA", 2, GRAY)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(outdir, exist_ok=True)
    try:
        os.umask(0o022)
    except OSError:
        pass
    write_png(build(), os.path.join(outdir, "entry.png"))


if __name__ == "__main__":
    main()
