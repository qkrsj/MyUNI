# -*- coding: utf-8 -*-
"""캐릭터 도트. 지금은 아트가 없어서 도형으로 찍는 임시 도트다.

학교 공식 마스코트가 아니라 **상징 동물 + 상징색**으로 만든 오리지널 캐릭터.
나중에 학교별 스프라이트 시트(schools.sprite_set)가 생기면 build_frames() 만 바꾸면 된다
- 돌려주는 모양(자세 x 방향별 PIL RGBA 목록)만 지키면 나머지 코드는 그대로다.

작은 칸(GRID)에 안티앨리어싱 없이 찍고 SCALE 배로 키운다. 그래서 가장자리가 반투명이
아니라 윈도우의 투명색 방식에서도 테두리가 안 남는다.
"""
from PIL import Image, ImageDraw, ImageOps

GRID_W, GRID_H = 26, 28
SCALE = 3
WIDTH, HEIGHT = GRID_W * SCALE, GRID_H * SCALE

# 진화 단계별 몸통 반지름 (칸 단위). 0 은 알.
BODY_R = {1: 5, 2: 7, 3: 9}

POSES = {"walk": 4, "stand": 2, "sleep": 2, "jump": 1}

BIRDS = ("eagle", "duck", "owl", "magpie", "crane", "bird")


def _rgb(hexcolor, default=(244, 196, 48)):
    h = (hexcolor or "").lstrip("#")
    if len(h) != 6:
        return default
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return default


def shade(rgb, amount):
    """amount < 0 이면 어둡게, > 0 이면 밝게."""
    if amount < 0:
        return tuple(int(c * (1 + amount)) for c in rgb)
    return tuple(int(c + (255 - c) * amount) for c in rgb)


def _dark(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] < 110


def _rgba(rgb, a=255):
    return rgb + (a,)


# ---------------------------------------------------------------- 그리기
def _draw_egg(d, frame, pose, prim, sec):
    cx, ground = GRID_W // 2, GRID_H - 1
    dx = 0 if pose == "sleep" else (0, -1, 0, 1)[frame % 4]
    lift = 3 if pose == "jump" else 0
    w, h = 8, 11
    box = [cx - w // 2 + dx, ground - h - lift, cx + w // 2 + dx, ground - lift]
    d.ellipse(box, fill=_rgba(sec), outline=_rgba(shade(prim, -0.2)))
    for sx, sy, r in ((-2, 3, 1), (2, 6, 1), (-1, 8, 0)):
        x, y = cx + sx + dx, box[1] + sy
        d.ellipse([x - r, y - r, x + r, y + r], fill=_rgba(prim))


def _draw_creature(d, frame, pose, stage, animal, prim, sec):
    r = BODY_R.get(stage, 5)
    cx, ground = GRID_W // 2, GRID_H - 1
    outline = _rgba(shade(prim, -0.45))
    legs = 2
    bob = {"walk": (0, 1, 0, 1), "sleep": (0, 1)}.get(pose, (0,))[frame % len(
        {"walk": (0, 1, 0, 1), "sleep": (0, 1)}.get(pose, (0,)))]
    lift = 3 if pose == "jump" else 0
    top = ground - legs - 2 * r - lift + bob
    cy = top + r

    # 다리: 걸을 때 번갈아 든다
    leg_x = (cx - max(1, r // 2), cx + max(1, r // 2) - 1)
    for i, lx in enumerate(leg_x):
        up = pose == "walk" and frame % 4 in ((1,) if i == 0 else (3,))
        d.line([lx, cy + r - 1, lx, ground - lift - (1 if up else 0)], fill=outline, width=1)

    # 머리 장식: 새는 볏, 나머지는 둥근 귀
    if animal in BIRDS:
        d.line([cx - 1, top - 2, cx, top], fill=_rgba(prim))
        d.line([cx + 1, top - 3, cx + 1, top], fill=_rgba(prim))
    else:
        er = max(1, r // 3)
        for ex in (cx - r + er, cx + r - er):
            d.ellipse([ex - er, top - er + 1, ex + er, top + er + 1], fill=_rgba(prim), outline=outline)

    # 몸통
    d.ellipse([cx - r, top, cx + r, top + 2 * r], fill=_rgba(prim), outline=outline)
    # 배
    br = max(2, int(r * 0.55))
    d.ellipse([cx - br + 1, cy, cx + br + 1, cy + int(r * 0.85)], fill=_rgba(sec))

    # 동물별 무늬
    if animal == "tiger" and r >= 7:
        for sx in (-r // 2, 0, r // 2):
            d.line([cx + sx, top + 1, cx + sx, top + max(2, r // 3)], fill=outline)
    if animal in BIRDS:
        wing = _rgba(shade(prim, -0.25))
        d.ellipse([cx - r + 1, cy - 1, cx - 1, cy + r // 2 + 1], fill=wing, outline=outline)

    # 눈 (오른쪽을 보고 있다)
    eye = (255, 255, 255, 255) if _dark(prim) else (30, 30, 30, 255)
    ey = cy - max(1, r // 3)
    blink = pose == "stand" and frame == 1
    for ex in (cx + max(1, r // 5), cx + max(3, int(r * 0.65))):
        if pose == "sleep" or blink:
            d.line([ex - 1, ey, ex, ey], fill=eye)
        elif r >= 7:
            d.rectangle([ex - 1, ey - 1, ex, ey], fill=eye)
        else:
            d.point((ex, ey), fill=eye)

    # 부리 / 코
    if animal in BIRDS:
        d.polygon([(cx + r - 1, cy - 1), (cx + r + 2, cy), (cx + r - 1, cy + 1)], fill=(245, 166, 35, 255))
    else:
        d.point((cx + r - 1, cy), fill=(40, 40, 40, 255))

    if pose == "sleep" and frame == 1:
        zx, zy = cx + r + 1, top - 2
        d.line([zx, zy, zx + 2, zy], fill=(80, 80, 120, 255))
        d.line([zx + 2, zy, zx, zy + 2], fill=(80, 80, 120, 255))
        d.line([zx, zy + 2, zx + 2, zy + 2], fill=(80, 80, 120, 255))


def draw(stage, animal, color_primary, color_secondary, pose="stand", frame=0):
    """도트 한 장 (오른쪽을 본다). 크기는 늘 WIDTH x HEIGHT."""
    prim, sec = _rgb(color_primary), _rgb(color_secondary, (255, 255, 255))
    im = Image.new("RGBA", (GRID_W, GRID_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if stage <= 0:
        _draw_egg(d, frame, pose, prim, sec)
    else:
        _draw_creature(d, frame, pose, stage, animal or "duck", prim, sec)
    return im.resize((WIDTH, HEIGHT), Image.NEAREST)


def build_frames(stage, animal, color_primary, color_secondary):
    """{(자세, 방향): [그림, ...]}. 방향은 1(오른쪽) / -1(왼쪽)."""
    out = {}
    for pose, n in POSES.items():
        right = [draw(stage, animal, color_primary, color_secondary, pose, i) for i in range(n)]
        out[(pose, 1)] = right
        out[(pose, -1)] = [ImageOps.mirror(im) for im in right]
    return out


def icon(size=64, color_primary="#F4C430", color_secondary="#FFFFFF"):
    """트레이 · 앱 아이콘. 아기 단계 캐릭터의 얼굴."""
    im = draw(1, "duck", color_primary, color_secondary, "stand", 0)
    bbox = im.getbbox() or (0, 0, im.width, im.height)
    im = im.crop(bbox)
    side = max(im.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return sq.resize((size, size), Image.NEAREST)
