# Memo: ZBE Project — Findings and Proposed Direction

**To:** [Supervisors]
**From:** [Author]
**Date:** March 2026
**Re:** Null results on initial hypotheses; proposed pivot to non-compliance paper

---

## 1. Background

The initial project aimed to study Spain's Low-Emission Zone (ZBE) mandate
through the lens of Colantone et al.'s work on the political costs of
environmental regulation. The 2021 Climate Change Law (Ley 7/2021) requires
all municipalities above 50,000 inhabitants to implement ZBEs, creating a
sharp population threshold suitable for a regression discontinuity design.

**Original hypotheses:**
- (H1) The ZBE mandate increased support for Vox (populist right) in
  obligated municipalities (electoral backlash, following Colantone et al.)
- (H2) The mandate shifted vehicle fleet composition toward cleaner vehicles
  in obligated municipalities (anticipatory compliance)

---

## 2. What I found — and why both hypotheses fail

### 2.1 Electoral backlash (H1): Null

The RD at the 50k threshold yields no effect on Vox vote share (2019-2023).
The reason is straightforward: the treatment never happened. Of ~150
obligated municipalities, only 18-19 had implemented any form of ZBE by the
May 2023 elections. Near the 50k threshold specifically, compliance was
essentially zero. There is no first stage.

A DiD among large cities (comparing implementers vs. non-implementers among
>50k municipalities) shows a suggestive positive effect on Vox growth in
left-governed cities with enforced ZBEs, but this is driven entirely by
Barcelona metro catching up from a near-zero Vox base — a floor effect, not
a treatment effect. N=17 implementers, of which 10 are in the Barcelona
metropolitan area under the same policy umbrella.

### 2.2 Fleet composition (H2): Null

The RD on vehicle environmental labels (share of "sin distintivo" / no-label
vehicles) shows zero discontinuity at 50k in any year from 2017 to 2024.
The difference-in-RD (comparing pre-mandate 2017-2020 vs. post-mandate
2021-2024) is 0.003 (p=0.894). The mandate did not induce even anticipatory
fleet adjustment at the threshold. Covariate balance and density tests are
clean — the design is valid, the effect is simply absent.

### 2.3 Governing party (supplementary): Also null

I hand-coded the governing party (2019-2023 term) for all >50k
municipalities and tested whether left vs. right predicts ZBE adoption.
It does not (OR=2.57, p=0.16). City size is the only significant predictor
(OR=3.61, p<0.001). Both left and right blocs delayed equally — 5 left-
governed and 5 right-governed cities are in the "explicitly delayed" category.
Among the few implementers, stringency is similar across blocs.

### 2.4 Why the Colantone framework doesn't apply here

Colantone et al. study settings where regulation is actually imposed and
economically costly. In Spain, the ZBE mandate was:
- Not enforced (no penalties for non-compliance in the law)
- Not implemented (82% of obligated cities did nothing)
- Not binding near the identification threshold (zero compliance at 50k)

You cannot study the political cost of a regulation that was never applied.

---

## 3. What IS in the data — a non-compliance story

The null results on H1 and H2 point to a different and potentially more
interesting finding: **comprehensive non-compliance with a national
environmental mandate.**

### 3.1 The descriptive facts

| Period | Enforcement mechanism | Compliance rate |
|--------|----------------------|----------------|
| 2021-Jun 2023 | Legal mandate only, no sanctions | ~12% (18/151) |
| Mid 2024 | EU fund clawback threats begin | ~34% (58/151) |
| Jan 2026 | Transport subsidies withdrawn | Still rising |

- Of the 18 "compliant" cities, many merely relabeled pre-existing
  pedestrian zones or traffic-calmed areas as ZBEs (nominal compliance).
- Only ~10 cities had genuine label-based enforcement with cameras and fines
  (Madrid, Barcelona metro, and a handful of others).
- Compliance tripled once the central government threatened to claw back
  Next Generation EU funds (~EUR 1.5bn allocated) and withdraw public
  transport subsidies (Valencia lost EUR 14m/year).

### 3.2 Why this could be a paper

This setting speaks to several established literatures:

**Fiscal federalism / unfunded mandates** (Oates 1972, 2005; Rodden 2006):
The central government imposed a costly obligation on municipalities without
providing funding, enforcement capacity, or political cover. Classic
vertical externality — the benefits of clean air are diffuse and long-term,
while the political costs of restricting cars are local and immediate.

**EU compliance gap** (Falkner et al. 2005; Treib 2014; Bondarouk &
Mastenbroek 2018): Spain's ZBE non-compliance mirrors the broader EU
pattern where member states transpose directives into law but fail to
implement them. This extends that literature to the *subnational* level —
Spain transposed the EU clean air objectives into national law, but
municipalities refused to implement.

**Fiscal conditionality and enforcement** (Scharpf 1988; Becker et al.
2010): The shift from legal mandate (ignored) to fiscal conditionality
(effective) provides a clean within-mandate comparison of enforcement
mechanisms. EU structural funds as an enforcement lever for environmental
policy.

**Political economy of environmental regulation** (Colantone et al. 2024;
Dolphin & Ivanova 2022): Rather than studying electoral backlash *from*
regulation, we study why regulation *fails to be imposed* — the anticipated
electoral cost is sufficient to deter implementation even without actual
voter reaction.

### 3.3 Proposed paper structure

> **"Why Mandates Fail: Low-Emission Zones and the Politics of
> Non-Compliance in Spain"**

1. **Institutional background**: Climate law, ZBE mandate, 50k threshold
2. **Measuring compliance**: Original hand-coded ZBE status for all 151
   cities (enforced / nominal / delayed / none) — descriptive contribution
3. **The threshold had no bite**: RD on fleet composition shows zero effect
   (Section 2.2 above). Cleanest empirical result.
4. **What predicts compliance?** Not party; only city size. Logit analysis.
5. **Why mandates fail without enforcement**: Three mechanisms — no
   sanctions, local electoral costs, coordination failure among peers
6. **Fiscal conditionality works**: Compliance tripled after EU fund
   clawback threats. Potential pre/post analysis if 2025 fleet data becomes
   available.

### 3.4 What additional data would strengthen this

- **2025 DGT fleet data** (expected release ~mid 2026): Would allow testing
  whether cities that complied under fiscal pressure show fleet composition
  changes. This would complete the story.
- **Municipality-level EU fund allocations**: Which cities received Next
  Generation funds for ZBE implementation and how much. Available from
  Ministerio de Transportes.
- **Detailed compliance timeline**: Exact activation dates for each city's
  ZBE. Partially available from MITECO's ZBE map.

---

## 4. Questions for you

1. **Is the non-compliance angle worth pursuing?** It pivots away from
   Colantone-style electoral backlash toward fiscal federalism / EU
   compliance. Is this within the scope of what we want to do?

2. **Target outlet?** This could fit Journal of Public Economics, JEEM,
   European Journal of Political Economy, or more policy-oriented outlets
   like JPART or Regulation & Governance.

3. **Should I invest in collecting the additional data** (EU fund
   allocations, detailed compliance timeline), or is the current evidence
   sufficient for a first draft?

4. **Is there value in the null RD results alone?** The fleet composition
   RD is clean and well-powered — a null result on a major national mandate
   is informative. But it needs the non-compliance framing to be publishable.

---

## Appendix: Summary of completed analyses

| Script | Analysis | Key result |
|--------|----------|------------|
| 11 | DiD: ZBE implementers vs non-implementers (Vox) | Suggestive but driven by Barcelona floor effect |
| 12 | Party politics of ZBE adoption | Null — party does not predict adoption |
| 13 | RD: Fleet composition at 50k threshold | Null — zero discontinuity, all years |

All code, data, and outputs are in the repository.
