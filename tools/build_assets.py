#!/usr/bin/env python3
"""Build ALL Kenney-based assets for IBONARIUM KYIV.
Outputs into download/ibonarium-kyiv/assets/:
  bld_<cat>_<i>[_dmg].png  - buildings (full canvas, engine-anchored)
  road_<mask>.png (16) + road_wide.png - road tiles with markings
  prop_<name>.png - Kenney props
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(__file__))
import kenney_render as K
K.SRC = '/home/z/my-project/scripts/kenney_src/extracted'   # джерело Kenney kits
from PIL import Image, ImageDraw

OUT = K.OUT
OUT2 = '/home/z/my-project/public/game/assets'
COM, SUB, IND, RDS = 'commercial', 'city-kit-suburban', 'city-kit-industrial', 'city-kit-roads'
os.makedirs(OUT, exist_ok=True)
os.makedirs(OUT2, exist_ok=True)

# ------------------------------------------------------------------ buildings
# cat: (wT, dT, hpx, [(kit, model), ...]) — МАСШТАБ ЗА РЕФЕРЕНСОМ ZOMBIE CITY HD ISOMETRIC (БАТЧ 8):
# герой ~30px. ФУТПРИНТИ ТА ВИСОТИ ЗБІЛЬШЕНО ЩЕ РАЗ: хрущовки 3x2 (стіна ~104px = 3.5x героя),
# панельки-дев'ятки 3x3 (башти ~250px), адмінки 4x2/4x3, історичні 3x2, дачі 3x2.
# Футпринти синхронні з world.js CATS! Рендер ТЕКСТУРНИЙ ×2 суперсемпл (render_tex):
# справжні вікна/рамки/двері/цегла з colormap Kenney на кожному пікселі.
CATS = {
  'khrus':      (3, 2, 88, [(COM,'building-a'),(COM,'building-b'),(COM,'building-d'),(COM,'building-f'),(COM,'building-g'),(COM,'building-h')]),
  'khrus2':     (3, 2, 90, [(COM,'building-i'),(COM,'building-l'),(COM,'building-m'),(COM,'building-c')]),
  'panel9':     (3, 3, 210, [(COM,'building-skyscraper-b'),(COM,'building-skyscraper-c'),(COM,'building-skyscraper-d'),(COM,'building-skyscraper-e')]),
  'panel9b':    (3, 3, 210, [(COM,'building-skyscraper-a'),(COM,'building-skyscraper-b'),(COM,'building-skyscraper-d')]),
  'hist2':      (3, 2, 72, [(SUB,'building-type-a'),(SUB,'building-type-c'),(SUB,'building-type-e'),(SUB,'building-type-h'),(SUB,'building-type-i'),(SUB,'building-type-r')]),
  'hist2b':     (3, 2, 74, [(SUB,'building-type-g'),(SUB,'building-type-l'),(SUB,'building-type-p'),(SUB,'building-type-q')]),
  'hist2c':     (3, 2, 76, [(SUB,'building-type-k'),(SUB,'building-type-t'),(SUB,'building-type-f'),(SUB,'building-type-s')]),
  'hist3':      (4, 2, 82, [(SUB,'building-type-b'),(SUB,'building-type-d'),(SUB,'building-type-j'),(SUB,'building-type-o')]),
  'admin3':     (4, 2, 126, [(COM,'building-j'),(COM,'building-n'),(IND,'building-l')]),
  'admin4':     (4, 3, 190, [(COM,'building-skyscraper-a'),(COM,'building-m'),(COM,'building-n')]),
  'shop1':      (3, 1, 64, [(SUB,'building-type-p'),(SUB,'building-type-q'),(IND,'building-i')]),
  'shop2':      (3, 1, 66, [(IND,'building-h'),(IND,'building-j'),(SUB,'building-type-i'),(COM,'low-detail-building-d')]),
  'factory':    (4, 3, 92, [(IND,'building-a'),(IND,'building-b'),(IND,'building-c'),(IND,'building-g')]),
  'factory2':   (4, 3, 112, [(IND,'building-f'),(IND,'building-n'),(IND,'building-r'),(IND,'building-t')]),
  'garage':     (1, 1, 44, [(IND,'building-j'),(IND,'building-h'),(IND,'building-k'),(SUB,'building-type-p')]),
  'khrus_dmg':  (3, 2, 86, [(COM,'building-a'),(COM,'building-b'),(COM,'building-d'),(COM,'building-g')]),
  'panel9_dmg': (3, 3, 196, [(COM,'building-skyscraper-b'),(COM,'building-skyscraper-c'),(COM,'building-skyscraper-d')]),
  'hist_ruin':  (2, 1, 48, [(SUB,'building-type-c'),(SUB,'building-type-g'),(SUB,'building-type-h')]),
  # ІРПІНЬ — дачний масив: великі дачі 3x2, всі ВИЩІ за героя (передня стінка 90-102px)
  'dacha1':     (3, 2, 80, [(SUB,'building-type-n'),(SUB,'building-type-u')]),
  'dacha2':     (3, 2, 74, [(SUB,'building-type-m'),(SUB,'building-type-q')]),
  'dacha3':     (3, 2, 86, [(SUB,'building-type-o')]),
}

SS = 2          # суперсемплінг: рендер ×2, LANCZOS-даунскейл — вдвічі більше деталей

def render_cat_model(kit, name, wT, dT, hpx):
    mdl = K.load_obj(K.obj_path(kit, name))
    tex = K.load_tex(kit)
    x0, x1, y0, y1, z0, z1 = K.bbox(mdl)
    W = (wT + dT) * 16 + 4
    H = (wT + dT) * 8 + hpx + 8
    su = wT / max(1e-6, x1 - x0)
    sv = dT / max(1e-6, z1 - z0)
    # вертикальний роястяг: повна висота категорії, анізотропія обмежена 2.0
    sy = min(hpx / max(1e-6, (y1 - y0) * 16), (su + sv) / 2 * 2.0)
    dTl = dT
    def proj(x, y, z):
        u = (x - x0) * su
        v = (z - z0) * sv
        # engine cat convention: roof rhombus at canvas top, walls extend DOWN by hpx
        return ((2 + dTl * 16) + (u - v) * 16, 8 + hpx + (u + v) * 8 - (y - y0) * 16 * sy, u + v + (y - y0) * sy)
    r, nfaces = K.render_tex(mdl, tex, W, H, proj, SS=SS)
    return r

def damage_post(img, heavy=False, graffiti=False):
    """ПОСТАПОКАЛІПТИЧНИЙ ПРОПУСК (детальний): вигорілі пилові кольори, бруд,
    розбиті вікна, іржаві патьоки, СМУГИ БРУДУ під вікнами, ГРАФІТІ, дахові пропси
    (кондеї/вентиляції/вежі), силуетний контур, м'яка тінь-АО основи."""
    import numpy as np
    arr = np.array(img, dtype=np.float32)
    if arr.shape[2] == 4:
        alpha = arr[:, :, 3:4] / 255.0
    else:
        alpha = np.ones(arr.shape[:2] + (1,), dtype=np.float32)
        arr = np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255, dtype=np.float32)], axis=2)
    rgb = arr[:, :, :3]
    # 1) десатурація + теплий пиловий тинт (важче для руїн)
    m = 0.30 if heavy else 0.22
    gray = rgb[:, :, 0] * 0.30 + rgb[:, :, 1] * 0.59 + rgb[:, :, 2] * 0.11
    gray = gray[:, :, None]
    mixed = rgb * (1 - m) + gray * m
    mixed[:, :, 0] = np.clip(mixed[:, :, 0] + 7, 0, 255)   # теплий пил
    mixed[:, :, 1] = np.clip(mixed[:, :, 1] + 3, 0, 255)
    mixed[:, :, 2] = np.clip(mixed[:, :, 2] - 5, 0, 255)   # забираємо "чисту" синяву
    mixed *= (0.88 if heavy else 0.94)                      # трохи темніше
    arr[:, :, :3] = mixed
    img = Image.fromarray(np.clip(arr, 0, 255).astype('uint8'), 'RGBA').copy()  # writable buffer
    px = img.load()
    w, h = img.size
    dr = ImageDraw.Draw(img)
    # 2) брудні патьоки зверху вниз (водостоки, сажа) — довші та виразніші
    n = 22 if heavy else 15
    for i in range(n):
        x = int(K.IB_hsh(i, 21, 13) * w)
        ln = 8 + int(K.IB_hsh(i, 23, 17) * (20 if heavy else 13))
        c = (18, 16, 14) if i % 3 else (96, 62, 38)     # сажа / іржа
        y0 = int(K.IB_hsh(i, 27, 19) * max(1, h - ln - 2)) + 1
        for y in range(y0, min(h - 1, y0 + ln)):
            if y >= h: break
            if px[min(w - 1, x), y][3] > 0 and (y - y0) % 2 == 0:
                dr.point((x, y), fill=c)
                if (y - y0) % 4 == 0 and x + 1 < w and px[min(w - 1, x + 1), y][3] > 0:
                    dr.point((x + 1, y), fill=c)     # потовщення — видимість на дрібному маштабі
    # 3) розбиті та забиті вікна (темні діри / фанера)
    holes = 11 if heavy else 6
    for i in range(holes):
        x = int(K.IB_hsh(i, 33, 23) * max(1, w - 5)) + 2
        y = int(K.IB_hsh(i, 35, 29) * max(1, h - 12)) + 4
        if y > h * 0.75: continue
        if px[x, y][3] == 0 or px[x, y + 3][3] == 0: continue
        if i % 3 == 2:  # забито дошками
            dr.rectangle([x - 1, y, x + 3, y + 3], fill=(104, 78, 46))
            dr.rectangle([x - 1, y, x + 3, y], fill=(124, 94, 56))
            dr.point((x + 1, y + 1), fill=(84, 62, 36))
        else:           # вибите вікно — діра з рванім краєм
            dr.rectangle([x, y, x + 2, y + 3], fill=(12, 12, 15))
            dr.rectangle([x - 1, y - 1, x - 1, y + 3], fill=(30, 30, 36))
            dr.point((x + 3, y + 1), fill=(30, 30, 36))
    # 4) СМУГИ БРУДУ ПІД ВІКНАМИ + ІРЖАВИ ПЯТНА (блотчи)
    for i in range(5):
        bx = int(K.IB_hsh(i, 51, 57) * max(1, w - 8)) + 3
        by = int(K.IB_hsh(i, 53, 59) * max(1, h - 20)) + 8
        if px[min(w-1, bx), min(h-1, by)][3] == 0: continue
        rw = 3 + int(K.IB_hsh(i, 55, 61) * 4)
        rh = 2 + int(K.IB_hsh(i, 57, 63) * 3)
        c = (74, 46, 30) if i % 2 else (40, 36, 30)
        dr.rectangle([bx, by, bx + rw, by + rh], fill=c)
    # 5) сміття й обладнання на дахах: кондеї з вентиляторами, виходи, вежі
    bb = img.getbbox()
    if bb:
        bx0, by0, bx1, by1 = bb
        if not heavy:
            roof_y0, roof_y1 = by0, min(by0 + (by1 - by0) // 3, by1)
            for i in range(4):
                bx = int(K.IB_hsh(i, 41, 31) * max(1, bx1 - bx0 - 10)) + bx0 + 4
                by = int(K.IB_hsh(i, 43, 37) * max(1, roof_y1 - roof_y0 - 6)) + roof_y0 + 2
                ok_spot = all(px[min(w-1, max(0, bx + dx)), min(h-1, max(0, by + dy))][3] > 0
                              for dx in (-1, 0, 5) for dy in (-1, 0, 4))
                if not ok_spot: continue
                if i % 3 == 0:
                    # кондея з вентилятором (решітка)
                    dr.rectangle([bx, by, bx + 5, by + 3], fill=(52, 54, 62))
                    dr.rectangle([bx, by, bx + 5, by], fill=(70, 72, 82))
                    dr.rectangle([bx + 1, by + 1, bx + 4, by + 2], fill=(30, 32, 38))
                    dr.point((bx + 2, by + 1), fill=(96, 100, 110))
                elif i % 3 == 1:
                    # вентиляційна труба
                    dr.rectangle([bx, by - 3, bx + 2, by + 2], fill=(58, 60, 68))
                    dr.rectangle([bx - 1, by - 4, bx + 3, by - 3], fill=(74, 76, 84))
                else:
                    # вихід на дах
                    dr.rectangle([bx, by, bx + 4, by + 3], fill=(60, 56, 52))
                    dr.rectangle([bx, by, bx + 4, by], fill=(80, 74, 68))
            # антена на високих дахах
            if K.IB_hsh(7, 45, 71) < 0.5:
                ax2 = bx0 + (bx1 - bx0) // 2
                for ay2 in range(max(0, by0 - 7), by0 + 1):
                    if px[min(w-1, ax2), ay2][3] == 0: continue
                    dr.point((ax2, ay2), fill=(120, 124, 134))
                dr.point((ax2, max(0, by0 - 8)), fill=(190, 60, 50))   # маячок
        # 6) м'яка тінь-АО основи (градієнт замість різкого закопчення)
        for gy2 in range(max(0, by1 - 4), by1):
            k = (by1 - gy2) / 4.0
            for x in range(bx0, bx1):
                if px[x, gy2][3] > 0 and K.IB_hsh(x, gy2, 47) < 0.55 + 0.45 * (1 - k):
                    r0, g0, b0_, a0 = px[x, gy2]
                    f = 0.86 + 0.14 * k
                    px[x, gy2] = (int(r0 * f), int(g0 * f), int(b0_ * (f + 0.02)), a0)
    # 7) ГРАФІТІ — кольорові теги на стінах (30% будівель, 2-3 фарби)
    if graffiti and bb:
        gx0 = max(2, int(K.IB_hsh(3, 63, 81) * (w * 0.45)))
        gy0 = max(by0 + 4 if bb else 4, int(K.IB_hsh(5, 65, 83) * max(1, h * 0.45)))
        cols = [(38, 166, 154), (211, 70, 60), (244, 180, 40), (120, 90, 200)]
        c1 = cols[int(K.IB_hsh(1, 67, 85) * 4) % 4]
        c2 = cols[int(K.IB_hsh(2, 69, 87) * 4) % 4]
        # хвилясте пятно-тег
        tx, ty = gx0, gy0
        for s2 in range(9):
            if ty + 1 >= h: break
            if px[min(w-1, tx), ty][3] > 0:
                dr.rectangle([tx, ty, tx + 2, ty + 1], fill=c1)
            tx += 3; ty += 1 if s2 % 2 else -1
            if tx >= w - 3: break
        tx2, ty2 = gx0 + 4, gy0 + 5
        for s2 in range(6):
            if ty2 + 1 >= h or tx2 >= w - 2: break
            if px[min(w-1, tx2), ty2][3] > 0:
                dr.rectangle([tx2, ty2, tx2 + 1, ty2 + 1], fill=c2)
            tx2 += 2; ty2 += 1 if s2 % 2 else 0
    # 8) СИЛУЕТНИЙ КОНТУР — темна обводка 1px (читабельність на дрібному маштабі)
    a8 = np.array(img, dtype=np.int16)
    solid = a8[:, :, 3] > 40
    s8 = solid.astype(np.uint8)
    er = (s8 & np.roll(s8, 1, 0) & np.roll(s8, -1, 0) & np.roll(s8, 1, 1) & np.roll(s8, -1, 1)).astype(bool)
    edge = solid & ~er
    a8[:, :, 0][edge] = np.clip(a8[:, :, 0][edge] * 0.55, 0, 255)
    a8[:, :, 1][edge] = np.clip(a8[:, :, 1][edge] * 0.55, 0, 255)
    a8[:, :, 2][edge] = np.clip(a8[:, :, 2][edge] * 0.60, 0, 255)
    img = Image.fromarray(np.clip(a8, 0, 255).astype('uint8'), 'RGBA')
    # 9) грубі зернисті точки (шороховатість)
    dr = ImageDraw.Draw(img)
    px = img.load()
    n2 = 54 if heavy else 36
    for i in range(n2):
        x = int(K.IB_hsh(i, 3, 7) * w); y = int(K.IB_hsh(i, 5, 9) * h)
        if px[x, y][3] == 0: continue
        c = (14, 14, 16, 255) if i % 3 else (120, 70, 40, 255)
        dr.point((x, y), fill=c)
        if i % 7 == 0: dr.rectangle([x, y, x + 1, y], fill=c)
    return img

def build_buildings():
    import shutil
    count = 0
    for cat, (wT, dT, hpx, pool) in CATS.items():
        damaged_cat = cat.endswith('_dmg') or cat == 'hist_ruin'
        for i, (kit, name) in enumerate(pool):
            img = render_cat_model(kit, name, wT, dT, hpx)
            # ОСНОВНИЙ варіант — постапокаліптична обробка; графіті на 3-й варіанті кожної категорії
            graf = (i % 3 == 2)
            apoc = damage_post(img.copy(), heavy=damaged_cat, graffiti=graf)
            apoc.save(f'{OUT}/bld_{cat}_{i}.png')
            # _dmg варіант — ще сильніше зруйнований (розбиті вікна, сажа)
            dmg = damage_post(img.copy(), heavy=True, graffiti=graf)
            dmg.save(f'{OUT}/bld_{cat}_{i}_dmg.png')
            # синхронізація в public/game/assets
            shutil.copy(f'{OUT}/bld_{cat}_{i}.png', f'{OUT2}/bld_{cat}_{i}.png')
            shutil.copy(f'{OUT}/bld_{cat}_{i}_dmg.png', f'{OUT2}/bld_{cat}_{i}_dmg.png')
            count += 1
            print(f'  bld {cat}_{i}: {img.size}')
    print('buildings:', count)

# ------------------------------------------------------------------ roads
def rot_model(mdl, deg90):
    """rotate around vertical axis; y=up"""
    import copy
    m2 = copy.copy(mdl)
    vs = []
    for (x, y, z) in mdl.v:
        for _ in range(deg90):
            x, z = z, -x
        vs.append((x, y, z))
    m2.v = vs
    return m2

def edge_open(img):
    """classify 4 rhombus edges: open(road)=dark asphalt, closed=light curb.
    mask bits: 1=N(NE edge) 2=E(SE) 4=S(SW) 8=W(NW)"""
    # edge segments as (t along edge, point) — rhombus corners: N(16,0) E(32,8) S(16,16) W(0,8)
    NE = [(16 + t * 16, 0 + t * 8) for t in (0.35, 0.5, 0.65)]
    SE = [(32 - t * 16, 8 + t * 8) for t in (0.35, 0.5, 0.65)]
    SW = [(16 - t * 16, 16 - t * 8) for t in (0.35, 0.5, 0.65)]
    NW = [(0 + t * 16, 8 - t * 8) for t in (0.35, 0.5, 0.65)]
    res = 0
    px = img.load()
    for bit, seg in ((1, NE), (2, SE), (4, SW), (8, NW)):
        lum, n = 0, 0
        for (x0, y0) in seg:
            for dy in (0, 1):
                x, y = int(x0), int(y0) + dy
                if 0 <= x < 32 and 0 <= y < 16:
                    r, g, b, a = px[x, y]
                    if a > 0: lum += (r + g + b) / 3; n += 1
        if n == 0: continue
        if lum / n < 118: res |= bit   # dark asphalt = opening
    return res

def render_road_base(kit, name, rot=0):
    """ТЕКСТУРНИЙ рендер ×2: бордюри, текстура асфальту з colormap; кліп ромбом"""
    mdl = rot_model(K.load_obj(K.obj_path(kit, name)), rot)
    tex = K.load_tex(kit)
    def proj(x, y, z):
        return ((x - z) * 16 + 16, (x + z) * 8 + 8 - y * 16, x + z + y)
    r, _ = K.render_tex(mdl, tex, 32, 16, proj, SS=2, bands=4)
    mask = Image.new('L', (32, 16), 0)
    ImageDraw.Draw(mask).polygon([(16, 0), (32, 8), (16, 16), (0, 8)], fill=255)
    base = Image.new('RGBA', (32, 16), (0, 0, 0, 0))
    base.paste(r, (0, 0), mask)
    return base

DET = [(90, 92, 100), (58, 60, 70), (120, 122, 130)]   # сірі деталі (латки/тріщини/люки)

def wear_detail(img, m, seed):
    """ДЕТАЛІ АСФАЛЬТУ — СУБТИЛЬНІ (дрібні, мало контрастні): тріщини, латки, люки,
    водостоки, олійні плями, сміття. Не забивають текстуру й розмітку."""
    dr = ImageDraw.Draw(img)
    px = img.load()
    w, h = img.size
    inside = lambda x, y: 0 <= x < w and 0 <= y < h and px[x, y][3] > 0
    # 1) тріщини — тонкі зигзаги 3-5px, ледь темніші за асфальт
    for i in range(2):
        cx = 5 + int(K.IB_hsh(i, m, 301) * 22); cy = 3 + int(K.IB_hsh(i, m, 302) * 8)
        ln = 3 + int(K.IB_hsh(i, m, 303) * 3)
        dxs = 1 if K.IB_hsh(i, m, 304) < 0.5 else -1
        for s2 in range(ln):
            x, y = cx + dxs * (s2 % 2), cy + s2
            if not inside(x, y): break
            dr.point((x, y), fill=(56, 58, 68))
    # 2) латки — малі, ледь помітні
    for i in range(2):
        lx = 4 + int(K.IB_hsh(i, m, 311) * 22); ly = 4 + int(K.IB_hsh(i, m, 312) * 7)
        lw = 2 + int(K.IB_hsh(i, m, 313) * 3); lh = 1 + int(K.IB_hsh(i, m, 314) * 2)
        for yy in range(lh):
            for xx in range(lw):
                if K.IB_hsh(lx + xx, ly + yy, 315 + i) < 0.3: continue
                if inside(lx + xx, ly + yy): dr.point((lx + xx, ly + yy), fill=(76, 78, 88))
    # 3) люк — малий, на кожен третій тайл
    if K.IB_hsh(m, 9, 321) < 0.34:
        hx = 11 + int(K.IB_hsh(1, m, 322) * 10); hy = 6 + int(K.IB_hsh(2, m, 323) * 5)
        if inside(hx, hy):
            dr.ellipse([hx - 2, hy - 1, hx + 2, hy + 1], fill=(60, 62, 72))
            dr.point((hx, hy), fill=(72, 74, 84))
    # 4) олійна пляма — ледь видима
    if K.IB_hsh(m, 5, 341) < 0.5:
        ox = 7 + int(K.IB_hsh(1, m, 342) * 18); oy = 5 + int(K.IB_hsh(2, m, 343) * 6)
        if inside(ox, oy):
            dr.ellipse([ox - 2, oy - 1, ox + 2, oy + 1], fill=(62, 64, 74))
            dr.point((ox, oy), fill=(56, 58, 68))
    # 5) дрібне сміття — 2 цятки
    for i in range(2):
        sx2 = int(K.IB_hsh(i, m, 351) * 29) + 1; sy2 = int(K.IB_hsh(i, m, 352) * 13) + 1
        if inside(sx2, sy2):
            dr.point((sx2, sy2), fill=(148, 142, 126) if i % 2 else (108, 94, 74))

def markings(dr, m, L, D, W2='#c9d2e0', Y='#ffc044'):
    """engine-style розмітка — ЧИСТІ лінії з рідкісними зношеними пропусками.
    mask: 1=N 2=E 4=S 8=W. straights 5/10, corners 3/6/12/9."""
    cnt = bin(m).count('1')
    WW = (206, 212, 224)   # брудно-біла фарба
    WW2 = (168, 174, 188)  # зношений пропуск
    YY = (218, 166, 60)    # зношена жовта
    def dash_v(x, y0, y1):
        for yy in range(y0, y1 + 1):
            if 0 <= x < 32 and 0 <= yy < 16:
                dr.point((x, yy), fill=WW if (yy % 7) < 5 else WW2)   # довгі смуги, короткі пропуски
    def dash_h(y, x0, x1):
        for xx in range(x0, x1 + 1):
            if 0 <= xx < 32 and 0 <= y < 16:
                dr.point((xx, y), fill=WW if (xx % 7) < 5 else WW2)
    def seg(x0, y0, x1, y1, c):
        n = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i // max(1, n); y = y0 + (y1 - y0) * i // max(1, n)
            if 0 <= x < 32 and 0 <= y < 16: dr.point((x, y), fill=c)
    if cnt == 2:
        if m == 5:   # vertical (screen) straight
            dash_v(15, 0, 15); dash_v(16, 0, 15)
            for yy in (2, 9): dr.point((16, yy), fill=YY)
        elif m == 10:  # horizontal straight
            dash_h(8, 0, 31)
            for x in (5, 15, 25): dr.point((x, 8), fill=YY); dr.point((x + 1, 8), fill=YY)
        elif m == 3:   seg(16, 2, 27, 7, YY)
        elif m == 6:   seg(27, 8, 17, 13, YY)
        elif m == 12:  seg(15, 13, 5, 9, YY)
        elif m == 9:   seg(5, 7, 14, 2, YY)
    elif cnt == 3:
        # T-перехрестя: зебра поперек проїзду (чіткі смуги)
        if m in (14, 11):   # відкрито E/W: зебра вертикальна
            for xx in (6, 10, 14):
                for yy in range(4, 12): dr.point((xx, yy), fill=WW if (yy % 3) else WW2)
        else:               # відкрито N/S: зебра горизонтальна
            for yy in (4, 8, 12):
                for xx in range(6, 26): dr.point((xx, yy), fill=WW if (xx % 3) else WW2)
    elif cnt == 4:
        # повне перехрестя: зебри з чотирьох боків
        for xx in (7, 11, 15, 19, 23):
            dr.point((xx, 3), fill=WW); dr.point((xx, 12), fill=WW)
        for yy in (4, 6, 8, 10):
            dr.point((6, yy), fill=WW); dr.point((25, yy), fill=WW)
        dr.rectangle([13, 7, 18, 8], outline=WW)

def build_roads():
    # verified orientation table (no-shade probes):
    # straight rot0=10(E+W) rot1=5(N+S) | bend rot0=12 rot1=6 rot2=3 rot3=9
    # T rot0=14 rot1=7 rot2=11 rot3=13  | end rot0=2 rot1=1 rot2=8 rot3=4 | cross=15
    STR, BND, T, END, CRS = 'road-straight', 'road-bend', 'road-intersection', 'road-end', 'road-crossroad'
    plan = {}
    for m in range(16):
        cnt = bin(m).count('1')
        if cnt == 2:
            if m == 5: plan[m] = (STR, 1)      # N+S straight (vertical screen)
            elif m == 10: plan[m] = (STR, 0)   # E+W straight (horizontal screen)
            elif m == 3: plan[m] = (BND, 2)    # N+E corner
            elif m == 6: plan[m] = (BND, 1)    # E+S corner
            elif m == 12: plan[m] = (BND, 0)   # S+W corner
            elif m == 9: plan[m] = (BND, 3)    # W+N corner
        elif cnt == 3:
            plan[m] = {14: (T, 0), 7: (T, 1), 11: (T, 2), 13: (T, 3)}[m]
        elif cnt == 1:
            plan[m] = {2: (END, 0), 1: (END, 1), 8: (END, 2), 4: (END, 3)}[m]
        else:
            plan[m] = (CRS, 0)
    for m in range(16):
        nm, rot = plan[m]
        img = render_road_base(RDS, nm, rot)
        dr = ImageDraw.Draw(img)
        markings(dr, m, None, None)
        wear_detail(img, m, 3)
        img.save(f'{OUT}/road_{m}.png')
    # wide interior: ТЕКСТУРНИЙ асфальт з деталями (латки, тріщини, люк)
    img = Image.new('RGBA', (32, 16), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.polygon([(16, 0), (32, 8), (16, 16), (0, 8)], fill=(81, 85, 102, 255))
    for i in range(34):
        x = int(K.IB_hsh(i, 11, 2) * 30) + 1; y = int(K.IB_hsh(i, 13, 3) * 14) + 1
        dr.point((x, y), fill=(96, 100, 118, 255) if i % 2 else (70, 74, 90, 255))
    wear_detail(img, 99, 3)
    img.save(f'{OUT}/road_wide.png')
    print('roads: 16 + wide')

# ------------------------------------------------------------------ props
PROPS = [
    # (out, kit, model, target_h_px, target_w_px or None) — БАТЧ 8: пропси БІЛЬШІ (масштаб міста)
    ('tree_o',   SUB, 'tree-large', 58, 44),
    ('tree_o2',  SUB, 'tree-small', 40, 32),
    ('pine',     SUB, 'tree-large', 62, 28),
    ('dumpster', RDS, 'dumpster', 18, 34),
    ('traff',    RDS, 'traffic-light', 42, None),
    ('lamp',     RDS, 'light-curved', 48, None),
    ('lamp_b',   RDS, 'light-square', 44, None),
    ('barr',     RDS, 'construction-barrier', 16, None),
    ('cone',     RDS, 'construction-cone', 12, None),
    ('crate',    IND, 'shipping-container-a', 18, 32),
    ('crate2',   IND, 'shipping-container-b', 18, 32),
    ('crate3',   IND, 'shipping-container-c', 18, 32),
    ('chimney',  IND, 'chimney-large', 40, None),
    ('tank',     IND, 'detail-tank-large', 20, 36),
    ('fence',    SUB, 'fence-1x3', 14, 34),
    ('bush',     SUB, 'planter', 14, 28),
    ('antenna',  RDS, 'electricity-pole', 38, None),
]

def render_prop_tex(kit, name, out_name, target_h=None, target_w=None, margin=3):
    """ТЕКСТУРНИЙ пропс ×2 суперсемпл, якір низ-центр (зберігає конвенцію kenney.js)"""
    mdl = load_obj_local(kit, name)
    tex = K.load_tex(kit)
    x0, x1, y0, y1, z0, z1 = K.bbox(mdl)
    mX = max(1e-6, x1 - x0); mZ = max(1e-6, z1 - z0); mH = max(1e-6, y1 - y0)
    s = 16.0
    if target_h: s = target_h / (mH * 16)
    if target_w:
        wpx = (mX + mZ) * 16 * s
        if wpx > target_w: s *= target_w / wpx
    if s < 0.8: s = 0.8
    W = int((mX + mZ) * 16 * s) + margin * 2 + 2
    H = int(mH * 16 * s) + int((mX + mZ) * 8 * s) + margin * 2 + 2
    def proj(x, y, z):
        u = (x - x0) * s
        v = (z - z0) * s
        return (margin + (u - v) * 16 + mZ * 16 * s, margin + mH * 16 * s + (u + v) * 8 - (y - y0) * 16 * s,
                u + v + (y - y0) * s)
    r, _ = K.render_tex(mdl, tex, W, H, proj, SS=2, bands=5)
    bb = r.getbbox()
    if bb: r = r.crop(bb)
    r.save(os.path.join(OUT, out_name + '.png'))
    return r

def load_obj_local(kit, name):
    return K.load_obj(K.obj_path(kit, name))

def build_props():
    for out, kit, name, th, tw in PROPS:
        img = render_prop_tex(kit, name, out, target_h=th, target_w=tw)
        print(f'  prop {out}: {img.size}')
    # crate variants: world uses 'crate' -> kenney.js picks random of crate/crate2/crate3
    print('props done')

if __name__ == '__main__':
    build_buildings()
    build_roads()
    build_props()
    print('ALL ASSETS DONE')
