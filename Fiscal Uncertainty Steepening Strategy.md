# **Strategic Allocation in Steepening Yield Curve Environments: A Markov-Switching Approach to Fiscal Uncertainty and Liquidity Microstructure**

The term structure of interest rates, fundamentally represented by the yield curve, serves as a comprehensive visual and mathematical snapshot of the relationship between bond yields and their respective maturities. This curve is not merely a static depiction of current borrowing costs but a dynamic indicator of market expectations regarding economic growth, inflation trajectories, and the future path of monetary policy.1 A steepening yield curve, characterized by an increasing differential between short-term and long-term interest rates, provides critical insights into shifting macroeconomic regimes. Whether this steepening is driven by a rapid decline in short-term rates or a more pronounced rise in long-term yields, the resulting widening of the spread necessitates a sophisticated approach to portfolio positioning and execution.  
Traditional fixed-income analysis often treats yield curve shifts as linear responses to isolated economic data points. However, modern financial theory increasingly recognizes that the market moves through distinct, often unobservable, regimes. These regimes are frequently governed by the degree of fiscal policy uncertainty and the subsequent demand for term premiums.5 To navigate these transitions, the application of Markov-switching models offers a robust econometric framework, allowing for the identification of structural breaks and shifts in volatility that characterize high-uncertainty environments.8 Within this framework, a binary strategic mandate emerges: in periods of high fiscal uncertainty, market participants must prioritize execution immediacy by paying the spread, whereas in stable regimes, the primary objective shifts toward collecting the carry and optimizing roll-down gains.5

## **Taxonomic Analysis of Yield Curve Morphology and Steepening Regimes**

The yield curve’s shape—normal, flat, or inverted—reflects the market’s baseline expectations for the economic cycle. A normal or upward-sloping curve conveys a sentiment of continued economic expansion and moderate inflation, where lenders demand higher yields for longer-term commitments to compensate for the inherent risks of time.3 The steepness of this slope is the primary focus of curve-based trading strategies, with the 2-year and 10-year Treasury yield spread serving as the industry-standard benchmark.4

| Yield Curve Shape | Spread Characteristic | Market Implication | Strategic Focus |
| :---- | :---- | :---- | :---- |
| Normal | Positive and widening | Anticipated expansion; rising inflation expectations 3 | Carry and roll-down optimization 5 |
| Flat | Near zero or narrowing | Transition point; policy uncertainty; potential slowdown 3 | Defensive positioning; duration management 14 |
| Inverted | Negative (short \> long) | Precursor to economic contraction; restrictive monetary policy 14 | Flight to safety; long-end outperformance 16 |
| Steep | Highly positive | Robust growth outlook or significant fiscal stimulus 2 | Spread widening trades; inflationary hedges 2 |

Steepening is defined by the widening of the yield differential between two points on the curve, yet the macroeconomic drivers behind this movement vary significantly depending on whether the shift is driven by a "bull" or "bear" market environment.1

### **Macroeconomic Triggers for Bull Steepening**

A bull steepener manifests when short-term interest rates fall more significantly than long-term rates. This scenario is typically viewed as "bullish" for the bond market because falling yields correspond to rising bond prices, with the most substantial gains concentrated at the shorter end of the curve.1 This movement is often triggered by the onset of a Federal Reserve rate-cutting cycle designed to spur economic activity during a slowdown or recession.1  
As the central bank aggressively lowers the federal funds rate, the front end of the curve responds with immediacy. However, long-term rates may decline at a slower pace or remain relatively stable, reflecting market participants' expectations of a future rebound in growth and inflation stemming from the monetary stimulus.6 The primary risk in a bull steepener is reinvestment risk; as short-term yields fall, the proceeds from maturing assets must be redeployed into lower-yielding securities.15

### **Macroeconomic Triggers for Bear Steepening**

Conversely, a bear steepener arises when long-term interest rates rise faster than short-term rates. This is a "bearish" development for bondholders, as rising yields lead to declining prices, particularly for intermediate-to-long-dated maturities that possess higher duration sensitivity.1 Bear steepening is frequently driven by expectations of robust economic growth and rising inflation, prompting investors to demand higher compensation for locking in their capital over longer horizons.2  
Beyond growth optimism, bear steepening is increasingly associated with fiscal policy pressures. When a government engages in large-scale deficit spending or significant fiscal stimulus, the resulting increase in Treasury supply can put upward pressure on long-term rates.2 This is compounded by rising inflation expectations, as the market anticipates that loose fiscal policy may lead to an overheating economy. In this environment, investors sell long-dated bonds to avoid capital losses, further driving up yields and steepening the curve.2

## **Markov-Switching Foundations for Regime-Dependent Interest Rate Modeling**

The inherent nonlinearity of interest rate movements, characterized by periods of relative stability interrupted by sudden spikes in volatility or shifts in mean levels, necessitates an econometric approach that can accommodate multiple states of the world. Markov-switching (MS) models, popularized by Hamilton, provide this capability by postulating that the economy moves between distinct regimes governed by an unobservable state variable $s\_t$.8

### **Mathematical Framework and State Transitions**

In a Markov-switching model, the parameters of the underlying process—such as the mean $\\mu$, the autoregressive coefficient $\\beta$, and the variance $\\sigma^2$—are functions of the state $s\_t$. For a simple switching AR(1) process, the observation $z\_t$ follows the law:

$$z\_t \= \\alpha(s\_t) \+ \\beta z\_{t-1} \+ \\epsilon\_t, \\quad \\epsilon\_t \\sim N(0, \\sigma^2(s\_t))$$  
where the transition between states is governed by a first-order Markov chain with fixed transition probabilities $p\_{ij} \= P(s\_t \= j | s\_{t-1} \= i)$.8 This property ensures that the current regime is dependent only on the immediate past, allowing the model to capture "jumpy" behavior as the market oscillates between different macroeconomic structures.9  
For interest rate trading, these regimes often correspond to "Normal" and "Crisis" states. In a normal state, interest rate dynamics may follow a mean-reverting process with low volatility. In a crisis or high-uncertainty state, the model may switch to a high-variance regime or a random-walk process, reflecting the breakdown of standard equilibrium relationships.20

### **Optimal Filtering and Regime Tracking in Incomplete Markets**

The challenge for market participants is that the true state $s\_t$ is hidden. To estimate the probability of being in a particular regime, traders utilize online filtering techniques. The goal is to calculate the conditional expectation $\\hat{Z}\_t \= E$ based on the filtration $\\mathcal{S}\_t$ generated by observed security prices.24 This process is mathematically rigorous because interest rate observations often contain state-dependent noise and filtration discontinuities.24  
A sophisticated market model governed by a Markov regime-switching process is naturally incomplete, meaning that not all risks can be hedged using the underlying assets alone.24 To complete the market, researchers suggest adding a number of derivatives equal to the number of possible regimes.24 This "market enlargement" allows the hidden regime to become adapted to the information set, enabling the construction of self-financing portfolios that can replicate any contingent claim.24

| Model Component | Functional Role in Strategy | Economic Interpretation |
| :---- | :---- | :---- |
| Latent State ($s\_t$) | Identifies unobservable regime | Normal vs. High Uncertainty/Crisis 9 |
| Transition Matrix ($P$) | Quantifies regime persistence | Probability of exiting ZLB or crisis 19 |
| Regime-Dependent Vol ($\\sigma(s\_t)$) | Measures instant risk | High-volatility regimes during fiscal shocks 23 |
| Filtering Probability ($\\hat{Z}\_t$) | Real-time signal for execution | Threshold for "paying the spread" 12 |

## **Fiscal Policy Uncertainty and its Role in Yield Curve Twists**

Fiscal policy has transitioned from a background variable to a primary driver of the Treasury term structure. Fiscal uncertainty, often proxied by news-based indices or volatility in tax and spending processes, has profound implications for the term premium and the steepness of the yield curve.6

### **Mechanisms of Fiscal Volatility Shocks**

Fiscal volatility shocks—defined as shocks to the uncertainty surrounding future tax rates and government spending rather than the levels themselves—can have sizable adverse effects on economic activity.23 These shocks typically lead to a drop in aggregate output, investment, and consumption as households and firms delay major expenditures in anticipation of a less certain fiscal future.23  
From a yield curve perspective, heightened fiscal policy uncertainty is often "stagflationary." It creates upward pressure on inflation expectations while simultaneously restraining real economic growth.28 This combination is a classic driver of bear steepening: long-term yields rise to reflect the risk of future fiscal consolidation or the inflationary consequences of a "fiscally-led" regime where debt is stabilized through price increases rather than surpluses.19

### **The Zero Lower Bound and Fiscally-Led Regimes**

The interaction between fiscal uncertainty and monetary policy is particularly acute at the Zero Lower Bound (ZLB). When nominal interest rates cannot be lowered further, the central bank’s ability to mitigate economic shocks is severely restricted.19 In this state, inflation expectations become highly sensitive to agents' beliefs about the "exit strategy" from the ZLB.  
If the market assigns a non-zero probability to a switch from a "monetary-led" regime (where the Fed aggressively targets inflation) to a "fiscally-led" regime (where debt concerns override price stability), inflation expectations can rise even in a recession.19 This inflationary pressure from the stock of public debt can prevent a deflationary spiral but results in a steeper, more volatile yield curve as investors demand a higher "safety margin" in the form of term premium.6

## **Strategic Execution: "Pay the Spread" in High-Uncertainty Regimes**

In the context of the proposed strategy, the identification of a high-uncertainty regime via a Markov-switching model triggers a shift in execution tactics. High-uncertainty regimes are characterized by impaired price discovery, widened bid-ask spreads, and unstable dynamics.12

### **The Physics of Execution Immediacy**

An investor seeking to establish a steepening position during a fiscal crisis—such as a debt ceiling impasse or a sudden surge in global risk aversion—faces a trade-off between price and certainty.12 In these environments, the strategy dictates that the participant should "pay the spread." This involves hitting the lowest ask or the highest bid with a market order rather than waiting at the back of a first-in-first-out (FIFO) queue with a limit order.12  
The rationale for paying the spread in a high-uncertainty regime is rooted in the risk of non-execution. If the market is in a "jump" state, where prices move discretely from one level to another, the cost of missing the entry or exit can far exceed the immediate transaction cost of the spread.12 Furthermore, in illiquid markets, the existence of a "square root rule" for price impact means that as trade size increases relative to market volume, the cost of execution grows non-linearly, making quick, aggressive execution preferable before liquidity further evaporates.12

### **Dealer Behavior and Adverse Selection**

During high-uncertainty periods, market makers and dealers face extreme inventory costs and limited risk tolerance.33 To protect against "informed traders" who may have superior information regarding a policy shift or a fiscal announcement, dealers widen their spreads significantly.32 For a steepener trader, "paying the spread" is an acknowledgment of this dealer risk premium. In a bear steepener driven by fiscal fears, for example, the impatient seller of long-dated bonds must accept a lower price to transfer the duration risk to a dealer's balance sheet.3

## **Strategic Execution: "Collect the Carry" in Low-Uncertainty Regimes**

In contrast, when the Markov-switching model identifies a low-uncertainty or "normal" regime, the strategic emphasis shifts toward the steady accumulation of returns through carry and roll-down optimization.5

### **Carry and Roll-Down Mechanics**

A yield curve spread steepener is typically executed by going long the front leg (e.g., 2-year notes) and short the back leg (e.g., 10-year notes).3 In a stable, upward-sloping curve environment, this trade generates "carry" if the yield of the long position exceeds the cost of financing it, and "roll-down" as the bond's maturity shortens and its price increases toward the lower yields of the shorter-term curve.5  
"Collecting the carry" in these regimes involves:

* **Patient Execution**: Utilizing limit orders to capture the spread, essentially acting as a liquidity provider rather than a liquidity taker.12  
* **Riding the Curve**: Holding bonds as they "roll down" the steep portions of the curve to capture price appreciation.5  
* **Duration Extension**: Incrementally shifting into longer maturities when the term premium appears elevated but inflation expectations are stable, thereby harvesting the risk premium without significant capital risk.5

| Trading Environment | Execution Style | Primary Goal | Tactical Implementation |
| :---- | :---- | :---- | :---- |
| High Fiscal Uncertainty | Pay the Spread | Immediacy / Risk Transfer | Market orders; high turnover; focus on slope change 12 |
| Low Fiscal Uncertainty | Collect the Carry | Yield Optimization | Limit orders; buy-and-hold for roll-down; spread capture 5 |

## **Intermediary Constraints and Central Bank Interventions**

The success of a regime-adaptive steepening strategy is heavily influenced by the capacity of financial intermediaries and the potential for central bank intervention.5

### **Dealer Balance Sheet Capacity and the SLR**

In the modern regulatory environment, the ability of primary dealers to intermediate the Treasury market is constrained by factors like the Supplementary Leverage Ratio (SLR).34 During periods of intense selling pressure—such as the "dash for cash" in March 2020—dealers may reach their balance sheet limits, causing a breakdown in market functioning.29  
For a steepener trader, these constraints manifest as a sudden, massive widening of the spread, making "paying the spread" an expensive but necessary action to exit or adjust positions.12 Furthermore, the unwinding of popular "basis trades"—where hedge funds use high leverage to exploit small price differences between cash Treasuries and futures—can lead to fire sales that distort the yield curve independently of macroeconomic fundamentals.34

### **Central Bank as a Regime Disrupter**

Central banks often intervene to address market dysfunction through asset purchase programs or repo facilities.29 While these actions are designed to restore liquidity, they can fundamentally alter the yield curve regime. For instance, the resumption of Quantitative Easing (QE) directly flattens the curve by suppressing long-term yields, which can ruin a bear steepener position even if fiscal concerns remain high.6  
Traders must therefore monitor "quasi-fiscal" risks, where central bank policy is overtly driven by managing the federal deficit or housing affordability rather than purely targeting inflation.36 The emergence of "fiscal dominance" represents a terminal regime for a steepening strategy, where institutional risk and the erosion of central bank independence lead to persistent inflation and a structurally steeper curve, albeit with extreme volatility.36

## **Global Divergence in Yield Curve Dynamics**

While the U.S. Treasury market is the primary venue for curve trades, fiscal uncertainty and regime-switching dynamics are global phenomena.7

### **The European Sovereign Context**

In the Eurozone, yield curve steepening has recently been driven by a combination of European Central Bank (ECB) easing and sovereign-specific fiscal concerns.36 Countries like France have seen their 10-year yields sell off significantly due to political instability and fiscal imbalances, resulting in a bear steepener that reflects a rising sovereign risk premium.6 Markov-switching models applied to European CDS term premiums reveal that the sensitivity of these spreads to market shocks can be ten times higher during crisis periods, underscoring the need for a regime-adaptive approach.26

### **The Japanese "Pivot" and Governance Risk**

Japan presents a unique case where the potential failure to form a stable government can usher in a period of heightened political uncertainty, amplifying volatility in Japanese Government Bonds (JGBs).7 As Japan moves away from years of negative interest rates, the yield curve has steepened to the highest levels in years, driven by the buds of governance risk and the market's demand for a positive term premium.7

| Region | Primary Steepening Driver | Regime Indicator | Strategic Nuance |
| :---- | :---- | :---- | :---- |
| United States | Debt ceiling; Fed cutting cycle; QE/QT shifts 6 | Fiscal EPU index; ACM term premium 5 | Focus on NOB/ZF spreads; DV01 neutrality 13 |
| Eurozone | Political instability (France); ECB transition 6 | Sovereign CDS spreads; volatility spikes 26 | Cross-country spread trades; liquidity focus 26 |
| Japan | Exit from YCC; political gridlock; governance risk 7 | BOJ policy signals; term premium return 7 | Managing "jump" risks in a low-vol regime 7 |

## **Quantitative Implementation: Synthesizing the Regime-Switching Strategy**

A professional implementation of the "Pay vs. Collect" strategy requires a multi-layered quantitative process that bridges high-frequency execution with long-term macroeconomic modeling.

### **Layer 1: The Macro-Econometric Filter**

The foundational layer utilizes a multivariate Markov-switching VAR (MS-VAR) or a regime-switching Nelson-Siegel model to identify the broad state of the economy.10 This model uses a large information set—including labor market slack, core PCE inflation, and global equity indices—to estimate the transition probabilities between expansionary and recessionary regimes.10  
Specifically, the model identifies the "ZLB State" (Zero Lower Bound) versus the "Normal State." The ZLB state is characterized by constant short rates but high sensitivity in long-term yields to fiscal exit strategies.19 Detection of a transition toward a "Fiscally-led" regime within the ZLB state is a primary signal for establishing long-duration bear steepeners.19

### **Layer 2: The Fiscal Uncertainty Monitor**

The second layer specifically targets fiscal volatility shocks.23 By estimating the laws of motion for government spending as a share of output and various tax rates (labor, capital, consumption), the strategy can distinguish between "level shocks" (which may be transitory) and "volatility shocks" (which increase the risk premium).23  
A two-standard-deviation increase in fiscal policy uncertainty has been shown to have an effect similar to a 25-basis-point innovation in the federal funds rate, but with a "stagflationary" tilt.28 When this uncertainty crosses a predetermined threshold, the strategy's execution component switches to "Pay the Spread" mode to lock in positions before fiscal consolidation battles or default risks fully materialize.12

### **Layer 3: High-Frequency Execution and Microstructure**

The final layer operates in real-time, monitoring the limit order book (LOB) and dealer inventory signals.32 In a low-uncertainty regime, the strategy uses "patient" limit orders to capture the bid-ask spread.12 In a high-uncertainty regime, identified by the MS-filter, the algorithm utilizes market orders to cross the spread and ensure execution.  
This layer also incorporates the "Vol-Slide" and "Carry-Adjusted" pricing for derivatives.39 Because being long a steepener through options often involves a negative carry position (paying the spread of implied over realized volatility), the strategy optimizes the timing of entry to coincide with regime shifts where the expected jump in realized volatility outweighs the carry cost.20

## **Conclusion: Adaptive Mastery of the Fiscal-Monetary Nexus**

The paradigm of yield curve trading has fundamentally shifted from a focus on central bank "dot plots" to an integrated analysis of fiscal-monetary coordination and the unobservable regimes of the macroeconomy. The steepening yield curve remains a potent signal of expansion and inflationary risk, but its message is increasingly filtered through the lens of sovereign debt sustainability and institutional stability.  
By employing Markov-switching models, sophisticated market participants can move beyond the "illusion of linearity" and recognize the structural breaks that define modern markets. The mandate to "pay the spread" during high fiscal uncertainty is an essential adaptation to the reality of impaired liquidity and dealer constraints. Conversely, the ability to "collect the carry" in stable regimes remains the bedrock of long-term bond returns through roll-down and yield harvesting.  
As the global economy faces the "toxic cocktail" of elevated debt levels and political instability, the ability to discern and trade between these hidden states will be the hallmark of superior fixed-income management. The yield curve is no longer just a line on a chart; it is a battleground where fiscal reality meets monetary theory, and where the most successful strategies are those that adapt their execution to the prevailing regime of uncertainty.

#### **Works cited**

1. Chart: Two types of steepening yield curves | Columbia Threadneedle Investments US, accessed March 5, 2026, [https://www.columbiathreadneedleus.com/insights/latest-insights/chart-two-types-of-steepening-yield-curves](https://www.columbiathreadneedleus.com/insights/latest-insights/chart-two-types-of-steepening-yield-curves)  
2. Finance 101: What is a Bear Steepener? \- Fire Capital Management, accessed March 5, 2026, [https://www.firecapitalmanagement.com/finance-101/what-is-a-bear-steepener](https://www.firecapitalmanagement.com/finance-101/what-is-a-bear-steepener)  
3. Yield Curve Strategies: Steepeners, Flatteners, and More \- IR Structure, accessed March 5, 2026, [https://irstructure.com/yield-curve-strategies-steepeners-flatteners-and-more/](https://irstructure.com/yield-curve-strategies-steepeners-flatteners-and-more/)  
4. What Can Investors Learn From the Yield Curve? \- American Century Investments, accessed March 5, 2026, [https://www.americancentury.com/insights/yield-curve/](https://www.americancentury.com/insights/yield-curve/)  
5. Treasury Term Premium Harvesting Strategies \- DayTrading.com, accessed March 5, 2026, [https://www.daytrading.com/treasury-term-premium-strategies](https://www.daytrading.com/treasury-term-premium-strategies)  
6. Yield Curve Steepening in the Near Term, Risk of Higher Term Premium Further Out \- DoubleLine, accessed March 5, 2026, [https://doubleline.com/wp-content/uploads/DoubleLine\_Yield-Curve-Term-Premium\_September-2025.pdf](https://doubleline.com/wp-content/uploads/DoubleLine_Yield-Curve-Term-Premium_September-2025.pdf)  
7. Global Debt Trends Amid Political Uncertainty \- LPL Financial, accessed March 5, 2026, [https://www.lpl.com/research/weekly-market-commentary/intersection-of-political-uncertainty-and-global-debt-markets.html](https://www.lpl.com/research/weekly-market-commentary/intersection-of-political-uncertainty-and-global-debt-markets.html)  
8. RDP 9611: A Markov-Switching Model of Inflation in Australia, accessed March 5, 2026, [https://www.rba.gov.au/publications/rdp/1996/9611/markov-switching-models.html](https://www.rba.gov.au/publications/rdp/1996/9611/markov-switching-models.html)  
9. LECTURE ON THE MARKOV SWITCHING MODEL, accessed March 5, 2026, [https://homepage.ntu.edu.tw/\~ckuan/pdf/Lec-Markov\_note.pdf](https://homepage.ntu.edu.tw/~ckuan/pdf/Lec-Markov_note.pdf)  
10. Dynamic Yield Curve Forecasting with Regime-Switching Nelson-Siegel-Svensson Models \- Princeton Dataspace, accessed March 5, 2026, [https://dataspace.princeton.edu/handle/88435/dsp019c67wq67g](https://dataspace.princeton.edu/handle/88435/dsp019c67wq67g)  
11. Methods for Measuring Expectations and Uncertainty in Markov-Switching Models \- Duke Economics, accessed March 5, 2026, [https://public.econ.duke.edu/\~fb36/Papers\_Francesco\_Bianchi/Bianchi\_methods\_for\_ms\_models](https://public.econ.duke.edu/~fb36/Papers_Francesco_Bianchi/Bianchi_methods_for_ms_models)  
12. EXECUTING WITH IMPACT \- Capital Fund Management, accessed March 5, 2026, [https://www.cfm.com/wp-content/uploads/2022/12/142-2016-Executing-with-impact-why-the-price-you-want-is-not-the-price-you-get.pdf](https://www.cfm.com/wp-content/uploads/2022/12/142-2016-Executing-with-impact-why-the-price-you-want-is-not-the-price-you-get.pdf)  
13. Yield Curve Spread Trades: Opportunities & Applications \- CME Group, accessed March 5, 2026, [https://www.cmegroup.com/education/files/yield-curve-spread-trades.pdf](https://www.cmegroup.com/education/files/yield-curve-spread-trades.pdf)  
14. What the Shape-Shifting Yield Curve Is Telling Us About Markets, accessed March 5, 2026, [https://www.hartfordfunds.com/insights/market-perspectives/fixed-income/what-the-shape-shifting-yield-curve-is-telling-us-about-markets.html](https://www.hartfordfunds.com/insights/market-perspectives/fixed-income/what-the-shape-shifting-yield-curve-is-telling-us-about-markets.html)  
15. What Investors Need to Know About the Steepening Yield Curve | Morningstar, accessed March 5, 2026, [https://www.morningstar.com/markets/what-investors-need-know-about-steepening-yield-curve](https://www.morningstar.com/markets/what-investors-need-know-about-steepening-yield-curve)  
16. Yield Curve Dynamics: Impact on Markets and Trading Strategies \- Bookmap, accessed March 5, 2026, [https://bookmap.com/blog/yield-curve-dynamics-impact-on-markets-and-trading-strategies](https://bookmap.com/blog/yield-curve-dynamics-impact-on-markets-and-trading-strategies)  
17. Bear Steepener: Understanding Yield Curve Steepening \- FasterCapital, accessed March 5, 2026, [https://fastercapital.com/content/Bear-Steepener--Understanding-Yield-Curve-Steepening.html](https://fastercapital.com/content/Bear-Steepener--Understanding-Yield-Curve-Steepening.html)  
18. (PDF) A Markov Switching Factor-Augmented VAR Model for Analyzing US Business Cycles and Monetary Policy \- ResearchGate, accessed March 5, 2026, [https://www.researchgate.net/publication/276261243\_A\_Markov\_Switching\_Factor-Augmented\_VAR\_Model\_for\_Analyzing\_US\_Business\_Cycles\_and\_Monetary\_Policy](https://www.researchgate.net/publication/276261243_A_Markov_Switching_Factor-Augmented_VAR_Model_for_Analyzing_US_Business_Cycles_and_Monetary_Policy)  
19. Escaping the Great Recession \- NBER, accessed March 5, 2026, [https://www.nber.org/system/files/working\_papers/w20238/revisions/w20238.rev1.pdf](https://www.nber.org/system/files/working_papers/w20238/revisions/w20238.rev1.pdf)  
20. Practical Markov Regime-Switching for Finance and Energy: Mitigating the Risk of Spurious Regimes. | by Jonathan | Medium, accessed March 5, 2026, [https://medium.com/@jlevi.nyc/practical-markov-regime-switching-for-finance-and-energy-mitigating-the-risk-of-spurious-regimes-61fb955c240b](https://medium.com/@jlevi.nyc/practical-markov-regime-switching-for-finance-and-energy-mitigating-the-risk-of-spurious-regimes-61fb955c240b)  
21. Regime-Switching Models for Estimating Inflation Uncertainty \- Federal Reserve, accessed March 5, 2026, [https://www.federalreserve.gov/econresdata/feds/2015/files/2015093pap.pdf](https://www.federalreserve.gov/econresdata/feds/2015/files/2015093pap.pdf)  
22. Non-Linear Phillips Curves with Inflation Regime-Switching \- Federal Reserve Board, accessed March 5, 2026, [https://www.federalreserve.gov/econresdata/feds/2016/files/2016078pap.pdf](https://www.federalreserve.gov/econresdata/feds/2016/files/2016078pap.pdf)  
23. Fiscal Volatility Shocks and Economic Activity, accessed March 5, 2026, [https://public.econ.duke.edu/\~jfr23/Current/main\_paper.pdf](https://public.econ.duke.edu/~jfr23/Current/main_paper.pdf)  
24. Regime Tracking in Markets with Markov Switching \- MDPI, accessed March 5, 2026, [https://www.mdpi.com/2227-7390/12/3/423](https://www.mdpi.com/2227-7390/12/3/423)  
25. A Regime-Switching Model of the Yield Curve at the Zero Bound \- Federal Reserve Bank of San Francisco, accessed March 5, 2026, [https://www.frbsf.org/wp-content/uploads/wp2013-34.pdf](https://www.frbsf.org/wp-content/uploads/wp2013-34.pdf)  
26. Short-term determinants of the idiosyncratic sovereign risk premium: a regime-dependent analysis for european credit default swa \- ECB, accessed March 5, 2026, [https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1717.pdf](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1717.pdf)  
27. Research on the Impact of Economic Policy Uncertainty and Investor Sentiment on the Growth Enterprise Market Return in China—An Empirical Study Based on TVP-SV-VAR Model \- MDPI, accessed March 5, 2026, [https://www.mdpi.com/2227-7072/12/4/108](https://www.mdpi.com/2227-7072/12/4/108)  
28. Fiscal Volatility Shocks and Economic Activity \- Federal Reserve Bank, accessed March 5, 2026, [https://www.newyorkfed.org/medialibrary/media/research/conference/2011/NYAMP/Fernandez-Villaverde\_etal\_2011.pdf](https://www.newyorkfed.org/medialibrary/media/research/conference/2011/NYAMP/Fernandez-Villaverde_etal_2011.pdf)  
29. Market dysfunction and central bank tools \- Bank for International Settlements, accessed March 5, 2026, [https://www.bis.org/publ/mc\_insights.htm](https://www.bis.org/publ/mc_insights.htm)  
30. Understanding CFDs: Complete introductory guide \- GO Markets, accessed March 5, 2026, [https://www.gomarkets.com/en/articles/introductory-guide-to-cfds](https://www.gomarkets.com/en/articles/introductory-guide-to-cfds)  
31. What Is the Debt Ceiling and Why Does It Matter? | Charles Schwab, accessed March 5, 2026, [https://www.schwab.com/learn/story/what-is-debt-ceiling](https://www.schwab.com/learn/story/what-is-debt-ceiling)  
32. A Pure-Jump Market-Making Model for High-Frequency Trading \- arXiv, accessed March 5, 2026, [https://arxiv.org/pdf/1903.07222](https://arxiv.org/pdf/1903.07222)  
33. Fixed-income dealing and central bank interventions \- Bank of Canada, accessed March 5, 2026, [https://www.bankofcanada.ca/2022/06/staff-analytical-note-2022-9/](https://www.bankofcanada.ca/2022/06/staff-analytical-note-2022-9/)  
34. Treasury Market Dysfunction and the Role of the Central Bank \- Brookings Institution, accessed March 5, 2026, [https://www.brookings.edu/wp-content/uploads/2025/03/4\_Kashyap-et-al.pdf](https://www.brookings.edu/wp-content/uploads/2025/03/4_Kashyap-et-al.pdf)  
35. Jian Yao (x 80406\) \- Georgetown University, accessed March 5, 2026, [https://faculty.georgetown.edu/evansm1/New%20Micro/Yao%20marketmaking%20in%20FX.pdf](https://faculty.georgetown.edu/evansm1/New%20Micro/Yao%20marketmaking%20in%20FX.pdf)  
36. Fiscal Dominance Lurks Behind Uncertain Central-Bank Policies \- MSCI, accessed March 5, 2026, [https://www.msci.com/research-and-insights/blog-post/fiscal-dominance-lurks-behind-uncertain-central-bank-policies](https://www.msci.com/research-and-insights/blog-post/fiscal-dominance-lurks-behind-uncertain-central-bank-policies)  
37. Quasi-Fiscal Implications of Central Bank Crisis Interventions \- IMF, accessed March 5, 2026, [https://www.imf.org/en/publications/wp/issues/2023/06/02/quasi-fiscal-implications-of-central-bank-crisis-interventions-534076](https://www.imf.org/en/publications/wp/issues/2023/06/02/quasi-fiscal-implications-of-central-bank-crisis-interventions-534076)  
38. The spillover effects of economic policy uncertainty on financial markets: a time-varying analysis | Request PDF \- ResearchGate, accessed March 5, 2026, [https://www.researchgate.net/publication/342283466\_The\_spillover\_effects\_of\_economic\_policy\_uncertainty\_on\_financial\_markets\_a\_time-varying\_analysis](https://www.researchgate.net/publication/342283466_The_spillover_effects_of_economic_policy_uncertainty_on_financial_markets_a_time-varying_analysis)  
39. Getting RICH from Carry trading on leverage & hedging with risk reversal strategy \- Reddit, accessed March 5, 2026, [https://www.reddit.com/r/options/comments/1jiocun/getting\_rich\_from\_carry\_trading\_on\_leverage/](https://www.reddit.com/r/options/comments/1jiocun/getting_rich_from_carry_trading_on_leverage/)  
40. Variance Swaps \- Derivatives Academy, accessed March 5, 2026, [https://derivativesacademy.com/storage/uploads/files/modules/resources/1702207867\_allen\_einchcomb\_granger\_jpm\_2006\_variance\_swaps.pdf](https://derivativesacademy.com/storage/uploads/files/modules/resources/1702207867_allen_einchcomb_granger_jpm_2006_variance_swaps.pdf)