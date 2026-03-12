# Memo: ZBE Project — Findings and Proposed Direction

**To:** [Supervisors]
**From:** Maurice
**Date:** March 2026
**Re:** Null results on initial hypotheses; proposed pivot to non-compliance paper

---

## 1. Background

The initial project aimed to study Spain's Low-Emission Zone (ZBE) mandate
through the lens of Colantone et al.'s (2024, APSR) work on the political
costs of environmental regulation — specifically their finding that Milan's
Area B congestion charge boosted Lega support. The 2021 Climate Change Law
(Ley 7/2021) requires all municipalities above 50,000 inhabitants to
implement ZBEs, creating a sharp population threshold suitable for a
regression discontinuity design.

**Original hypotheses:**
- (H1) The ZBE mandate increased support for Vox (populist right) in
  obligated municipalities — electoral backlash à la Colantone et al. (2024)
  and Stokes (2016) on renewable energy backlash
- (H2) The mandate shifted vehicle fleet composition toward cleaner vehicles
  in obligated municipalities — anticipatory compliance

---

## 2. What I found — and why both hypotheses fail

### 2.1 Electoral backlash (H1): Null

The RD at the 50k threshold yields no effect on Vox vote share (2019→2023).
The reason is straightforward: **the treatment never happened.** Of ~150
obligated municipalities, only 18–19 had implemented any form of ZBE by the
May 2023 elections. Near the 50k threshold specifically, compliance was
essentially zero. There is no first stage.

This contrasts sharply with the Colantone et al. setting where Milan's
Area B was actually enforced with cameras and fines. The Spanish mandate
created an *obligation* but not a *policy change* — a critical distinction
that Stokes (2020, *Short Circuiting*) would recognise as the difference
between policy adoption and policy implementation.

A DiD among large cities (comparing implementers vs. non-implementers among
>50k municipalities) shows a suggestive positive effect on Vox growth in
left-governed cities with enforced ZBEs, but this is driven entirely by
Barcelona metro catching up from a near-zero Vox base — a floor effect, not
a treatment effect. N=17 implementers, of which 10 are in the Barcelona
metropolitan area under the same AMB policy umbrella.

### 2.2 Fleet composition (H2): Null

The RD on vehicle environmental labels (share of "sin distintivo" / no-label
vehicles) shows zero discontinuity at 50k in any year from 2017 to 2024.
The difference-in-RD (comparing pre-mandate 2017–2020 vs. post-mandate
2021–2024) is +0.003 (p=0.894). The mandate did not induce even anticipatory
fleet adjustment at the threshold. Covariate balance and density tests are
clean — the design is valid, the effect is simply absent.

### 2.3 Governing party (supplementary): Also null

I hand-coded the governing party (2019–2023 term) for all >50k
municipalities and tested whether left vs. right predicts ZBE adoption.
It does not (OR=2.57, p=0.16). City size is the only significant predictor
(OR=3.61, p<0.001). Both left and right blocs delayed equally — 5 left-
governed and 5 right-governed cities are in the "explicitly delayed" category.
Among the few implementers, stringency is similar across blocs.

### 2.4 Why the Colantone framework doesn't apply here

Colantone et al. (2024) and the related literature on political costs of
climate policy — Stokes (2016) on wind energy, Tatham & Peters (2023) on
fuel taxation and the yellow vests, Urpelainen & Zhang (2022) on wind power
and congressional elections — all study settings where regulation is
**actually imposed** and economically costly. In Spain, the ZBE mandate was:

- Not enforced (no penalties for non-compliance in the law)
- Not implemented (82% of obligated cities did nothing)
- Not binding near the identification threshold (zero compliance at 50k)

You cannot study the political cost of a regulation that was never applied.
This is closer to the "symbolic policies" setting studied by Tallent, Jan &
Sattelmayer (2025) — the mandate was symbolic rather than substantive.

---

## 3. What IS in the data — a non-compliance story

The null results on H1 and H2 point to a different and potentially more
interesting finding: **comprehensive non-compliance with a national
environmental mandate.**

### 3.1 The descriptive facts

| Period | Enforcement mechanism | Compliance rate |
|--------|----------------------|----------------|
| 2021–Jun 2023 | Legal mandate only, no sanctions | ~12% (18/151) |
| Mid 2024 | EU fund clawback threats begin | ~34% (58/151) |
| Jan 2026 | Transport subsidies withdrawn | Still rising (~169 cities now obligated) |

- Of the 18 "compliant" cities pre-2023, many merely relabeled pre-existing
  pedestrian zones or traffic-calmed areas as ZBEs (nominal compliance).
- Only ~10 cities had genuine label-based enforcement with cameras and fines
  (Madrid, Barcelona metro, and a handful of others).
- Compliance tripled once the central government threatened to claw back
  Next Generation EU funds (~EUR 1.5bn allocated) and withdraw public
  transport subsidies (Valencia lost EUR 14m/year).

### 3.2 Why this could be a paper

This setting speaks to several established literatures:

**Multilevel governance and implementation in Spain.** Navarro & Velasco
(2022, "From centralisation to new ways of multi-level coordination: Spain")
document the structural tensions in Spanish intergovernmental relations.
The ZBE case is a particularly clean example: a national law imposed a
specific, measurable obligation on municipalities with a clear deadline —
and was comprehensively ignored. This extends their analysis from
coordination *challenges* to outright non-compliance.

**Fiscal federalism / unfunded mandates.** The classic framework (Oates
1972, 2005; Rodden 2006) predicts non-compliance when higher-level
governments impose costly obligations without providing funding, enforcement
capacity, or political cover. The ZBE mandate fits this pattern exactly:
the benefits of cleaner air are diffuse and long-term, while the political
costs of restricting vehicles are local and immediate.

**EU compliance gap — extended to the subnational level.** The EU
implementation literature (Falkner et al. 2005; Treib 2014; Bondarouk &
Mastenbroek 2018) documents how member states transpose directives into
national law but fail to implement them on the ground. Spain's ZBE case
adds a layer: Spain transposed EU clean air objectives into national law
(Ley 7/2021), but *municipalities* refused to implement the national law.
The compliance gap operates at two levels simultaneously.

**Enforcement and conditionality.** Barrett (2008, 2016) on enforcement
in international agreements argues that voluntary compliance fails without
credible sanctions. The Spanish case provides a within-mandate natural
experiment: the same obligation produced ~12% compliance under legal mandate
alone, then ~34% under fiscal conditionality (EU fund clawback). This
speaks directly to the enforcement design question — Shimshack & Ward
(2005) on regulator reputation and compliance, and Gonzalez & You (2024)
on money and cooperative federalism in EPA enforcement.

**Political economy of environmental regulation — the anticipation channel.**
Rather than studying electoral backlash *from* regulation (Colantone et al.
2024; Stokes 2016), we study why regulation *fails to be imposed in the
first place*. The anticipated electoral cost is sufficient to deter
implementation even without actual voter reaction. This connects to
Mildenberger's (2020, *Carbon Captured*) argument about how concentrated
opponents block diffuse-benefit policies, and to Trebilcock (2014,
*Dealing with Losers*) on the political economy of policy transitions.

### 3.3 New finding: fiscal conditionality and the per-capita channel

I downloaded municipal budget settlement data (liquidaciones presupuestarias)
from the Ministerio de Hacienda's CONPREL portal for 2019–2023 and tested
whether fiscal characteristics predict ZBE compliance.

**Setup:** Logit models predicting binary compliance status (vigente=1,
all others=0) among >50k municipalities, using baseline (2019–2020 average)
fiscal variables to avoid post-treatment contamination. Key challenge:
fiscal ratios (e.g., transfer dependency = transfers/total revenue) are
mechanically correlated with city size, since larger cities have higher
own-source revenue. Per-capita measures resolve this — transfers per capita
correlates only r=0.09 with log(population).

**Results (logit, >50k municipalities, N≈63):**

| Model | Key predictor | OR | p-value | Note |
|-------|--------------|-----|---------|------|
| Baseline (log pop only) | log(pop) | 3.61 | <0.001 | Size is the dominant predictor |
| + Transfer dependency | transfer_dep | 0.82 | 0.73 | Confounded with size |
| + Debt burden | debt_burden | 0.41 | 0.62 | Not significant |
| + EU transfer share | eu_share | 1.15 | 0.88 | Not significant |
| + Own revenue share | own_rev_share | 1.23 | 0.67 | Not significant |
| **Per-capita transfers** | **transfers_pc** | **1.006** | **0.049** | **Significant, controlling for log(pop)** |

**Interpretation:** Among >50k municipalities, those receiving more
intergovernmental transfers per capita were marginally more likely to
comply with the ZBE mandate. The effect size is modest (OR=1.006, meaning
each additional EUR per capita in transfers raises the odds of compliance
by 0.6%), but it is the *only* fiscal variable that survives controlling
for city size. This is consistent with a fiscal conditionality mechanism:
cities with greater exposure to intergovernmental transfers had more to
lose from the EU fund clawback and transport subsidy threats.

**Important caveats:**
- p=0.049 is marginal; this would not survive a multiple-testing correction
- The result is driven by the post-conditionality compliers (N≈9 cities
  that moved from non-compliance to compliance after the fiscal threats).
  The pre-conditionality implementers (early movers) show no fiscal pattern.
- With N≈63 municipalities and a binary outcome, statistical power is limited
- The per-capita measure resolves the size confound, but city size (log pop)
  remains the overwhelmingly dominant predictor

**Bottom line:** This is suggestive evidence for the fiscal conditionality
mechanism — enough to motivate the story in Section 6 of the paper, but
too underpowered to be a standalone result. It needs the 2025 data to
become credible (see Section 3.5).

### 3.4 Proposed paper structure (revised)

> **"Why Mandates Fail: Low-Emission Zones and the Politics of
> Non-Compliance in Spain"**

1. **Institutional background**: Climate law, ZBE mandate, 50k threshold,
   EU clean air context
2. **Measuring compliance**: Original hand-coded ZBE status for all 151+
   cities (enforced / nominal / delayed / none) — descriptive contribution
3. **The threshold had no bite**: RD on fleet composition shows zero
   discontinuity (Section 2.2). Cleanest empirical result.
4. **What predicts compliance?** Not governing party; only city size.
   Logit analysis with institutional controls. **Fiscal controls** from
   Hacienda data (transfer dependency, debt burden, own revenue share)
   included as covariates.
5. **Why mandates fail without enforcement**: Three mechanisms —
   (a) no sanctions in the law, (b) local electoral costs vs. diffuse
   benefits, (c) coordination failure among peer cities
6. **Fiscal conditionality works**: Compliance tripled after EU fund
   clawback threats and transport subsidy withdrawal. **Mechanism test:**
   per-capita transfers predict post-conditionality compliance (p=0.049),
   consistent with fiscal exposure driving the response. Pre/post analysis
   with 2025 fleet data if available.

### 3.5 What additional data would strengthen this

**The 2025 DGT fleet data (expected mid-2026) changes things dramatically.**
By January 2026, ~169 municipalities are obligated and ~58 have ZBEs
vigentes. If you can code compliance status for all 169 and merge with
fiscal data, you have a proper cross-section with real power. At that
point the per-capita transfers result either replicates with N≈58
compliers or it doesn't — and either answer is informative.

*Scenario A: The result holds.* With N≈58 compliers (vs. ~111
non-compliers), you have a well-powered logit. If transfers per capita
remains significant controlling for log(population), this is credible
evidence that fiscal conditionality operated through the transfer channel
— cities with more to lose complied faster. This becomes the headline
result of Section 6 and elevates the paper from "descriptive non-compliance
story" to "mechanism-identified compliance paper."

*Scenario B: The result disappears.* If the relationship washes out with
more data, that is equally informative — it means the early post-
conditionality compliers were not systematically the most fiscally
exposed cities. Non-compliance was driven by something else (political
will, administrative capacity, local opposition). The paper still works
but Section 6 becomes purely descriptive: conditionality increased
compliance on average, but the *within-city* channel was not fiscal
exposure.

**Other valuable additions:**
- **Municipality-level EU fund allocations**: Which cities received Next
  Generation funds for ZBE implementation and how much. Available from
  Ministerio de Transportes.
- **Detailed compliance timeline**: Exact activation dates for each city's
  ZBE. Partially available from MITECO's interactive map.

---

## 4. Questions for you

1. **Is the non-compliance angle worth pursuing?** It pivots away from
   Colantone-style electoral backlash toward fiscal federalism and EU
   compliance. The empirical work is mostly done; the question is whether
   the framing is compelling enough for a publication.

2. **Target outlet?** Given the mix of environmental policy and multilevel
   governance, candidates include:
   - *Journal of Environmental Economics and Management* (RD + fleet data)
   - *European Journal of Political Economy* (political economy angle)
   - *Regulation & Governance* (compliance/enforcement focus)
   - *Journal of Public Policy* or *JPART* (implementation failure)
   - *Environmental Politics* (EU climate policy)

3. **Should I invest in collecting the additional data** (EU fund
   allocations, detailed compliance timeline), or is the current evidence
   sufficient for a first draft?

4. **Timing on the 2025 DGT fleet data.** The municipal-level data for
   2025 should appear on DGT's portal around mid-2026. Should I wait for
   this before circulating a draft, or write up the current results and
   plan a revision? The fiscal conditionality result (Section 3.3) goes
   from suggestive (N≈9 post-conditionality compliers) to potentially
   definitive (N≈58) with the new data.

5. **Connection to my other project.** The US climate litigation paper
   (ClimateLiterature repo) studies the *opposite* phenomenon — subnational
   governments proactively using courts to advance climate policy. There
   may be a conceptual link worth developing: in both cases, subnational
   governments respond strategically to higher-level mandates, but the
   direction differs based on fiscal incentives, institutional capacity,
   and electoral pressures.

---

## Appendix A: Summary of completed analyses

| Script | Analysis | Key result |
|--------|----------|------------|
| 11 | DiD: ZBE implementers vs non-implementers (Vox) | Suggestive but driven by Barcelona floor effect |
| 12 | Party politics of ZBE adoption | Null — party does not predict adoption (p=0.16) |
| 12b | Fiscal predictors of ZBE compliance | Per-capita transfers significant (p=0.049); all ratio measures null |
| 13 | RD: Fleet composition at 50k threshold | Null — zero discontinuity, all years (DiRD p=0.89) |

All code, data, and outputs are in the SpainCars repository.

## Appendix B: Key references (in my existing bib or to add)

**Already in references.bib:**
- Stokes (2016) "Electoral Backlash against Climate Policy"
- Stokes (2020) *Short Circuiting Policy*
- Mildenberger (2020) *Carbon Captured*
- Mildenberger & Lachapelle (2022) "Limited impacts of carbon tax rebates"
- Tatham & Peters (2023) "Fueling opposition? Yellow vests..."
- Urpelainen & Zhang (2022) "Electoral Backlash or Positive Reinforcement?"
- Tallent, Jan & Sattelmayer (2025) "More than Symbols"
- Navarro & Velasco (2022) "From centralisation to new ways of multi-level coordination: Spain"
- Shimshack & Ward (2005) "Regulator reputation, enforcement..."
- Gonzalez & You (2024) "Money and cooperative federalism: EPA"
- Barrett (2008, 2016) on enforcement in international agreements
- Trebilcock (2014) *Dealing with Losers*
- Heidbreder (2017) "Strategies in multilevel policy implementation"

**Need to add:**
- Colantone, Lonardo, Prato & Stanig (2024) "The Political Consequences of Green Policies" APSR
- Oates (1972, 2005) fiscal federalism
- Rodden (2006) *Hamilton's Paradox*
- Falkner, Treib, Hartlapp & Leiber (2005) *Complying with Europe*
- Treib (2014) "Implementing and complying with EU governance outputs"
- Bondarouk & Mastenbroek (2018) on EU environmental compliance
- Scharpf (1988) on joint-decision traps
