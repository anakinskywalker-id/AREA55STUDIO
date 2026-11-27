"""
Generate demo equirectangular 360-degree PNG panoramas and an architectural SVG floorplan
using only Python's standard library so the 360 VR property tour works immediately out of the box.
"""

import math
import os
import struct
import zlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEMO_DIR = os.path.join(BASE_DIR, "assets", "demo")
os.makedirs(DEMO_DIR, exist_ok=True)


def write_png(filepath: str, width: int, height: int, rgb_bytes: bytes) -> None:
    """Write an RGB byte buffer to a valid PNG file."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack("!I", len(data))
            + tag
            + data
            + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw_rows = bytearray()
    stride = width * 3
    for y in range(height):
        raw_rows.append(0)  # filter type 0
        start = y * stride
        raw_rows.extend(rgb_bytes[start : start + stride])

    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw_rows), level=6)

    with open(filepath, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", idat))
        f.write(chunk(b"IEND", b""))


def clamp(v: float) -> int:
    return 0 if v < 0 else (255 if v > 255 else int(v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def generate_room_pano(
    filename: str,
    wall_color: tuple[int, int, int],
    floor_color: tuple[int, int, int],
    ceiling_color: tuple[int, int, int],
    accent_color: tuple[int, int, int],
    is_exterior: bool = False,
    width: int = 1024,
    height: int = 512,
) -> None:
    """Generate a synthetic equirectangular 360 panorama of a room or exterior."""
    buf = bytearray(width * height * 3)
    idx = 0

    for y in range(height):
        v = y / height
        phi = (0.5 - v) * math.pi  # +pi/2 (zenith) to -pi/2 (nadir)
        cos_phi = math.cos(phi)
        sin_phi = math.sin(phi)

        for x in range(width):
            u = x / width
            theta = (u - 0.5) * 2.0 * math.pi  # -pi to +pi
            dx = cos_phi * math.sin(theta)
            dy = sin_phi
            dz = cos_phi * math.cos(theta)

            if is_exterior:
                # Sky + horizon + modern house facade + garden lawn
                if dy > 0.02:
                    # Sky gradient
                    t = min(1.0, dy / 0.8)
                    r = lerp(180, 72, t)
                    g = lerp(220, 145, t)
                    b = lerp(245, 225, t)
                    # Sun glow
                    sun_dot = max(0.0, dx * 0.5 + dy * 0.6 + dz * 0.62)
                    if sun_dot > 0.96:
                        glow = (sun_dot - 0.96) / 0.04
                        r = lerp(r, 255, glow)
                        g = lerp(g, 248, glow)
                        b = lerp(b, 210, glow)
                elif dy < -0.02:
                    # Grass / paving stone perspective
                    dist = min(20.0, 1.6 / abs(dy))
                    gx = dx * dist
                    gz = dz * dist
                    if abs(gx) < 2.2 and gz > 0:
                        # Stone walkway
                        tile = ((int(math.floor(gx * 2)) + int(math.floor(gz * 2))) % 2) * 14
                        r, g, b = 175 + tile, 170 + tile, 162 + tile
                    else:
                        # Lawn stripes
                        stripe = (int(math.floor(gz * 1.5)) % 2) * 12
                        r, g, b = 78 + stripe, 138 + stripe, 72 + stripe
                else:
                    r, g, b = 155, 195, 175

                # House facade in front (+Z direction)
                if dz > 0.25 and abs(dx / max(0.01, dz)) < 1.15 and -0.35 < dy / max(0.01, dz) < 0.72:
                    wx = dx / dz
                    wy = dy / dz
                    # Main wall
                    r, g, b = wall_color
                    # Window / glass door
                    if (-0.65 < wx < -0.15 or 0.15 < wx < 0.65) and (-0.15 < wy < 0.45):
                        r, g, b = 120, 175, 210
                    # Roof overhang
                    if wy > 0.52:
                        r, g, b = accent_color
            else:
                # Indoor rectangular room ray-box intersection
                # Room dimensions: X in [-3, 3], Y in [-1.4, 1.8], Z in [-3.5, 3.5]
                tx = (3.0 / abs(dx)) if abs(dx) > 1e-5 else 1e9
                ty = ((1.8 if dy > 0 else 1.4) / abs(dy)) if abs(dy) > 1e-5 else 1e9
                tz = (3.5 / abs(dz)) if abs(dz) > 1e-5 else 1e9

                t = min(tx, ty, tz)
                hx, hy, hz = dx * t, dy * t, dz * t

                if t == ty:
                    if dy > 0:
                        # Ceiling with recessed warm light panel
                        if abs(hx) < 1.2 and abs(hz) < 1.2:
                            r, g, b = 250, 244, 228
                        else:
                            r, g, b = ceiling_color
                    else:
                        # Floor with subtle wood/tile grid
                        grid = 14 if (int(math.floor(hx * 2)) + int(math.floor(hz * 2))) % 2 == 0 else 0
                        r = floor_color[0] + grid
                        g = floor_color[1] + grid
                        b = floor_color[2] + grid
                else:
                    # Walls with subtle shading by orientation
                    shade = 0.92 if t == tx else 1.0
                    r = wall_color[0] * shade
                    g = wall_color[1] * shade
                    b = wall_color[2] * shade

                    # Baseboard
                    if hy < -1.25:
                        r, g, b = accent_color

                    # Window on +Z wall
                    if t == tz and dz > 0 and abs(hx) < 1.3 and -0.4 < hy < 1.1:
                        if abs(hx) > 1.2 or hy < -0.32 or hy > 1.02 or abs(hx) < 0.05:
                            r, g, b = accent_color  # Window frame
                        else:
                            # Bright daylight view
                            sky_t = max(0.0, min(1.0, (hy + 0.4) / 1.5))
                            r = lerp(185, 130, sky_t)
                            g = lerp(225, 190, sky_t)
                            b = lerp(245, 240, sky_t)

                    # Accent art frame on -X wall
                    if t == tx and dx < 0 and abs(hz) < 0.8 and -0.1 < hy < 0.9:
                        if abs(hz) > 0.72 or hy < -0.02 or hy > 0.82:
                            r, g, b = accent_color
                        else:
                            r = lerp(accent_color[0], 235, 0.45)
                            g = lerp(accent_color[1], 210, 0.45)
                            b = lerp(accent_color[2], 180, 0.45)

            buf[idx] = clamp(r)
            buf[idx + 1] = clamp(g)
            buf[idx + 2] = clamp(b)
            idx += 3

    out_path = os.path.join(DEMO_DIR, filename)
    write_png(out_path, width, height, bytes(buf))
    print(f"Generated {out_path}")


def generate_floorplan_svg(filename: str) -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 560" width="800" height="560">
  <rect width="800" height="560" fill="#f8fafc"/>
  <!-- Garden / Exterior Area -->
  <rect x="40" y="390" width="720" height="140" rx="8" fill="#dcfce7" stroke="#86efac" stroke-width="2"/>
  <text x="400" y="475" text-anchor="middle" font-family="sans-serif" font-size="16" font-weight="600" fill="#166534">TAMAN &amp; FASAD DEPAN (EXTERIOR)</text>

  <!-- House Footprint -->
  <rect x="80" y="50" width="640" height="340" fill="#ffffff" stroke="#1e293b" stroke-width="6"/>

  <!-- Living Room (Left-Bottom) -->
  <rect x="80" y="190" width="280" height="200" fill="#fef3c7" stroke="#334155" stroke-width="3"/>
  <text x="220" y="295" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="700" fill="#92400e">RUANG TAMU</text>

  <!-- Master Bedroom (Left-Top) -->
  <rect x="80" y="50" width="280" height="140" fill="#e0e7ff" stroke="#334155" stroke-width="3"/>
  <text x="220" y="125" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="700" fill="#3730a3">MASTER BEDROOM</text>

  <!-- Kitchen & Dining (Right-Bottom) -->
  <rect x="360" y="190" width="360" height="200" fill="#ffedd5" stroke="#334155" stroke-width="3"/>
  <text x="540" y="295" text-anchor="middle" font-family="sans-serif" font-size="15" font-weight="700" fill="#9a3412">DAPUR &amp; RUANG MAKAN</text>

  <!-- Kids Bedroom / Study (Right-Top) -->
  <rect x="360" y="50" width="220" height="140" fill="#f3e8ff" stroke="#334155" stroke-width="3"/>
  <text x="470" y="125" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="700" fill="#6b21a8">KAMAR ANAK</text>

  <!-- Bathroom (Top-Right) -->
  <rect x="580" y="50" width="140" height="140" fill="#cffafe" stroke="#334155" stroke-width="3"/>
  <text x="650" y="125" text-anchor="middle" font-family="sans-serif" font-size="13" font-weight="700" fill="#155e75">KAMAR MANDI</text>

  <!-- Doors -->
  <line x1="190" y1="390" x2="250" y2="390" stroke="#f8fafc" stroke-width="8"/>
  <line x1="210" y1="190" x2="250" y2="190" stroke="#fef3c7" stroke-width="6"/>
  <line x1="360" y1="260" x2="360" y2="310" stroke="#ffedd5" stroke-width="6"/>
  <line x1="450" y1="190" x2="495" y2="190" stroke="#ffedd5" stroke-width="6"/>
</svg>"""
    out_path = os.path.join(DEMO_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated {out_path}")


if __name__ == "__main__":
    generate_room_pano(
        "exterior-fasad.png",
        wall_color=(242, 238, 230),
        floor_color=(120, 160, 100),
        ceiling_color=(135, 195, 240),
        accent_color=(75, 65, 58),
        is_exterior=True,
    )
    generate_room_pano(
        "living-room.png",
        wall_color=(245, 240, 232),
        floor_color=(188, 152, 114),
        ceiling_color=(250, 250, 248),
        accent_color=(120, 88, 60),
    )
    generate_room_pano(
        "bedroom.png",
        wall_color=(226, 232, 244),
        floor_color=(165, 132, 102),
        ceiling_color=(246, 248, 252),
        accent_color=(72, 85, 125),
    )
    generate_room_pano(
        "kitchen.png",
        wall_color=(244, 236, 224),
        floor_color=(210, 206, 198),
        ceiling_color=(252, 252, 250),
        accent_color=(168, 92, 52),
    )
    generate_floorplan_svg("denah-anggrek.svg")
