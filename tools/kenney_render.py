#!/usr/bin/env python3
"""Kenney City Kit -> isometric renderer for IBONARIUM KYIV engine.
Projects Kenney OBJ models into the engine's 2:1 iso projection:
  screen_x = (u - v) * 16,  screen_y = (u + v) * 8 - z * 16
where u,v are tile coords (1 unit = 1 tile). Produces PNG assets.
"""
import os, sys, math, json
import numpy as np
from PIL import Image

SRC = os.path.join(os.path.dirname(__file__), 'kenney_src', 'extracted')
OUT = '/home/z/my-project/download/ibonarium-kyiv/assets'
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- OBJ loader
class Model:
    def __init__(self):
        self.v = []   # (x,y,z)
        self.vt = []  # (u,v)
        self.faces = []  # list of (verts[(vi,ti)...], )

def load_obj(path):
    m = Model()
    vbase, tbase = 1, 1
    for line in open(path, encoding='utf-8', errors='ignore'):
        parts = line.split()
        if not parts: continue
        if parts[0] == 'v':
            m.v.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == 'vt':
            m.vt.append((float(parts[1]), float(parts[2])))
        elif parts[0] == 'f':
            idx = []
            ok = True
            for p in parts[1:]:
                seg = p.split('/')
                vi = int(seg[0])
                ti = int(seg[1]) if len(seg) > 1 and seg[1] else None
                idx.append((vi, ti))
            if ok and len(idx) >= 3:
                # triangulate fan
                for i in range(1, len(idx) - 1):
                    m.faces.append((idx[0], idx[i], idx[i + 1]))
    return m

def face_color(tex, uvs):
    """sample texture at uv centroid (nearest)"""
    if not uvs: return (255, 0, 255)
    u = sum(uv[0] for uv in uvs) / len(uvs)
    v = sum(uv[1] for uv in uvs) / len(uvs)
    x = int(u * tex.width) % tex.width
    y = int((1 - v) * tex.height) % tex.height
    px = tex.getpixel((x, y))
    return px[:3]

def shade_color(rgb, n):
    """flat lambert: light from top-left-front, quantized to 3 bands (Kenney flat look)"""
    L = (-0.38, 0.86, -0.33)  # world axes: x,y horizontal, z up
    d = n[0]*L[0] + n[1]*L[1] + n[2]*L[2]
    if d > 0.72: f = 1.0
    elif d > 0.30: f = 0.80
    else: f = 0.62
    if abs(n[2]) > 0.9: f = 1.0          # pure tops stay brightest
    return (int(rgb[0]*f), int(rgb[1]*f), int(rgb[2]*f))

def render(mdl, tex, W, H, proj, z_up=16, flip_faces=False, max_faces=40000, no_shade=False):
    """proj(v3 world (x,y,z)) -> (sx,sy,depth); world axes x,y horizontal, z=up.
       Returns PIL RGB image WxH transparent."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    polys = []
    verts = mdl.v
    for f in mdl.faces[:max_faces]:
        pts = []
        uvs = []
        for vi, ti in f:
            i = vi - 1 if vi > 0 else len(verts) + vi
            x, y, z = verts[i]
            sx, sy, dep = proj(x, y, z)
            pts.append((sx, sy, dep))
            if ti is not None and mdl.vt:
                j = ti - 1 if ti > 0 else len(mdl.vt) + ti
                if 0 <= j < len(mdl.vt): uvs.append(mdl.vt[j])
        if len(pts) < 3: continue
        # face normal (world space)
        ax = pts  # reuse? no - need world
        polys.append((pts, uvs))
    # compute normals in world space separately
    out = []
    for f in mdl.faces[:max_faces]:
        wp = []
        uvs = []
        for vi, ti in f:
            i = vi - 1 if vi > 0 else len(verts) + vi
            x, y, z = verts[i]
            wp.append((x, y, z))
            if ti is not None and mdl.vt:
                j = ti - 1 if ti > 0 else len(mdl.vt) + ti
                if 0 <= j < len(mdl.vt): uvs.append(mdl.vt[j])
        if len(wp) < 3: continue
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = wp[0], wp[1], wp[2]
        ux, uy, uz = x2-x1, y2-y1, z2-z1
        vx, vy, vz = x3-x1, y3-y1, z3-z1
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        ln = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
        nx, ny, nz = nx/ln, ny/ln, nz/ln
        if ny < -0.92 and not flip_faces:  # cull only pure undersides (leaf cones stay)
            continue
        depth = (x1+x2+x3)/3 + (y1+y2+y3)/3 + (z1+z2+z3)/3
        sx_pts = []
        for (x, y, z) in wp:
            sx, sy, _ = proj(x, y, z)
            sx_pts.append((sx, sy))
        col = face_color(tex, uvs) if no_shade else shade_color(face_color(tex, uvs), (nx, ny, nz))
        out.append((depth, sx_pts, col))
    out.sort(key=lambda t: t[0])
    from PIL import ImageDraw
    dr = ImageDraw.Draw(img)
    for depth, spts, col in out:
        if all(p[0] < -2 or p[0] > W+2 or p[1] < -2 or p[1] > H+2 for p in spts):
            continue
        dr.polygon(spts, fill=col+(255,))
    return img

def shade_factor(n, bands=5):
    """fine lambert bands (5 замість 3 — плавніші переходи світла, більше півтонів)"""
    L = (-0.38, 0.86, -0.33)
    d = n[0]*L[0] + n[1]*L[1] + n[2]*L[2]
    if abs(n[2]) > 0.9: return 1.0
    if bands >= 5:
        if d > 0.80: f = 1.0
        elif d > 0.52: f = 0.88
        elif d > 0.28: f = 0.77
        elif d > 0.06: f = 0.66
        else: f = 0.55
    else:
        if d > 0.72: f = 1.0
        elif d > 0.30: f = 0.80
        else: f = 0.62
    return f

def render_tex(mdl, tex, W, H, proj, SS=2, bands=5, max_faces=60000):
    """ТЕКСТУРНИЙ рендер: UV-інтерполяція кольорових карт Kenney на кожен піксель,
    z-buffer замість сортування фарбувальника, суперсемплінг SS з LANCZOS-даунскейлом.
    Дає справжні вікна/рамки/цеглу/двері з colormap замість плоских плям.
    proj(v3 world) -> (sx,sy,depth); більше depth = ближче до камери."""
    Ws, Hs = W*SS, H*SS
    img = np.zeros((Hs, Ws, 4), dtype=np.float32)
    zbuf = np.full((Hs, Ws), -1e9, dtype=np.float32)
    tarr = np.asarray(tex.convert('RGB'), dtype=np.float32)
    tw, th = tex.size
    verts = mdl.v
    nvt = len(mdl.vt)
    count = 0
    for f in mdl.faces[:max_faces]:
        wp = []; sp = []; uv = []
        for vi, ti in f:
            i = vi - 1 if vi > 0 else len(verts) + vi
            if not (0 <= i < len(verts)): break
            x, y, z = verts[i]
            sx, sy, dep = proj(x, y, z)
            wp.append((x, y, z)); sp.append((sx*SS, sy*SS, dep))
            if ti is not None and nvt:
                j = ti - 1 if ti > 0 else nvt + ti
                if 0 <= j < nvt: uv.append(mdl.vt[j])
        if len(sp) < 3: continue
        if len(uv) != len(sp):
            # грань без UV — беремо колір-центроїд (плоский колір)
            if uv:
                cu = sum(u[0] for u in uv)/len(uv); cv = sum(u[1] for u in uv)/len(uv)
            else:
                cu = cv = 0.5
            uv = [ (cu, cv) ] * len(sp)
        (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = wp[0], wp[1], wp[2]
        ux, uy, uz = x2-x1, y2-y1, z2-z1
        vx, vy, vz = x3-x1, y3-y1, z3-z1
        nx, ny, nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        ln = math.sqrt(nx*nx+ny*ny+nz*nz) or 1
        nyx = ny/ln
        if nyx < -0.92: continue        # чисті низи не малюємо
        shade = shade_factor((nx/ln, nyx, nz/ln), bands)
        xs = [p[0] for p in sp]; ys = [p[1] for p in sp]
        minx = max(0, int(min(xs))); maxx = min(Ws-1, int(max(xs))+1)
        miny = max(0, int(min(ys))); maxy = min(Hs-1, int(max(ys))+1)
        if minx > maxx or miny > maxy: continue
        (ax, ay, ad), (bx, by, bd), (cx, cy, cd) = sp
        (u0, v0), (u1, v1), (u2, v2) = uv[0], uv[1], uv[2]
        den = (by-cy)*(ax-cx) + (cx-bx)*(ay-cy)
        if abs(den) < 1e-9: continue
        gx = np.arange(minx, maxx+1, dtype=np.float32) + 0.5
        gy = np.arange(miny, maxy+1, dtype=np.float32) + 0.5
        GX, GY = np.meshgrid(gx, gy)
        w0 = ((by-cy)*(GX-cx) + (cx-bx)*(GY-cy)) / den
        w1 = ((cy-ay)*(GX-cx) + (ax-cx)*(GY-cy)) / den
        w2 = 1.0 - w0 - w1
        mask = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
        if not mask.any(): continue
        depth = w0*ad + w1*bd + w2*cd
        uu = np.mod(w0*u0 + w1*u1 + w2*u2, 1.0)
        vv = w0*v0 + w1*v1 + w2*v2
        px = np.clip((uu*tw).astype(np.int32) % tw, 0, tw-1)
        py = np.clip(((1.0-vv)*th).astype(np.int32) % th, 0, th-1)
        col = tarr[py, px] * shade
        zb = zbuf[miny:maxy+1, minx:maxx+1]
        upd = mask & (depth > zb)
        if not upd.any(): continue
        zb[upd] = depth[upd]
        reg = img[miny:maxy+1, minx:maxx+1]
        reg[upd, 0] = col[upd, 0]; reg[upd, 1] = col[upd, 1]; reg[upd, 2] = col[upd, 2]
        reg[upd, 3] = 255.0
        count += 1
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA')
    if SS > 1:
        out = out.resize((W, H), Image.LANCZOS)
    return out, count

def bbox(mdl):
    xs = [v[0] for v in mdl.v]; ys = [v[1] for v in mdl.v]; zs = [v[2] for v in mdl.v]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

def load_tex(kit):
    p = os.path.join(SRC, kit, 'Models', 'OBJ format', 'Textures', 'colormap.png')
    return Image.open(p).convert('RGB')

def obj_path(kit, name):
    return os.path.join(SRC, kit, 'Models', 'OBJ format', name + '.obj')

# ------------------------------------------------------------ projections
def proj_tile(u, v, z):
    """1x1 tile centered: u,v in [-.5,.5] -> 32x16 canvas"""
    return ((u - v) * 16 + 16, (u + v) * 8 + 2 - z * 16, u + v + z)

def proj_tile_custom(u, v, z):
    return ((u - v) * 16 + 15.5, (u + v) * 8 + 0.5 - z * 16, u + v + z)

# ---------------------------------------------------------------- renderers
def render_tile(kit, name, out_name):
    """ground tile: full 1x1 model -> 32x16 rhombus-clipped"""
    mdl = load_obj(obj_path(kit, name))
    tex = load_tex(kit)
    x0, x1, y0, y1, z0, z1 = bbox(mdl)
    img = Image.new('RGBA', (32, 16), (0, 0, 0, 0))
    # project model (already unit centered) via u=x, v=z
    def proj(x, y, z):
        return proj_tile(x, z, y)
    r = render(mdl, tex, 32, 16, proj)
    # clip to rhombus
    mask = Image.new('L', (32, 16), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).polygon([(16,0),(32,8),(16,16),(0,8)], fill=255)
    img.paste(r, (0, 0), mask)
    img.save(os.path.join(OUT, out_name + '.png'))
    return img

def render_tile_full(kit, name, out_name, W=32, H=16):
    """tile WITHOUT rhombus clip (for tiles with raised parts like curbs) — content-cropped"""
    mdl = load_obj(obj_path(kit, name))
    tex = load_tex(kit)
    def proj(x, y, z):
        return proj_tile(x, z, y)
    r = render(mdl, tex, W, H, proj)
    bb = r.getbbox()
    if bb: r = r.crop(bb)
    r.save(os.path.join(OUT, out_name + '.png'))
    return r

def render_building(kit, name, out_name, wT, dT, hpx, base=True):
    """building model anisotropic-fit to footprint (wT,dT), height<=hpx.
       Output canvas matches engine cat canvas: W=(wT+dT)*16+4 H=(wT+dT)*8+hpx+8
       N corner at (2+dT*16, 8)."""
    mdl = load_obj(obj_path(kit, name))
    tex = load_tex(kit)
    x0, x1, y0, y1, z0, z1 = bbox(mdl)
    mX = max(1e-6, x1 - x0); mZ = max(1e-6, z1 - z0); mH = max(1e-6, y1 - y0)
    W = (wT + dT) * 16 + 4
    H = (wT + dT) * 8 + hpx + 8
    # scales: model spans mX tiles in u, mZ in v; height mH*sy_scale*16 <= hpx
    su = wT / mX
    sv = dT / mZ
    sy = min(hpx / (mH * 16), (su + sv) / 2 * 1.35)  # cap vertical stretch
    def proj(x, y, z):
        u = (x - x0) * su            # 0..wT
        v = (z - z0) * sv            # 0..dT
        sx = (2 + dT * 16) + (u - v) * 16
        syy = 8 + (u + v) * 8 - (y - y0) * 16 * sy
        return (sx, syy, u + v + (y - y0) * sy)
    r = render(mdl, tex, W, H, proj)
    # crop top whitespace only (keep bottom anchored at footprint)
    bb = r.getbbox()
    if bb:
        # content may extend below H (footprint bottom edge) - keep as is
        r2 = r.crop((0, max(0, bb[1] - 2), W, min(H, bb[3] + 1)))
        if r2.height < H:
            full = Image.new('RGBA', (W, r2.height), (0, 0, 0, 0))
            full.paste(r2, (0, 0))
            r = full
    r.save(os.path.join(OUT, out_name + '.png'))
    return r, W, r.height

def render_prop(kit, name, out_name, target_h=None, target_w=None, scale=None, margin=3):
    """prop with uniform scale; anchor: bottom-center of content"""
    mdl = load_obj(obj_path(kit, name))
    tex = load_tex(kit)
    x0, x1, y0, y1, z0, z1 = bbox(mdl)
    mX = max(1e-6, x1 - x0); mZ = max(1e-6, z1 - z0); mH = max(1e-6, y1 - y0)
    if scale is None:
        s = 16.0
        if target_h: s = target_h / (mH * 16)
        if target_w:
            wpx = (mX + mZ) * 16 * s
            if wpx > target_w: s *= target_w / wpx
        if s < 0.8: s = 0.8
    else:
        s = scale
    W = int((mX + mZ) * 16 * s) + margin * 2 + 2
    H = int(mH * 16 * s) + int((mX + mZ) * 8 * s) + margin * 2 + 2
    def proj(x, y, z):
        u = (x - x0) * s
        v = (z - z0) * s
        return (margin + (u - v) * 16 + mZ * 16 * s, margin + mH * 16 * s + (u + v) * 8 - (y - y0) * 16 * s,
                u + v + (y - y0) * s)
    r = render(mdl, tex, W, H, proj)
    bb = r.getbbox()
    if bb: r = r.crop(bb)
    r.save(os.path.join(OUT, out_name + '.png'))
    return r

# ---------------------------------------------------------------- batch jobs
if __name__ == '__main__':
    jobs = sys.argv[1] if len(sys.argv) > 1 else 'tiles'
    if jobs == 'tiles':
        # test render: roads straight/bend/crossroad/intersection, grass, sidewalk-ish
        render_tile('city-kit-roads', 'road-straight', 'test_road_straight')
        render_tile('city-kit-roads', 'road-straight', 'test_road_straight2')
        render_tile('city-kit-roads', 'road-bend', 'test_road_bend')
        render_tile('city-kit-roads', 'road-crossroad', 'test_road_crossroad')
        render_tile('city-kit-roads', 'road-intersection', 'test_road_intersection')
        render_tile('city-kit-roads', 'road-end', 'test_road_end')
        # montage x6
        names = ['test_road_straight', 'test_road_bend', 'test_road_crossroad', 'test_road_intersection', 'test_road_end']
        montage = Image.new('RGBA', (32 * len(names), 16), (20, 20, 30, 255))
        for i, n in enumerate(names):
            montage.paste(Image.open(os.path.join(OUT, n + '.png')), (i * 32, 0))
        montage = montage.resize((32 * len(names) * 6, 96), Image.NEAREST)
        montage.save(os.path.join(OUT, '_montage_roads.png'))
        print('tiles done')

# deterministic hash for build scripts (same formula as engine)
import hashlib
def IB_hsh(x, y, s=0):
    h = (int(x) * 374761393 + int(y) * 668265263 + int(s) * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return h / 4294967296.0
