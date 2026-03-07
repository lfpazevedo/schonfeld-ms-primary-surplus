# Documentation Index

This folder contains critical research findings and methodology documentation for the steepener strategy.

---

## ⚠️ CRITICAL FINDINGS (Read First)

### 1. `STUDY_LOOKAHEAD_BIAS_AND_FOCUS_STD_DEV.md`
**Status**: CRITICAL — Invalidates V1–V4 results

**Summary**: 
- Identifies look-ahead bias in V1–V4 (full-sample percentiles)
- Reveals cross-sectional vs. time-series confusion in Focus std dev usage
- Provides corrected implementation approaches

**Key Finding**: V3 (−35.59 bps) and V4 (−183.87 bps) results are **invalid** due to look-ahead bias. True performance likely 50-100% worse.

---

### 2. `STRATEGY_VERSION_VALIDITY_MATRIX.md`
**Status**: REFERENCE — Quick validity guide

**Summary**:
- Side-by-side comparison of all strategy versions
- Validity ratings for each version
- Shows evolution of fixes (V5+ corrected look-ahead)

**Use For**: Quick reference on which versions can be trusted

---

### 3. `METHODOLOGY_EVOLUTION.md`
**Status**: HISTORY — Design decisions & lessons learned

**Summary**:
- Tracks strategy evolution from V1 to V7 (planned)
- Documents the "boiled frog" normalization problem
- Outlines validation protocol for production

**Use For**: Understanding why design choices were made

---

## Code Reference

### `src/data/processing/focus/proper_uncertainty_measures.py`
**Status**: IMPLEMENTATION — Correct uncertainty measures

**Summary**:
- Implements time-series volatility (correct measure)
- Implements forecast revision tracking
- Provides composite uncertainty index
- Includes expanding-window regime detection (no look-ahead)

**Use For**: Replacing Focus std dev with proper uncertainty measures in V7

---

## Study Summary

### The Two Critical Errors

| Error | V1–V4 Status | Impact | Fixed In |
|-------|--------------|--------|----------|
| **Look-Ahead Bias** | Full-sample percentiles | Results inflated 50-100% | V5+ |
| **Wrong Uncertainty Measure** | Cross-sectional std used | Regime detection incorrect | V7 (planned) |

### What Focus Std Dev Actually Is

```
Focus Std Dev = Disagreement among forecasters (cross-sectional)
                ↓
    Hedge Fund A: -1.2%
    Hedge Fund B: -0.8%
    Bank C:       -1.5%
    → Std = 0.35%

What we should use = Time-series volatility
                ↓
    Jan forecast: -1.0%
    Feb forecast: -1.2%
    Mar forecast: -0.9%
    → Vol = 0.18% (annualized)
```

### Version Status Summary

| Version | Look-Ahead | Correct Measure | Normalization | Status |
|---------|------------|-----------------|---------------|--------|
| V1–V4 | ❌ Full sample | ❌ Cross-sectional | N/A | **INVALID** |
| V5 | ✅ Expanding | ⚠️ Still wrong | ⚠️ Rolling | Deprecated |
| V6 | ✅ Expanding | ⚠️ Still wrong | ✅ Expanding | Conditional |
| V7 | ✅ Expanding | ✅ Time-series | ✅ Expanding | Planned |

---

## Recommended Reading Order

1. **If you're new**: Start with `STRATEGY_VERSION_VALIDITY_MATRIX.md` for context
2. **If you're technical**: Read `STUDY_LOOKAHEAD_BIAS_AND_FOCUS_STD_DEV.md` for details
3. **If you're implementing**: Study `proper_uncertainty_measures.py` for code
4. **If you're reviewing**: Check `METHODOLOGY_EVOLUTION.md` for design rationale

---

## Action Items

### For Stakeholders
- [ ] Review `STRATEGY_VERSION_VALIDITY_MATRIX.md` (5 minutes)
- [ ] Archive any V1–V4 results in presentations/reports
- [ ] Approve V7 development roadmap

### For Developers
- [ ] Implement proper uncertainty measures (see `proper_uncertainty_measures.py`)
- [ ] Run V3/V4 with expanding windows (for comparison)
- [ ] Design V7 architecture with composite uncertainty index

### For Risk Management
- [ ] Establish 3-stage validation protocol
- [ ] Define Sharpe thresholds for production
- [ ] Create monitoring framework for regime detection accuracy

---

## Contact

- **Research Questions**: Quantitative Research Team
- **Implementation Questions**: Data Engineering Team
- **Risk/Validation Questions**: Risk Management Team

---

*Last Updated: March 6, 2026*
*Document Owner: Quantitative Research*
