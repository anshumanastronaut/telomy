#!/usr/bin/env python3
"""Build the 3D twin's anatomy GLB from BodyParts3D (DBCLS, CC BY 4.0) — real organ meshes segmented from a CT-scanned
human body, merged per Telomy organ system, decimated for mobile, oriented Y-up / facing +Z / feet on the floor.

Attribution required by the licence: "BodyParts3D, © The Database Center for Life Science, licensed under CC BY 4.0".

  python ml/anatomy/build_glb.py --src ~/telomy-lab/bodyparts3d --out ~/telomy-lab/bodyparts3d/telomy_anatomy.glb
"""
from __future__ import annotations
import argparse, collections, os, re
import numpy as np
import pyfqmr
import trimesh

# organ id → (concept names to include, target triangles). Names are BodyParts3D "part-of" concept names.
GROUPS = {
    'skin':       (['skin'], 30000),
    'brain':      (['brain'], 12000),
    'heart':      (['heart'], 9000),
    'lungs':      (['left lung', 'right lung', 'trachea'], 10000),
    'liver':      (['liver'], 6000),
    'stomach':    (['stomach', 'esophagus'], 4000),
    'pancreas':   (['pancreas'], 1800),
    'kidneys':    (['left kidney', 'right kidney'], 3000),
    'intestines': (['small intestine', 'large intestine'], 9000),
    'bladder':    (['urinary bladder'], 1200),
    'vessels':    ([r're:^(aorta|.*carotid artery|.*subclavian artery|brachiocephalic trunk|.*common iliac artery|.*external iliac artery|.*femoral artery)$'], 6000),
    'skeleton':   (['skeletal system'], 30000),
}
# NB: BodyParts3D 4.0 (part-of, 99 %) has no skeletal-muscle meshes — its "musculoskeletal system" is the 138 bones only.


def load_index(src):
    by_name, by_elem = collections.defaultdict(set), collections.defaultdict(set)
    with open(os.path.join(src, 'partof_element_parts.txt')) as f:
        next(f)
        for line in f:
            cid, name, eid = line.rstrip('\n').split('\t')[:3]
            by_name[name].add(eid); by_elem[eid].add(name)
    return by_name, by_elem


def elements_for(spec, by_name):
    out = set()
    for s in spec:
        if s.startswith('re:'):
            rx = re.compile(s[3:])
            for n, es in by_name.items():
                if rx.search(n): out |= es
        else:
            out |= by_name.get(s, set())
    return out


def decimate(m: trimesh.Trimesh, target: int) -> trimesh.Trimesh:
    if len(m.faces) <= target: return m
    s = pyfqmr.Simplify(); s.setMesh(m.vertices, m.faces)
    s.simplify_mesh(target_count=target, aggressiveness=7, preserve_border=False, verbose=0)
    v, f, _ = s.getMesh()
    return trimesh.Trimesh(v, f, process=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.expanduser('~/telomy-lab/bodyparts3d'))
    ap.add_argument('--out', default=os.path.expanduser('~/telomy-lab/bodyparts3d/telomy_anatomy.glb'))
    a = ap.parse_args()
    objdir = os.path.join(a.src, 'objs', 'partof_BP3D_4.0_obj_99')
    by_name, by_elem = load_index(a.src)
    claimed: set[str] = set()
    meshes = {}
    # organs first, then the body-wide systems, so an element belongs to the most specific group
    for gid in ['brain', 'heart', 'lungs', 'liver', 'stomach', 'pancreas', 'kidneys', 'intestines', 'bladder', 'vessels', 'skin', 'skeleton']:
        spec, target = GROUPS[gid]
        elems = sorted(e for e in elements_for(spec, by_name) - claimed if os.path.exists(os.path.join(objdir, e + '.obj')))
        claimed |= set(elems)
        parts = []
        for e in elems:
            m = trimesh.load(os.path.join(objdir, e + '.obj'), force='mesh', process=False)
            if isinstance(m, trimesh.Trimesh) and len(m.faces): parts.append(m)
        if not parts:
            print(f'{gid:11s} — no elements'); continue
        total = sum(len(m.faces) for m in parts)
        r = min(1.0, target / total)            # simplify each piece proportionally (many small pieces stall a merged pass)
        merged = trimesh.util.concatenate([decimate(m, max(40, int(len(m.faces) * r))) for m in parts])
        meshes[gid] = merged
        print(f'{gid:11s} {len(elems):4d} elements  {total:7d} → {len(merged.faces):6d} tris')

    # ---- orientation, from the data itself
    allv = np.vstack([m.vertices for m in meshes.values()])
    ext = allv.max(0) - allv.min(0)
    up = int(np.argmax(ext))                                   # tallest axis = head-to-foot
    rest = [i for i in range(3) if i != up]
    # depth axis: the heart sits in front of the spine → the axis where they differ most is front/back
    spine = meshes['skeleton'].vertices
    spine = spine[np.abs(spine[:, rest[0]] - np.median(spine[:, rest[0]])) < 25]   # midline band ≈ vertebrae
    hc, sc = meshes['heart'].vertices.mean(0), spine.mean(0)
    depth = max(rest, key=lambda i: abs(hc[i] - sc[i])); lateral = [i for i in rest if i != depth][0]
    front_sign = np.sign(hc[depth] - sc[depth])
    head_sign = np.sign(meshes['brain'].vertices.mean(0)[up] - allv.mean(0)[up])

    def to_three(v):
        x = v[:, lateral]; y = v[:, up] * head_sign; z = v[:, depth] * front_sign
        return np.stack([x, y, z], 1) / 1000.0                 # mm → m

    # left/right: the liver is on the body's right = the viewer's LEFT (−x) when the body faces +z
    liver_x = to_three(meshes['liver'].vertices)[:, 0].mean() - to_three(allv)[:, 0].mean()
    mirror = liver_x > 0
    scene = trimesh.Scene()
    base = to_three(allv); y0 = base[:, 1].min(); cx = base[:, 0].mean(); cz = base[:, 2].mean()
    for gid, m in meshes.items():
        v = to_three(m.vertices)
        if mirror: v[:, 0] = -v[:, 0]
        v[:, 0] -= cx if not mirror else -cx
        v[:, 1] -= y0; v[:, 2] -= cz
        f = m.faces[:, ::-1] if (mirror ^ (np.linalg.det(np.eye(3)) < 0)) else m.faces
        tm = trimesh.Trimesh(v, f, process=False); tm.fix_normals()
        scene.add_geometry(tm, node_name=gid, geom_name=gid)
    scene.export(a.out)
    h = (base[:, 1].max() - y0)
    print(f'axes up={up} depth={depth} lateral={lateral} front={front_sign:+.0f} mirror={mirror}  height {h:.2f} m')
    print(f'wrote {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
