#!/usr/bin/env python3
"""
Repetition code on IQM Emerald's best low-error qubit CHAIN.

MULTI-ROUND (rounds = d): errors accumulate over rounds, so the logical error is
measurable and we can extract the logical error PER ROUND and show SUPPRESSION
(per-round error dropping as distance grows) -- the textbook "QEC works" result.
Multi-round also breaks the single-round degeneracy, so the number is rigorous.

    python rep_code_emerald.py check     # noiseless sanity at rounds=d (Aer), no hardware
    python rep_code_emerald.py run       # real Emerald runs (spends credits)
"""
import os, sys, json
import numpy as np, stim, pymatching
from collections import defaultdict
from surface_code import stim_to_qiskit

def _calib_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in (os.path.join(here, "calib"), os.path.join(here, "files"),
              os.path.expanduser("~/Desktop/qpufolder/kazulak_thomas/files")):
        if os.path.exists(os.path.join(c, "emerald_coupling_map.json")):
            return c
    raise FileNotFoundError("emerald_coupling_map.json / emerald_qubit_scores.json not found "
                            "(put them in a 'calib/' folder next to this script).")


CALIB_DIR = _calib_dir()
DISTANCES = [3, 5, 7, 9]
SHOTS = 50000
NOISE = dict(after_clifford_depolarization=0.01,
             before_measure_flip_probability=0.01,
             after_reset_flip_probability=0.01)
BAD = {"QB9", "QB25", "QB41", "QB46", "QB47"}


def rounds_for(d):
    return d                       # matched experiment: distance d, d rounds


def load_calibration():
    cmap = json.load(open(f"{CALIB_DIR}/emerald_coupling_map.json"))
    labels = cmap["qubit_labels"]
    name2idx = {lab: i for i, lab in enumerate(labels)}
    adj = defaultdict(set)
    for a, b in cmap["coupling_map_0indexed"]:
        adj[a].add(b); adj[b].add(a)
    cost = {}
    for s in json.load(open(f"{CALIB_DIR}/emerald_qubit_scores.json")):
        c = s["readout_err"] + 2 * s["clifford1_err"] + s["prx_err"] + 0.5 * s["qnd_fail"]
        cost[name2idx[s["qubit"]]] = 1e9 if s["qubit"] in BAD else c
    return adj, cost, len(labels)


def best_chain(L, adj, cost, n):
    best, best_cost = None, 1e18
    for start in range(n):
        if cost[start] >= 1e9:
            continue
        path, used, tot = [start], {start}, cost[start]
        for _ in range(L - 1):
            nbrs = [(cost[q], q) for q in adj[path[-1]] if q not in used and cost[q] < 1e9]
            if not nbrs:
                break
            c, q = min(nbrs); path.append(q); used.add(q); tot += c
        if len(path) == L and tot < best_cost:
            best, best_cost = path, tot
    return best


def counts_to_raw(counts, nm, shots):
    raw = np.zeros((shots, nm), bool); r = 0
    for bits, c in counts.items():
        v = bits.replace(" ", "")[::-1]
        row = np.array([x == "1" for x in v[:nm]], bool)
        for _ in range(c):
            raw[r] = row; r += 1
    return raw[:r]


def decode(raw, d, rounds):
    noisy = stim.Circuit.generated("repetition_code:memory", distance=d, rounds=rounds, **NOISE)
    det, obs = noisy.compile_m2d_converter().convert(measurements=raw, separate_observables=True)
    y = obs[:, 0].astype(int)
    m = pymatching.Matching.from_detector_error_model(
        noisy.detector_error_model(decompose_errors=True))
    pred = np.asarray(m.decode_batch(det), np.uint8).reshape(-1)[:len(y)]
    return float(y.mean()), float(np.mean(pred != y))


def per_round(ler, rounds):
    """logical error per round from total: P=(1-(1-2eps)^R)/2."""
    f = max(1e-12, 1.0 - 2.0 * ler)
    return (1.0 - f ** (1.0 / rounds)) / 2.0


def check():
    from qiskit_aer import AerSimulator
    from qiskit import transpile
    sim = AerSimulator()
    print("NOISELESS gate check at rounds=d (conversion must give LER=0):")
    ok = True
    for d in DISTANCES:
        r = rounds_for(d)
        exec_c = stim.Circuit.generated("repetition_code:memory", distance=d, rounds=r)
        qc, *_ = stim_to_qiskit(exec_c)
        counts = sim.run(transpile(qc, sim), shots=2000).result().get_counts()
        raw = counts_to_raw(counts, exec_c.num_measurements, 2000)
        _, ler = decode(raw, d, r)
        ok &= (ler == 0)
        print(f"  d={d} rounds={r} ({2*d-1} qubits): noiseless LER={ler:.4f} "
              f"-> {'PASS' if ler == 0 else 'FAIL'}")
    print("ALL PASS -- safe to run on hardware." if ok else "FIX CONVERSION before hardware.")


def run():
    from iqm.qiskit_iqm import IQMProvider
    from qiskit import transpile
    assert os.environ.get("IQM_TOKEN"), "export IQM_TOKEN"
    adj, cost, n = load_calibration()
    backend = IQMProvider("https://resonance.meetiqm.com",
                          quantum_computer="emerald").get_backend()
    results = []
    for d in DISTANCES:
        r = rounds_for(d)
        chain = best_chain(2 * d - 1, adj, cost, n)
        if chain is None:
            print(f"  d={d}: no clean chain, skipping"); continue
        exec_c = stim.Circuit.generated("repetition_code:memory", distance=d, rounds=r)
        qc, *_ = stim_to_qiskit(exec_c)
        qct = transpile(qc, backend, initial_layout=chain, optimization_level=3)
        counts = backend.run(qct, shots=SHOTS).result().get_counts()
        raw = counts_to_raw(counts, exec_c.num_measurements, SHOTS)
        np.savez(f"rep_mr_d{d}_shots.npz", raw=raw, chain=np.array(chain), rounds=r)
        und, ler = decode(raw, d, r)
        eps = per_round(ler, r)
        results.append((d, r, und, ler, eps))
        print(f"  d={d:2d} rounds={r:2d} ({len(chain):2d}q) | undecoded {und*100:6.2f}% | "
              f"MWPM total {ler*100:6.3f}% | per-round {eps*100:7.4f}%")
    print("\n=== SUPPRESSION (logical error PER ROUND should DROP with distance) ===")
    for d, r, und, ler, eps in results:
        print(f"  d={d}: {eps*100:.4f}% / round")
    for i in range(len(results) - 1):
        e0, e1 = results[i][4], results[i + 1][4]
        if e1 > 0:
            print(f"  Lambda(d={results[i][0]}->{results[i+1][0]}) = {e0/e1:.2f}x  "
                  f"({'suppressing' if e0 > e1 else 'NOT suppressing'})")
    try:
        import matplotlib.pyplot as plt
        ds = [x[0] for x in results]; eps = [x[4] * 100 for x in results]
        plt.figure(figsize=(5, 3.5)); plt.semilogy(ds, eps, "o-")
        plt.xlabel("code distance d"); plt.ylabel("logical error per round (%)")
        plt.title("Repetition code suppression on IQM Emerald")
        plt.grid(True, which="both", alpha=0.3); plt.tight_layout()
        plt.savefig("rep_code_suppression.png", dpi=130)
        print("saved rep_code_suppression.png")
    except Exception as e:
        print("plot skipped:", e)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    (check if mode == "check" else run)()
