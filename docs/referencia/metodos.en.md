# Assignment Methods and Operational Scope

This page details the traffic assignment methods available in **Desire Lines**, the conceptual differences between the synthetic-network and real-network approaches, the approximate Level of Service (LOS) classification, the scope limitations in urban areas, and the performance envelope of the assignment engine.

---

## 1. Traffic Assignment Methods

The plugin provides three main methods for assigning traffic onto road networks (defined in the [`traffic/assignment.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/assignment.py) module): **All-or-Nothing (AoN)**, **Method of Successive Averages equilibrium (MSA + BPR)** and **Frank-Wolfe equilibrium (FW + BPR)** (the recommended default method).

### 1.1 All-or-Nothing (AoN)

The **All-or-Nothing (AoN)** method assigns 100% of the demand of each Origin/Destination (OD) pair to the shortest path in free-flow time (`t0`), computed with Dijkstra's algorithm.

* **Mechanism**: Single pass (1 iteration). It does not account for the speed degradation or the increase in travel time caused by congestion.
* **Computational cost**: **Low** (a single Dijkstra pass per origin; equilibrium methods repeat that pass at every iteration — 100 by default in the panel).
* **Interpreting the `v/c` ratio**: Since travel times are not updated in AoN, the computed capacity serves only for later evaluation. If the volume/capacity ratio is greater than 1.0 (`v/c > 1`), **this is a direct diagnosis of overload/physical capacity deficit** on the road segment, and **not** a system equilibrium state.

#### When to use AoN:
* **Quick diagnosis of potential demand**: To identify the main travel desire corridors before applying capacity constraints.
* **Networks with little route competition**: When the network topology offers few or no relevant alternative routes between origins and destinations.
* **Demand far below capacity**: In low-volume rural networks, where congestion is negligible and `v/c` stays well below 1.
* **Baseline**: As a reference scenario to compare against the saturated FW or MSA equilibrium.

---

### 1.2 MSA + BPR Equilibrium (Method of Successive Averages)

The **MSA equilibrium** method iteratively distributes traffic taking into account the effect of congestion on travel times, using the *Bureau of Public Roads* (BPR) impedance equation.

* **Iterative mechanism**: At each iteration `k` (`k` = 1, 2, ..., N):
    1. The travel times `t_a` of each arc `a` are recomputed with the BPR curve:
       `t_a = t0_a * [1 + alfa * (v_a / C_a) ^ beta]`
       where `t0_a` is the free-flow time, `v_a` is the current volume, `C_a` is the per-direction capacity, and `alfa` and `beta` are the BPR parameters (per link or global, default: `alfa = 0.15`, `beta = 4.0`).
    2. A full AoN loading is performed on the new times `t_a`, producing auxiliary volumes `y_a^(k)`.
    3. The accumulated flow is updated by combining the previous result with the auxiliary one through successive averaging with a fixed step of $1/k$:
       `v_a^(k) = v_a^(k-1) + (1 / k) * (y_a^(k) - v_a^(k-1))`
* **Convergence**: Assignment progress is monitored through the **iteration relative gap**:
  $$\text{gap} = \frac{|\sum_a t_a v_a - \sum_a t_a y_a|}{\sum_a t_a v_a}$$
* **Computational cost**: **Moderate**, but with slow asymptotic convergence due to the fixed $1/k$ step, requiring hundreds to thousands of iterations to reach gaps below 0.001.

---

### 1.3 Frank-Wolfe + BPR Equilibrium (Default Algorithm)

The **Frank-Wolfe (FW)** method is the classic, well-established algorithm for solving Wardrop's User Equilibrium problem under Beckmann's mathematical formulation. It is the **default method** in Desire Lines for equilibrium assignment.

* **Iterative mechanism**:
    1. **Initialization**: Runs an initial AoN loading at the free-flow times `t0`, defining the base $v^{(1)}$.
    2. At each iteration `k` (`k` = 2, ..., N):
        - Recomputes the current BPR times $t_a(v_a)$.
        - Runs an auxiliary AoN loading with $t_a$, obtaining the descent direction $y_a$.
        - Evaluates the **relative gap**. If $0 \le \text{gap} \le \text{gap\_tol}$, it stops early due to convergence.
        - **Optimal line search**: Determines the step size $\lambda \in [0, 1]$ that minimizes Beckmann's objective function along the direction $(y - v)$, solving the derivative by **bisection** (30 evaluations):
          $$\frac{d}{d\lambda} \sum_a \int_0^{v_a + \lambda(y_a - v_a)} t_a(w)\,dw = \sum_a t_a(v_a + \lambda(y_a - v_a)) \cdot (y_a - v_a) = 0$$
        - Updates the volumes with the optimal step:
          $$v_a^{(k)} = v_a^{(k-1)} + \lambda \cdot (y_a - v_a^{(k-1)})$$
* **Default convergence parameters**:
    - **Maximum iterations**: **100** (configurable up to 5000 in the panel).
    - **Relative gap tolerance**: **0.001**.
* **Computational cost**: **Excellent**. Each iteration requires the same Dijkstra pass as MSA, but computing the optimal $\lambda$ speeds up the approach to equilibrium: on Sioux Falls, the same relative gap is reached with about 6 to 7× fewer iterations (FW 50 it: gap 0.0031; MSA only reaches that gap at iteration 297, and the gap of FW 100 it, 0.0014, is not reached by MSA within 300 iterations; and gap < 0.001 at iteration 132 for FW versus 915 for MSA).

---

### 1.4 When to use Frank-Wolfe vs. MSA

| Criterion | Frank-Wolfe + BPR (Recommended) | MSA + BPR |
|---|---|---|
| **Convergence speed** | **Fast**: mean error < 0.5% at 100 iterations; on Sioux Falls, gap < 0.001 from iteration 132 | **Slow**: with the $1/k$ step, on Sioux Falls the gap only drops below 0.001 at iteration 915 |
| **Update step** | Optimal ($\lambda$ via line search on Beckmann's function) | Predetermined ($1/k$) |
| **Usage recommendation** | **First choice** for any planning study, traffic modelling and real projects | Academic/teaching use, historical comparisons, or as a baseline for methods without line search |

---

## 2. Comparison of Methods in Desire Lines

| Feature | Synthetic AoN (Delaunay — Tab 3) | Highway AoN (Tab 4) | MSA + BPR (Tab 4) | Frank-Wolfe + BPR (Tab 4) |
|---|---|---|---|---|
| **Network type** | **Synthetic** (Delaunay triangulation between centroids) | **Real** (SNV/DER road network via GISBR) | **Real** (SNV/DER road network via GISBR) | **Real** (SNV/DER road network via GISBR) |
| **Passes / Iterations** | Single pass (1-shot) | Single pass (1-shot) | Iterative (1/k step, default 100 it) | Iterative (optimal step λ, default 100 it) |
| **Considers capacity?** | No (abstract network with no physical attributes) | Yes (computes HCM, but does not feed back time) | Yes (computes HCM and feeds back times via BPR) | Yes (computes HCM and feeds back times via BPR) |
| **Route redistribution?** | No | No | Yes (redistributes traffic with a 1/k step) | Yes (redistributes traffic with an optimal step) |
| **Interpreting `v/c > 1`** | N/A | Diagnosis of local overload | Tendency toward equilibrium | Tendency toward rigorous equilibrium |
| **Performance / Convergence** | Instantaneous | One pass (equilibrium: one per iteration) | Moderate (slow asymptotic convergence) | Fast and accurate (accelerated convergence) |

---

## 3. Approximate Level of Service (LOS) Classification

The HCM **Level of Service (LOS)** ranges formally from **A** (best operating condition) to **F** (breakdown/severe congestion).

### Approximation by `v/c` Ranges (Decision D3)

In the HCM 6th Edition, rigorous determination of LOS requires traffic density (pc/km/lane) or percent time spent following (*PTSF*), parameters that need continuous counts and field measurements not available in the national SNV registry.

In compliance with **Decision D3**, Desire Lines reports LOS based strictly on **ranges of the Volume/Capacity (`v/c`) ratio**, as shown in the table below:

| Level of Service (LOS) | `v/c` range | Operating condition identified |
|:---:|:---:|---|
| **A** | `v/c <= 0.35` | **Free flow**: Vehicles travel without speed restrictions; manoeuvres are completely free. |
| **B** | `0.35 < v/c <= 0.55` | **Stable flow**: Minor restrictions on speed and manoeuvrability. |
| **C** | `0.55 < v/c <= 0.75` | **Controlled stable flow**: Speed affected by traffic volume; occasional delays. |
| **D** | `0.75 < v/c <= 0.90` | **Approaching saturation**: Severe restrictions on manoeuvring; small fluctuations in demand cause queues. |
| **E** | `0.90 < v/c <= 1.00` | **Capacity**: Operation at the road's capacity limit; unstable flow. |
| **F** | `v/c > 1.00` | **Overload / Breakdown**: Demand exceeds capacity; bottlenecks and long queues form. |

!!! warning "Approximation note"
    LOS computed from `v/c` ranges is a quick visual diagnostic indicator for highlighting bottlenecks in the road network. It does not replace the detailed HCM field procedures when detailed data are available.

---

## 4. Operational Scope and Urban Flagging

### 4.1 Highway-Only Scope (Decision D2)

The Desire Lines capacity calculation module was developed specifically for **rural and intercity highways**:

* **Two-lane highways**: Full procedure according to **HCM 6th Edition, Chapter 15**.
* **Multilane highways and freeways**: Full procedure according to **HCM 6th Edition, Chapter 12**.

**Out of scope**: Signalized intersections, urban crossings, roundabouts, ramps and weaving sections (HCM Chapters 16 to 19). The official SNV/DNIT dataset does not provide urban operational parameters (such as signal cycle lengths, phasing and distances between intersections), which makes rigorous application of the urban HCM impossible without inventing data.

### 4.2 Warning and Flagging of Urban Crossings (Decision D11)

On urban-crossing segments integrated into the highway network, the actual capacity of the road is governed by signal controls and intersections, not by the geometric characteristics of the segment. Applying the highway formula to these segments **overestimates the actual capacity of the urban road**.

To handle this limitation with full transparency:

1. **Connectivity preserved**: The plugin **does not remove** urban crossings from the graph, preserving the integrity of the shortest transport paths.
2. **Scope flagging**: Each urban arc processed is tagged with the attribute `escopo = 'urbano'` (while the others receive `escopo = 'rodoviario'`).
3. **Log warning**: When the capacity calculation and assignment finish, the plugin log explicitly reports the number of urban segments that were processed with the highway approximation.
4. **Filtering by the analyst**: The analyst can use the `escopo` field to isolate or filter urban segments in reports and cartographic post-processing.

---

## 5. Performance Envelope (Decision D4)

To work around the performance limitations of QGIS's native C++ network engine — which does not allow arc costs to be updated in place without rebuilding the whole graph at every equilibrium iteration — Desire Lines uses its own **pure-Python graph engine** ([`traffic/graph.py`](https://github.com/d-camargo/desire_lines/blob/main/desire_lines/traffic/graph.py)).

### Processing Capabilities and Limits

* **Recommended network size**: Comfortable for networks with up to **~50,000** directed arcs.
* **Equilibrium iterations**: Excellent performance with the default of **100 iterations** of Frank-Wolfe or MSA on state-level and regional study areas.
* **Dijkstra per origin**: The shortest-path search runs **once per unique origin** (not per individual OD pair), drastically reducing total processing time.
* **AoN speed-up**: Since All-or-Nothing assignment performs only a single Dijkstra pass, it is proportionally faster than the equilibrium methods, which repeat that pass at every iteration (up to **100** by default), making it possible to process larger networks in a few seconds.

---

## 6. Validation on Sioux Falls

The accuracy of the Desire Lines traffic assignment engine was validated using the classic **Sioux Falls** benchmark ([bstabler/TransportationNetworks](https://github.com/bstabler/TransportationNetworks)), made up of 24 zones, 76 directed links, 528 OD pairs with positive demand (360,600 trips in total) and a reference Total System Travel Time (TSTT) of **7,480,225** (under the BPR function with $\alpha = 0.15$ and $\beta = 4.0$).

The error is measured per link against the reference equilibrium flows (`SiouxFalls_flow.tntp`):
$$\text{error} = \frac{|v - v_{\text{ref}}|}{v_{\text{ref}}}$$

| Scenario | max. error | mean error | TSTT |
|---|---|---|---|
| TNTP inputs (cap/fft, one-way), MSA 10 it / gap 0.01 (**previous panel default**) | 69.6 % | 13.7 % | 9,342,350 |
| same, MSA 50 it | 16.9 % | 3.0 % | 7,770,932 |
| same, MSA 500 it (gap 1.8e-3) | 1.7 % | 0.30 % | 7,507,334 |
| same, MSA 2000 it (gap 4.7e-4) | 0.4 % | 0.07 % | 7,487,138 |
| same, **Frank-Wolfe** 50 / 100 / 300 it | 5.3 / 2.3 / 0.7 % | 0.96 / 0.46 / 0.14 % | 7,484,340 / 7,476,227 / 7,478,543 |
| TNTP cap/fft, but **each feature becomes two-way** | 73.6 % | 19.4 % | 3,743,234 |
| **What the plugin did before** (HCM cap, t0 = geometry ÷ 80 km/h, two-way, 10 it) | 177 % | 64.9 % | 714,504,749 |

### Validation Conclusions

1. **Superior convergence of Frank-Wolfe**: With **Frank-Wolfe at 300 iterations**, the engine reaches a mean error of only **0.14%** (maximum 0.7%) and a TSTT of 7,478,543, practically indistinguishable from the analytical reference (< 0.03% deviation). The new default of **100 iterations and gap 0.001** offers an excellent balance between speed and accuracy (mean error 0.46%).
2. **MSA performance**: MSA confirms correct asymptotic convergence (mean error 0.07% at 2000 iterations), but needs about 6 to 7× more iterations than Frank-Wolfe for the same relative gap (measured on Sioux Falls: FW 50 it ≈ MSA 297 it; gap < 0.001 in 132 it for FW and 915 it for MSA).
3. **Importance of supplied parameters and one-way links**: The main causes of divergence in calibrated networks are not the shortest-path algorithms, but imposing two-way operation where the road is one-way (`mao_unica`), or computing capacity/free-flow time with generic formulas when the real values are already known (`capacidade` and `tempo_livre`).
