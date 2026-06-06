"""
emerald_qec_sim.py
==================
Build a *calibration-grounded* noisy surface-code memory circuit for the
recommended d=3 patch on IQM Emerald, decode it with PyMatching, and estimate
the logical error rate (LER) per QEC round.

Noise is heterogeneous and taken directly from the calibration JSON:
  - every CZ (CX->CZ) gets DEPOLARIZE2 with that coupler's measured infidelity,
  - every 1q gate gets DEPOLARIZE1 with that qubit's PRX infidelity,
  - every ancilla / final data measurement gets an X_ERROR readout flip,
  - data qubits decohere during each measurement window via a T1/T2 Pauli channel.

Avg-infidelity -> depolarizing-probability conversions: p2 = r*16/15 (2q),
p1 = r*4/3 (1q). Idle channel: pX=pY=(1-e^{-t/T1})/4, pZ=(1-e^{-t/Tphi})/2.
"""
from __future__ import annotations
import math, json, argparse
import numpy as np
import stim, pymatching
import emerald_patch_finder as E


def recommended_patch(M, edges, cr):
    BLACK = {q for q in cr if (M['prx_err'].get(q, 0) > 0.005 or M['ro_err'].get(q, 0) > 0.10
             or M['t1'][q] < 18e-6 or (M['t2e'].get(q, 1) < 5e-6) or (M['t2'].get(q, 1) < 5e-6))}
    def p_idle(q, t=1e-6):
        T1 = M['t1'].get(q, 1e-3); T2 = M['t2e'].get(q) or M['t2'].get(q) or 1e-3
        return 1 - math.exp(-t * (1/T1 + 1/T2))
    lat, nodes, tedges = E.surface_template(3)
    cands = []
    for p in E.find_placements(lat, nodes, tedges, edges, cr):
        qs = p['data'] + p['anc']
        if any(q in BLACK for q in qs):
            continue
        wc = max(M['cz_err'].get(tuple(sorted(e)), 0) for e in p['edges'])
        wr = max(M['ro_err'].get(q, 0) for q in p['anc'])
        tot = (sum(M['prx_err'].get(q, 0) for q in qs)
               + sum(M['ro_err'].get(q, 0) for q in p['anc'])
               + sum(M['cz_err'].get(tuple(sorted(e)), 0) for e in p['edges'])
               + sum(p_idle(q) for q in qs))
        cands.append((round(max(wc, wr), 4), tot, p))
    cands.sort(key=lambda r: (r[0], r[1]))
    return cands[0][2], BLACK


def idle_pauli(T1, T2, t):
    pad = 1 - math.exp(-t / T1)                       # relaxation
    inv_tphi = max(1e-9, 1/T2 - 1/(2*T1))
    pz = 0.5 * (1 - math.exp(-t * inv_tphi))          # pure dephasing
    px = py = pad / 4.0
    return max(px, 0), max(py, 0), max(pz, 0)


def make_noisy(distance, rounds, stim2em, M, t_round, uniform=None):
    """uniform=None -> calibration noise; else dict(cz,ro,t1,t2,prx) for a flat baseline."""
    clean = stim.Circuit.generated("surface_code:rotated_memory_z",
                                    distance=distance, rounds=rounds)
    coords = clean.get_final_qubit_coordinates()
    lat = {q: (int((coords[q][0]+coords[q][1])//2), int((coords[q][0]-coords[q][1])//2))
           for q in coords}
    # data qubits = those not measured every round; detect from MR targets
    mr = set()
    for inst in clean.flattened():
        if inst.name in ("MR", "MRZ", "MRX"):
            mr |= {t.value for t in inst.targets_copy()}
    data_idx = [q for q in coords if q not in mr]

    def cz_p(a, b):
        r = uniform['cz'] if uniform else M['cz_err'].get(tuple(sorted((stim2em[a], stim2em[b]))), 0)
        return min(0.75, r * 16/15)

    def g1_p(q):
        r = uniform['prx'] if uniform else M['prx_err'].get(stim2em[q], 0)
        return min(0.75, r * 4/3)

    def ro_p(q):
        return uniform['ro'] if uniform else M['ro_err'].get(stim2em[q], 0)

    def idle_p(q):
        if uniform:
            T1, T2 = uniform['t1'], uniform['t2']
        else:
            T1 = M['t1'].get(stim2em[q], 1e-3); T2 = M['t2e'].get(stim2em[q]) or 1e-3
        return idle_pauli(T1, T2, t_round)

    noisy = stim.Circuit()
    for inst in clean.flattened():
        nm = inst.name
        targs = [t.value for t in inst.targets_copy()] if inst.name not in ("DETECTOR", "OBSERVABLE_INCLUDE", "QUBIT_COORDS") else None
        # ---- noise BEFORE measurements ----
        if nm in ("M", "MR", "MZ", "MRZ"):
            for q in targs:
                noisy.append("X_ERROR", [q], ro_p(q))
        if nm in ("MR", "MRZ", "MRX"):       # ancilla round-measurement => data idles now
            for q in data_idx:
                px, py, pz = idle_p(q)
                noisy.append("PAULI_CHANNEL_1", [q], [px, py, pz])
        # ---- the operation itself ----
        noisy.append(inst)
        # ---- noise AFTER gates ----
        if nm == "CX":
            for i in range(0, len(targs), 2):
                noisy.append("DEPOLARIZE2", [targs[i], targs[i+1]], cz_p(targs[i], targs[i+1]))
        elif nm in ("H", "S", "SQRT_X", "SQRT_X_DAG", "SQRT_Y", "X", "Y", "Z"):
            for q in targs:
                noisy.append("DEPOLARIZE1", [q], g1_p(q))
    return noisy


def ler(noisy, shots, seed=0):
    dem = noisy.detector_error_model(decompose_errors=True)
    mtch = pymatching.Matching.from_detector_error_model(dem)
    sampler = noisy.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(shots, separate_observables=True)
    pred = mtch.decode_batch(det)
    fails = int(np.sum(pred[:, 0] != obs[:, 0]))
    return fails / shots, fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("calibration")
    ap.add_argument("--t-round-us", type=float, default=1.0)
    ap.add_argument("--shots", type=int, default=200_000)
    args = ap.parse_args()

    M, label = E.load_metrics(args.calibration)
    edges, adj, cr = E.build_device(M)
    patch, BLACK = recommended_patch(M, edges, cr)
    stim2em = patch['mapping']
    t_round = args.t_round_us * 1e-6

    print(f"Device {label} | recommended d=3 patch, zero SWAPs")
    print("  data:", ", ".join("QB%d" % q for q in patch['data']))
    print("  anc :", ", ".join("QB%d" % q for q in patch['anc']))

    # median baseline for context
    med = lambda d: float(np.median(list(d.values())))
    uni = dict(cz=med(M['cz_err']), ro=med(M['ro_err']), prx=med(M['prx_err']),
               t1=med(M['t1']), t2=med(M['t2e']))
    print(f"\nt_round={args.t_round_us} us, shots={args.shots}")
    print(f"{'rounds':>7}{'  pL_calibration':>18}{'  pL_uniform(median)':>22}")
    Rs = [1, 3, 5, 7, 9]
    pL_cal = []
    for R in Rs:
        nc = make_noisy(3, R, stim2em, M, t_round)
        nu = make_noisy(3, R, stim2em, M, t_round, uniform=uni)
        pc, fc = ler(nc, args.shots, seed=R)
        pu, fu = ler(nu, args.shots, seed=R+100)
        pL_cal.append(pc)
        se = lambda p, n: math.sqrt(max(p*(1-p), 1/n)/n)
        print(f"{R:>7}{pc*100:>14.3f}% ±{se(pc,args.shots)*100:.3f}{pu*100:>16.3f}% ±{se(pu,args.shots)*100:.3f}")

    # per-round LER fit:  1-2pL = (1-2eps)^R
    R_arr = np.array(Rs, float)
    y = np.log(np.clip(1 - 2*np.array(pL_cal), 1e-9, 1))
    slope = np.dot(R_arr, y) / np.dot(R_arr, R_arr)          # through origin
    eps = 0.5 * (1 - math.exp(slope))
    print(f"\nFitted per-round logical error rate (calibration noise): {eps*100:.3f}% per round")
    json.dump({"distance": 3, "t_round_us": args.t_round_us, "shots": args.shots,
               "rounds": Rs, "pL_calibration": pL_cal,
               "per_round_LER": eps,
               "data_qubits": ["QB%d" % q for q in patch['data']],
               "ancilla_qubits": ["QB%d" % q for q in patch['anc']]},
              open("emerald_d3_ler.json", "w"), indent=1)
    print("saved emerald_d3_ler.json")


if __name__ == "__main__":
    main()
