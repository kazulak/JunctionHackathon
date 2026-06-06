"""
emerald_patch_finder.py
=======================
Parse an IQM Emerald (CRYSTAL-54) calibration JSON, reconstruct the device
coupling graph, score every qubit/coupler, and find the best-scoring rotated
surface-code patches (d=3 and d=5) that embed into the lattice with ZERO SWAPs.

Zero-SWAP guarantee: every two-qubit interaction in the syndrome-extraction
circuit is an ancilla<->data CZ. We embed the exact Stim rotated-surface-code
template so that every such interaction lands on a physical CZ coupler. No
data-data or ancilla-ancilla coupling is ever required, so no routing/SWAPs.

Usage:
    python emerald_patch_finder.py CALIBRATION.json [--t-round-us 1.0]
"""
from __future__ import annotations
import json, re, argparse, itertools, math
from collections import defaultdict, deque, Counter

# ----------------------------------------------------------------------------
# 1. Parse calibration JSON into per-qubit / per-coupler metric dictionaries
# ----------------------------------------------------------------------------
def load_metrics(path):
    data = json.load(open(path))
    obs = data["observations"]
    val = {}
    for o in obs:
        val[o["dut_field"]] = o["value"]

    def q1(f):  # single-qubit index from a non-coupler field
        mm = re.findall(r"QB(\d+)", re.sub(r"QB\d+__QB\d+", "", f))
        return int(mm[0]) if mm else None

    def cpl(f):  # ordered-then-sorted coupler tuple
        m = re.search(r"QB(\d+)__QB(\d+)", f)
        return tuple(sorted((int(m.group(1)), int(m.group(2)))))

    M = dict(
        prx_err={}, clifford1_err={}, ro_err={}, ro_e01={}, ro_e10={},
        qnd_fid={}, qnd0={}, qnd1={}, repeat={},
        t1={}, t2={}, t2e={}, cz_err={}, clifford2_err={},
    )
    for f, v in val.items():
        if f.startswith("metrics.rb.prx.drag_crf_sx"):           M["prx_err"][q1(f)] = 1 - v
        elif f.startswith("metrics.rb.clifford.xy_sx"):          M["clifford1_err"][q1(f)] = 1 - v
        elif f.startswith("metrics.ssro.measure.constant") and f.endswith(".fidelity"):    M["ro_err"][q1(f)] = 1 - v
        elif f.startswith("metrics.ssro.measure.constant") and f.endswith(".error_0_to_1"): M["ro_e01"][q1(f)] = v
        elif f.startswith("metrics.ssro.measure.constant") and f.endswith(".error_1_to_0"): M["ro_e10"][q1(f)] = v
        elif "qndness" in f and f.endswith(".fidelity"):          M["qnd_fid"][q1(f)] = v
        elif "qndness" in f and f.endswith(".qndness_0"):         M["qnd0"][q1(f)] = v
        elif "qndness" in f and f.endswith(".qndness_1"):         M["qnd1"][q1(f)] = v
        elif "qndness" in f and f.endswith(".repeatability"):     M["repeat"][q1(f)] = v
        elif f.endswith(".t1_time"):                              M["t1"][q1(f)] = v
        elif f.endswith(".t2_time"):                              M["t2"][q1(f)] = v
        elif f.endswith(".t2_echo_time"):                         M["t2e"][q1(f)] = v
        elif f.startswith("metrics.irb.cz"):                      M["cz_err"][cpl(f)] = 1 - v
        elif f.startswith("metrics.rb.clifford.uz_cz"):           M["clifford2_err"][cpl(f)] = 1 - v
    return M, data.get("dut_label", "?")


# ----------------------------------------------------------------------------
# 2. Reconstruct device graph + integer lattice coords (col,row)
# ----------------------------------------------------------------------------
def build_device(M):
    edges = set(M["cz_err"].keys())
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    # BFS coordinate assignment: |Δidx|==1 -> horizontal, else vertical
    coord = {1: (0, 0)}; dq = deque([1])
    while dq:
        u = dq.popleft(); x, y = coord[u]
        for v in adj[u]:
            if v in coord:
                continue
            coord[v] = (x + (1 if v > u else -1), y) if abs(u - v) == 1 \
                       else (x, y + (1 if v > u else -1))
            dq.append(v)
    minx = min(c[0] for c in coord.values())
    maxy = max(c[1] for c in coord.values())
    cr = {q: (x - minx, maxy - y) for q, (x, y) in coord.items()}  # col, row (row 0 = top)
    return edges, adj, cr


def coupling_map_qiskit(edges):
    """Directed coupling map, 0-indexed (Qiskit convention: QBn -> n-1)."""
    cm = []
    for a, b in sorted(edges):
        cm.append([a - 1, b - 1]); cm.append([b - 1, a - 1])
    return cm


# ----------------------------------------------------------------------------
# 3. Canonical rotated surface-code template (from Stim), in axis-aligned coords
# ----------------------------------------------------------------------------
def surface_template(distance):
    import stim
    c = stim.Circuit.generated("surface_code:rotated_memory_z",
                               distance=distance, rounds=1)
    coords = c.get_final_qubit_coordinates()
    mr, m, pairs = set(), set(), set()
    for inst in c.flattened():
        n = inst.name
        if n in ("MR", "MRZ", "MRX"):
            mr |= {t.value for t in inst.targets_copy()}
        if n in ("M", "MZ", "MX"):
            m |= {t.value for t in inst.targets_copy()}
        if n in ("CX", "CZ", "ZCX"):
            ts = [t.value for t in inst.targets_copy()]
            pairs |= {frozenset((ts[i], ts[i + 1])) for i in range(0, len(ts), 2)}
    data, anc = m - mr, mr
    # Stim rotated-code edges are diagonal Δ=(±1,±1); rotate 45deg -> unit axis bonds
    lat = {q: (int((coords[q][0] + coords[q][1]) // 2),
               int((coords[q][0] - coords[q][1]) // 2)) for q in coords}
    nodes = {q: ("data" if q in data else "anc") for q in coords}
    tedges = [tuple(p) for p in pairs]          # (ancilla,data) interaction pairs
    return lat, nodes, tedges


# 8 dihedral orientations of the square lattice
def _orient(p, k):
    x, y = p
    rot = [(x, y), (-y, x), (-x, -y), (y, -x)][k % 4]
    return (rot[0], -rot[1]) if k >= 4 else rot


# ----------------------------------------------------------------------------
# 4. Enumerate zero-SWAP embeddings of the template into the device
# ----------------------------------------------------------------------------
def find_placements(lat, nodes, tedges, dev_edges, cr):
    dev_nodes = set(cr.keys())
    dev_eset = {frozenset(e) for e in dev_edges}
    tmpl_ids = list(lat.keys())
    anchor = tmpl_ids[0]
    placements, seen = [], set()
    for k in range(8):
        olat = {q: _orient(lat[q], k) for q in tmpl_ids}
        ox, oy = olat[anchor]
        for dq in dev_nodes:
            dx, dy = cr[dq]
            shift = (dx - ox, dy - oy)
            # map every template node to a device position
            pos2dev = {v: k_ for k_, v in cr.items()}
            mapping, ok = {}, True
            for q in tmpl_ids:
                p = (olat[q][0] + shift[0], olat[q][1] + shift[1])
                if p not in pos2dev:
                    ok = False; break
                mapping[q] = pos2dev[p]
            if not ok or len(set(mapping.values())) != len(tmpl_ids):
                continue
            # every template interaction must be a physical coupler
            if any(frozenset((mapping[a], mapping[b])) not in dev_eset for a, b in tedges):
                continue
            key = frozenset(mapping.values())
            if key in seen:
                continue
            seen.add(key)
            data_qs = sorted(mapping[q] for q in tmpl_ids if nodes[q] == "data")
            anc_qs  = sorted(mapping[q] for q in tmpl_ids if nodes[q] == "anc")
            used_edges = [tuple(sorted((mapping[a], mapping[b]))) for a, b in tedges]
            placements.append(dict(orientation=k, data=data_qs, anc=anc_qs,
                                   edges=used_edges, mapping=mapping))
    return placements


# ----------------------------------------------------------------------------
# 5. Composite physical-error figure of merit (per QEC round). Lower = better.
# ----------------------------------------------------------------------------
def score_patch(p, M, t_round_s, w=None):
    w = w or dict(gate=1, idle=1, ro=1, qnd=1, cz=1)

    def p_idle(q):  # decoherence per round (echoed dephasing dominant)
        T2 = M["t2e"].get(q) or M["t2"].get(q) or 1e-3
        return 1 - math.exp(-t_round_s / T2)

    def qnd_fail(q):  # worst-state non-demolition failure
        q0, q1 = M["qnd0"].get(q), M["qnd1"].get(q)
        if q0 is not None and q1 is not None:
            return 1 - min(q0, q1)
        return 1 - M["qnd_fid"].get(q, 1.0)

    parts = []
    total = 0.0
    for q in p["data"]:
        e = w["gate"] * M["prx_err"].get(q, 0) + w["idle"] * p_idle(q)
        total += e; parts.append(("data", q, e))
    for q in p["anc"]:
        e = (w["gate"] * M["prx_err"].get(q, 0) + w["ro"] * M["ro_err"].get(q, 0)
             + w["qnd"] * qnd_fail(q) + w["idle"] * p_idle(q))
        total += e; parts.append(("anc", q, e))
    for ed in p["edges"]:
        e = w["cz"] * M["cz_err"].get(tuple(sorted(ed)), 0)
        total += e; parts.append(("cz", ed, e))
    # bottleneck = single largest physical error rate present in the patch
    bottleneck = max(
        [M["prx_err"].get(q, 0) for q in p["data"] + p["anc"]]
        + [M["ro_err"].get(q, 0) for q in p["anc"]]
        + [qnd_fail(q) for q in p["anc"]]
        + [M["cz_err"].get(tuple(sorted(ed)), 0) for ed in p["edges"]]
    )
    return total, bottleneck, parts


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("calibration")
    ap.add_argument("--t-round-us", type=float, default=1.0)
    args = ap.parse_args()

    M, label = load_metrics(args.calibration)
    edges, adj, cr = build_device(M)
    t_round = args.t_round_us * 1e-6

    print(f"Device {label}: {len(cr)} qubits, {len(edges)} CZ couplers, "
          f"degree dist {dict(sorted(Counter(len(adj[q]) for q in cr).items()))}")

    cm = coupling_map_qiskit(edges)
    json.dump({"qubit_labels": [f"QB{i+1}" for i in range(54)],
               "n_qubits": 54, "coupling_map_0indexed": cm,
               "coupling_map_qbnames": [[f"QB{a}", f"QB{b}"] for a, b in sorted(edges)]},
              open("emerald_coupling_map.json", "w"), indent=1)

    # qubit scores table
    rows = []
    for q in sorted(cr):
        q0, q1 = M["qnd0"].get(q), M["qnd1"].get(q)
        qf = 1 - min(q0, q1) if (q0 and q1) else None
        us = lambda d: (round(d[q]*1e6, 2) if q in d else None)
        rows.append(dict(qubit=f"QB{q}", prx_err=M["prx_err"].get(q),
                         clifford1_err=M["clifford1_err"].get(q),
                         readout_err=M["ro_err"].get(q), qnd_fail=qf,
                         repeatability=M["repeat"].get(q),
                         t1_us=us(M["t1"]), t2_us=us(M["t2"]), t2e_us=us(M["t2e"])))
    json.dump(rows, open("emerald_qubit_scores.json", "w"), indent=1)

    best = {}
    for d in (3, 5):
        lat, nodes, tedges = surface_template(d)
        pls = find_placements(lat, nodes, tedges, edges, cr)
        scored = []
        for p in pls:
            tot, bot, parts = score_patch(p, M, t_round)
            scored.append((tot, bot, p, parts))
        scored.sort(key=lambda r: r[0])
        best[d] = scored
        print(f"\n=== distance d={d}  ({2*d*d-1} qubits, {len(tedges)} CZ/round) ===")
        print(f"zero-SWAP placements found: {len(scored)}")
        if scored:
            tot, bot, p, parts = scored[0]
            print(f"BEST patch  total_round_error={tot*100:.2f}%  bottleneck={bot*100:.2f}%")
            print(f"  data ({len(p['data'])}): {', '.join('QB%d'%q for q in p['data'])}")
            print(f"  ancilla ({len(p['anc'])}): {', '.join('QB%d'%q for q in p['anc'])}")
            top3 = sorted(parts, key=lambda r: -r[2])[:3]
            print("  worst contributors:",
                  "; ".join(f"{t}:{(('QB%d'%i) if isinstance(i,int) else 'QB%d-QB%d'%i)}={e*100:.2f}%"
                            for t, i, e in top3))
            # save best patches
            json.dump({"distance": d, "total_round_error": tot, "bottleneck": bot,
                       "data_qubits": [f"QB{q}" for q in p["data"]],
                       "ancilla_qubits": [f"QB{q}" for q in p["anc"]],
                       "cz_pairs": [[f"QB{a}", f"QB{b}"] for a, b in p["edges"]],
                       "initial_layout_0indexed": {f"QB{q}": q-1 for q in p["data"]+p["anc"]}},
                      open(f"emerald_best_patch_d{d}.json", "w"), indent=1)
    return best


if __name__ == "__main__":
    main()
