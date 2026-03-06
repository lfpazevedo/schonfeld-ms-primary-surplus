# **Strategic Management of Interest Rate Term Structures in the Brazilian Market: Dynamics, Instruments, and Steepening Tactics**

The Brazilian financial market is recognized globally for its high degree of technical sophistication, particularly in the realm of interest rate derivatives. At the core of this environment lies the forward curve—a mathematical and psychological representation of the market's collective expectations regarding the future trajectory of the Interbank Deposit (DI) rate. For portfolio managers, the ability to navigate, interpret, and trade this curve is not merely a technical requirement but a strategic necessity, as interest rate risk remains the primary driver of volatility and return in the Brazilian fixed-income landscape.1 Trading the curve requires a deep understanding of the two primary instruments used for local interest rate exposure: the One-Day Interbank Deposit Futures (DI1) and the Pre-DI Swap. While both serve to express views on the term structure, their operational, structural, and fiscal differences dictate their utility in varying market conditions.

## **The Institutional Architecture of the Brazilian Interest Rate Complex**

To understand the forward curve, one must first understand the underlying benchmark: the DI rate. The DI rate, or CDI (Certificado de Depósito Interfinanceiro), is calculated by B3 based on the weighted average of one-day interbank loans conducted at a fixed rate and registered on the B3 platform.3 This rate serves as the operational heart of the private financial sector, tracking the Selic Over rate—the Central Bank's target rate—with remarkable precision. Because the Selic is determined by the Monetary Policy Committee (COPOM) only every 45 days, the DI1 futures market acts as a real-time "oracle," discounting future policy moves long before they are officially announced.2  
The forward curve, specifically the PRE curve (Nominal Interest Rate curve), is constructed by mapping the settlement prices of DI1 futures across various maturities. This curve represents the market's expectation for the accumulated interest rate from the present until a given future date, inclusive of risk premia and inflation expectations.1 In a market characterized by historically high real interest rates and frequent fiscal volatility, the Brazilian curve is often more liquid and reactive than the underlying cash market for government bonds.2

### **The DI1 Future: The Flagship Instrument of B3**

The One-Day Interbank Deposit Future (DI1) is the most heavily traded interest rate derivative in Brazil. It possesses several unique characteristics that distinguish it from international counterparts like SOFR or Euribor futures. Primarily, the DI1 trades in terms of an annualized interest rate rather than a price index.7 However, the actual financial settlement of the contract is performed using a Unitary Price (PU), which represents the present value of BRL 100,000 at the contract's maturity, discounted by the traded rate.6  
The mathematical relationship between the quoted rate and the PU is essential for any portfolio manager's risk calculations. The PU is defined as follows:

$$PU \= \\frac{100,000}{(1 \+ r)^{\\frac{DU}{252}}}$$  
In this formula, $r$ represents the effective annual interest rate, and $DU$ represents the number of business days between the trading date and the expiration date.8 The denominator $252$ reflects the standard Brazilian day count convention, which assumes 252 business days per year.6 Because the DI1 is a "short" interest rate instrument, a position that is "long" the PU (Applied/Aplicado) profits when interest rates fall, while a position that is "short" the PU (Taken/Tomado) profits when rates rise.2  
An operational nuance of the DI1 is the daily variation margin. Unlike many OTC products, the DI1 is marked-to-market daily, with profits and losses settled in cash on the following business day.6 Furthermore, B3 applies a "correction rate" to the previous day's settlement price to account for the actual DI rate realized overnight. This mechanism ensures that the contract accurately reflects the difference between the expected future rate and the realized overnight rate, effectively isolating the term risk from the overnight carry.7

| Specification | Details of the DI1 Contract |
| :---- | :---- |
| **Ticker** | DI1 8 |
| **Underlying** | Average One-Day Interbank Deposit Rate (DI) 8 |
| **Price Quotation** | Annualized interest rate, 252 business day basis 8 |
| **Contract Value** | BRL 100,000 at maturity 5 |
| **Minimum Tick Size** | 0.001 (up to 3m), 0.005 (3m to 60m), 0.010 (above 60m) 8 |
| **Settlement Type** | Daily cash variation margin 6 |
| **Expirations** | First business day of every month 8 |

Significant regulatory updates in July 2025 further refined the contract's granularity. Circular Letter 034/2025-PRE introduced a reduction in the tick size for maturities exceeding 60 months from 0.010% to 0.005%, aligning long-dated contracts with the medium-term segment to enhance price discovery in the back end of the curve.8

### **The Pre-DI Swap: Structural Customization and OTC Dynamics**

While the DI1 future provides liquidity and standardization, the Pre-DI Swap offers customization and a different settlement profile. A Pre-DI Swap is a fixed-floating instrument where the "Pre" leg pays a fixed rate and the "DI" leg pays the accumulated daily CDI rate over the swap's tenor.10 The most significant structural difference is that Brazilian swaps are typically characterized by a single payment at maturity rather than periodic coupon exchanges.10  
The valuation of the fixed leg follows a compounding logic similar to the DI1:

$$Value\_{Fixed} \= Notional \\times (1 \+ k)^{\\frac{n}{252}}$$  
where $k$ is the fixed rate and $n$ is the business day count.10 The floating leg is the capitalization of actual DI rates:

$$Value\_{Floating} \= Notional \\times \\prod\_{i=0}^{n-1} (1 \+ DI\_i)^{\\frac{1}{252}}$$  
Portfolio managers often utilize swaps when they need to match the specific cash flow dates of a private credit asset or a corporate liability that does not align with the standard first-business-day-of-the-month maturity of the DI1 futures.7 However, swaps are generally less liquid than futures and are subject to counterparty credit risk, although most are registered with the B3 clearinghouse to mitigate this.10

## **Comparative Analysis: Selection Criteria for Curve Exposure**

The choice between using DI1 futures or Pre-DI swaps is driven by four primary factors: liquidity, capital efficiency, accounting treatment, and taxation.

### **Liquidity and Execution Management**

DI1 futures are the undisputed leaders in liquidity. The "Januaries" (F) and "Julys" (N) are the primary benchmarks, and the market can absorb massive volumes without significant slippage.6 For a manager executing a rapid "tactical" steepening trade in response to a fiscal announcement, the DI1 is the only viable option. Swaps, being OTC, require bilateral negotiation or the use of a broker, which can result in wider bid-ask spreads and slower execution.7

### **Capital and Margin Considerations**

The DI1's daily variation margin requires constant cash flow management. If a fund is "Taken" (shorting PU) and rates fall, it must settle the loss in cash the next day.6 This can lead to "liquidity drag" or the need to maintain a buffer in highly liquid repo markets. Swaps, if structured with settlement at maturity, preserve cash during the trade's life, which can be advantageous for long-term strategic positions where the manager wants to avoid the volatility of daily cash flows.10

### **Taxation and the 2025-2026 Regulatory Shifts**

Taxation in Brazil is complex and highly dynamic. For domestic investment funds, gains on DI1 futures are generally subject to a 15% rate, whereas swaps can fall under a regressive table (22.5% to 15%) depending on the maturity.15 However, the most critical developments for portfolio managers in 2025 and 2026 relate to the Tax on Financial Operations (IOF).  
Recent government decrees (No. 12,466, 12,467, and 12,499) and Provisional Measure 1,303/2025 have significantly altered the IOF landscape for credit and exchange-linked transactions.17 While derivatives used for hedging are often eligible for a zero-rate IOF, speculative swap positions can attract significant tax burdens if redeemed within 30 days, following a regressive scale from 96% down to 0%.15 Furthermore, for non-resident investors (operating under Resolution 4373), DI1 futures are often preferred due to their clear exemption or reduced rate status compared to the more nuanced tax treatment of certain OTC swap structures.20

| Feature | DI1 Future (B3) | Pre-DI Swap (OTC/B3) |
| :---- | :---- | :---- |
| **Market Venue** | Centralized Exchange 8 | OTC Registered with CCP 10 |
| **Settlement** | Daily Cash Variation 6 | Typically at Maturity 10 |
| **Liquidity** | Extremely High (Benchmarks) 2 | Moderate to Low 7 |
| **Flexibility** | Standardized Maturities 8 | Highly Customizable 7 |
| **Capital Use** | Daily Margining 8 | Collateralized (CSAs) 10 |

## **Technical Construction of the Forward Curve**

The construction of the "D-Curve" or PRE curve is the starting point for any relative value analysis. This curve is built using the settlement rates of DI1 futures, but because futures only exist for specific dates, the market relies on sophisticated interpolation methods to derive rates for any arbitrary point in time.1

### **The Flat-Forward 252 Interpolation Method**

The standard methodology endorsed by B3 and used by the vast majority of Brazilian financial institutions is the **Flat-Forward Interpolation** on a 252-business-day basis.22 The fundamental assumption of this method is that the forward rate is constant between any two observable market vertices. If the curve has a vertex at 3 months ($r\_1$) and another at 6 months ($r\_2$), the rate for a 4-month maturity ($r\_i$) is calculated such that the implied forward rate between 3 and 4 months is identical to the forward rate between 4 and 6 months.22  
The mathematical formula for the interpolated rate ($r\_i$) is:

$$(1 \+ r\_i)^{\\frac{DU\_i}{252}} \= (1 \+ r\_a)^{\\frac{DU\_a}{252}} \\times \\left^{\\frac{DU\_i \- DU\_a}{DU\_p \- DU\_a}}$$  
where $DU\_a$ and $DU\_p$ are the business days to the anterior and posterior vertices, respectively.22 This method is preferred over linear interpolation because it maintains the continuity of the discount function and avoids creating artificial "sawtooth" volatility in the forward rate curve.26

### **Advanced Modeling: Nelson-Siegel Factors**

For strategic forecasting and principal component analysis (PCA), many managers utilize the **Nelson-Siegel (NS)** framework to decompose the curve into three latent factors:

1. **Level ($\\beta\_0$):** Reflects the long-term interest rate, which in Brazil is heavily influenced by the fiscal regime and the structural real interest rate.28  
2. **Slope ($\\beta\_1$):** Captures the difference between short and long-term rates. A negative $\\beta\_1$ typically indicates a steep curve, while a value near zero suggests a flat or inverted curve.28  
3. **Curvature ($\\beta\_2$):** Represents the medium-term "hump," often reflecting the market's expectation of the peak or trough of a monetary policy cycle.28

Research indicates that the use of a Kalman filter to estimate these factors simultaneously, rather than a two-step regression, provides more accurate short-term forecasts for the Brazilian term structure.29 Furthermore, incorporating forward-looking macroeconomic variables into a Factor-Augmented VAR (FAVAR) model has been shown to reduce forecast errors by 15% to 40% compared to a simple random walk model.28

## **Mechanics of the Steepening Trade**

A "steepener" is a trade that profits when the yield spread between a long-term interest rate and a short-term interest rate widens. In the Brazilian market, this is a core strategy used by hedge funds (Multimercados) to express views on both monetary policy and fiscal sustainability.2

### **The Two Faces of Steepening: Bull and Bear**

Portfolio managers must distinguish between the two primary drivers of a steeper curve, as they require different positioning and carry different risks.  
**The Bull Steepener:** This occurs when short-term rates fall faster than long-term rates. It is the classic "recession trade" or "easing cycle trade".32 When the Central Bank signals that it will cut the Selic rate, the front end of the curve (e.g., the 1-year vertex) drops immediately. However, the long end (e.g., the 10-year vertex) may drop more slowly or remain stable if the market fears that the rate cuts will be inflationary in the long run.32  
**The Bear Steepener:** This occurs when long-term rates rise faster than short-term rates. This is the "fiscal risk trade" or "inflation scare trade".32 In this scenario, the front end might be anchored by the current Selic rate, but the back end rises as investors demand a higher "term premium" to hold long-term Brazilian debt.32 Bear steepenings from an inverted curve are historically rare and often signal the onset of a recession or a major shift in the country's risk perception.37

### **Execution Jargon: "Tomado" vs. "Aplicado"**

In the Brazilian pit (or its modern electronic equivalent), the following terms are universal:

* **Aplicado (Applied/Receiving):** Buying the PU \= Expecting rates to fall. The manager "receives" the fixed rate and "pays" the floating DI.2  
* **Tomado (Taken/Paying):** Selling the PU \= Expecting rates to rise. The manager "pays" the fixed rate and "receives" the floating DI.2

To execute a **Steepener**, a manager will:

1. **Aplicado no Curto (Applied in the short end):** Receive rates in a front-end contract (e.g., DI1F25).  
2. **Tomado no Longo (Taken in the long end):** Pay rates in a back-end contract (e.g., DI1F29).33

| Strategy | Front Leg Position | Back Leg Position | Market Outlook |
| :---- | :---- | :---- | :---- |
| **Bull Steepener** | Applied (Buy PU) | Taken (Sell PU) | Aggressive rate cuts expected 32 |
| **Bear Steepener** | Applied (Buy PU) | Taken (Sell PU) | Fiscal risk or inflation rising 32 |
| **Bull Flattener** | Taken (Sell PU) | Applied (Buy PU) | Long-term yields falling on disinflation 32 |
| **Bear Flattener** | Taken (Sell PU) | Applied (Buy PU) | Aggressive rate hikes expected 32 |

### **B3 Structured Operations: DII and DIF**

To simplify these complex trades, B3 offers **Structured Operations** that allow for the simultaneous execution of both legs at a predetermined spread.

* **Slope Strategy (DII):** This allows the trader to buy one maturity and sell another in a single transaction. This is crucial for managing "leg risk"—the danger that the market moves between the execution of the first and second legs, ruining the intended spread.8  
* **Forward Rate Agreement on DI (DIF):** This trades the "forward-forward" rate. For example, a DIF can allow a manager to trade the 3-month rate starting 6 months from now. It is a pure bet on the future shape of a specific segment of the curve.8

## **Risk Management: The Imperative of DV01 Neutrality**

A critical mistake for novice traders is to trade an equal number of contracts on both legs of a steepener. Because long-term contracts have a much higher sensitivity to rate changes, an equal-weight trade is not a bet on the curve's slope, but a massive directional bet on the long end.39 To isolate the curve risk, managers use the **DV01** (Dollar Value of a Basis Point), also known as **PV01** (Price Value of a Basis Point).41

### **The DV01 Calculation**

DV01 measures the change in the PU for a 1 basis point (0.01%) move in the rate. For the DI1, it is roughly proportional to the duration of the contract.

$$DV01 \= \\left| PU(r) \- PU(r \+ 0.0001) \\right|$$  
Because the relationship is non-linear, the DV01 of a 10-year contract is significantly higher than that of a 2-year contract.41 To achieve a **duration-neutral** or **DV01-neutral** steepener, the manager must calculate the **Hedge Ratio (HR)** 39:

$$HR \= \\frac{DV01\_{LongLeg}}{DV01\_{ShortLeg}}$$  
If the 10-year contract has a DV01 of BRL 71.16 and the 2-year contract has a DV01 of BRL 34.36, the ratio is approximately 2.07.39 The manager would need to be "Applied" in 2,070 contracts of the 2-year for every 1,000 contracts they are "Taken" in the 10-year. This weighting ensures that if the entire curve moves up by 1 bp (a parallel shift), the position's net P\&L is zero. The manager only makes money if the 10-year rate rises *more* than the 2-year rate (steepening).38

### **Convexity and PCA Weighting**

Sophisticated managers often go beyond simple DV01 neutrality. They may use **Principal Component Analysis (PCA)** to weight their legs based on how the curve historically moves. The second principal component typically represents the "Slope." By weighting the legs such that the first principal component (the "Level") is minimized, the manager can more accurately target the steepening move.42 Furthermore, long-dated DI1 contracts have significant **Convexity**, meaning they gain more when rates fall than they lose when rates rise by the same amount. In volatile environments, "buying convexity" can be an additional source of alpha.44

## **Macroeconomic Drivers of the Brazilian Term Structure**

The Brazilian curve is not a closed system; it is deeply influenced by several exogenous and endogenous variables that portfolio managers monitor via terminals like Bloomberg or local platforms like Broadcast and Enfoque.2

### **The IPCA-Nominal Spread: Break-even Inflation**

The PRE curve (Nominal) can be compared to the DIC curve (Real Interest Rate/Cupom de IPCA) to derive the **Break-even Inflation**.1 The DIC curve is derived from IPCA-indexed futures (DAP).1

$$Implied Inflation \\approx r\_{nominal} \- r\_{real}$$  
In Brazil, inflation expectations are often unanchored due to fiscal uncertainty. If a manager believes the IPCA prints will exceed the market's forecast, they will enter a "Break-even trade" by being "Taken" in the DI1 and "Applied" in the DAP.1

### **The Cupom Cambial (DOC Curve) and FX Arbitrage**

The **DOC Curve** represents the interest rate differential between the Brazilian Real (BRL) and the U.S. Dollar (USD), known as the **Cupom Cambial**.1 This curve is vital for pricing FX forwards and swaps. It is derived from the "Dirty Cupom" (DDI futures) and the spot USD/BRL rate. When offshore dollar liquidity tightens, the DOC curve often spikes, leading to an inversion of the local FX-linked curve even if the nominal DI curve remains steep.1

### **Fiscal Dominance and the Term Premium**

The back end of the Brazilian curve is a direct reflection of the "Fiscal Risk Premium." Unlike the front end, which is controlled by the COPOM, the 10-year rate is dictated by the market's perception of the government's ability to service its debt.2 When the debt-to-GDP ratio projections rise, the long end of the curve "opens" (rates rise), leading to a Bear Steepener. Portfolio managers often use the spread between the 10-year NTN-F (fixed-rate bond) and the DI1 future as a measure of "basis risk" between the cash and futures markets.6

## **Professional Software and Infrastructure**

To manage these positions, Brazilian portfolio managers utilize a specific stack of professional tools:

1. **Bloomberg:** The global standard for relative value, cross-country comparisons, and monitoring the WIRP (World Interest Rate Probability) function for COPOM expectations.45  
2. **ProfitChart (Nelogica):** The dominant platform for local DI1 execution. It includes advanced "Interest Rate Curve" modules that allow for real-time visualization of the PRE, DIC, and DOC curves.4  
3. **B3 CALC:** An official pricing engine provided by B3 that ensures managers are using the same PU and day-count calculations as the exchange's clearinghouse.48  
4. **Broadcast and Enfoque:** Local real-time news and data services that provide the fastest updates on fiscal announcements and COPOM communications.2  
5. **rb3 (R Package):** A tool increasingly used by quantitative researchers to fetch historical B3 data, build interpolation models, and backtest curve strategies.1

## **Conclusion: Strategic Synthesis for the Portfolio Manager**

Trading the forward curve in Brazil is a high-stakes exercise in reconciling technical mechanics with macroeconomic intuition. The DI1 future provides the liquid, standardized "scalpel" needed for precision trades, while the Pre-DI swap offers the customized "hammer" for structural hedging.2  
Successful steepening strategies require:

* **Technical Rigor:** Correctly calculating DV01 ratios and using Flat-Forward interpolation to identify mispriced segments of the curve.22  
* **Macroeconomic Clarity:** Distinguishing between a Bull Steepener (driven by monetary easing) and a Bear Steepener (driven by fiscal risk).32  
* **Execution Excellence:** Utilizing structured operations like DII and DIF to minimize slippage and operational risk.8  
* **Fiscal Awareness:** Navigating the shifting sands of 2025-2026 taxation reforms (IOF/IR) to ensure that gross alphas are not erased by tax liabilities.17

In the Brazilian context, the forward curve is more than a line on a chart; it is a living document of the nation's economic health. For the portfolio manager, it remains the ultimate arena for generating absolute returns in one of the world's most dynamic financial markets.1

#### **Works cited**

1. Fetching B3 Yield Curves \- CRAN, accessed March 6, 2026, [https://cran.r-project.org/web/packages/rb3/vignettes/Fetching-historical-yield-curve.html](https://cran.r-project.org/web/packages/rb3/vignettes/Fetching-historical-yield-curve.html)  
2. O Oráculo da Faria Lima: DI1 e o que ele diz sobre o futuro do seu dinheiro | Investing.com, accessed March 6, 2026, [https://br.investing.com/analysis/o-oraculo-da-faria-lima-di1-e-o-que-ele-diz-sobre-o-futuro-do-seu-dinheiro-200474740](https://br.investing.com/analysis/o-oraculo-da-faria-lima-di1-e-o-que-ele-diz-sobre-o-futuro-do-seu-dinheiro-200474740)  
3. DI Rate \- Cbonds, accessed March 6, 2026, [https://cbonds.com/glossary/di-rate/](https://cbonds.com/glossary/di-rate/)  
4. DI1: conheça o contrato futuro da taxa DI \- Melver, accessed March 6, 2026, [https://www.melver.com.br/blog/di1-conheca-o-contrato-futuro-da-taxa-di/](https://www.melver.com.br/blog/di1-conheca-o-contrato-futuro-da-taxa-di/)  
5. One day Interbank Deposit Rate Futures Prices \- Investing.com, accessed March 6, 2026, [https://www.investing.com/rates-bonds/one-day-interbank-deposit-rate](https://www.investing.com/rates-bonds/one-day-interbank-deposit-rate)  
6. Brazilian DI1 Interest Rate Futures \- EconBiz, accessed March 6, 2026, [https://www.econbiz.de/Record/brazilian-di1-interest-rate-futures-burgess-nicholas/10013290373](https://www.econbiz.de/Record/brazilian-di1-interest-rate-futures-burgess-nicholas/10013290373)  
7. Accessing the opportunities in Brazil's capital markets \- Acuiti, accessed March 6, 2026, [https://www.acuiti.io/wp-content/uploads/2021/10/B3-Report.pdf](https://www.acuiti.io/wp-content/uploads/2021/10/B3-Report.pdf)  
8. Circular Letter, accessed March 6, 2026, [https://docs.publicnow.com/viewDoc.aspx?filename=37147\\EXT\\5AA0B3A5A2F6FBEBEB19F7D2BFA506E861E7315A\_33363D29C8F532407FF862C40110165D80B23498.PDF](https://docs.publicnow.com/viewDoc.aspx?filename=37147%5CEXT%5C5AA0B3A5A2F6FBEBEB19F7D2BFA506E861E7315A_33363D29C8F532407FF862C40110165D80B23498.PDF)  
9. Trading on B3 overview, accessed March 6, 2026, [https://library.tradingtechnologies.com/trade/b3-trading-on-b3-overview.html](https://library.tradingtechnologies.com/trade/b3-trading-on-b3-overview.html)  
10. Brazilian Swaps \- OpenGamma, accessed March 6, 2026, [https://quant.opengamma.io/Brazilian-Swaps-OpenGamma.pdf](https://quant.opengamma.io/Brazilian-Swaps-OpenGamma.pdf)  
11. S\&P/B3 Futures Indices, accessed March 6, 2026, [https://www.spglobal.com/spdji/pt/documents/methodologies/methodology-sp-b3-futures-indices.pdf](https://www.spglobal.com/spdji/pt/documents/methodologies/methodology-sp-b3-futures-indices.pdf)  
12. How to Compute Historical Rates from B3 Future Prices \- CRAN, accessed March 6, 2026, [https://cran.r-project.org/web/packages/rb3/vignettes/Fetching-historical-future-rates.html](https://cran.r-project.org/web/packages/rb3/vignettes/Fetching-historical-future-rates.html)  
13. CIRCULAR LETTER, accessed March 6, 2026, [https://docs.publicnow.com/viewDoc.aspx?filename=37147\\EXT\\FA26AE18B51D1E928CF851449A9F5A15EBAEFA36\_F978DC4CD080184AF61C15CE8320138656C18C3B.PDF](https://docs.publicnow.com/viewDoc.aspx?filename=37147%5CEXT%5CFA26AE18B51D1E928CF851449A9F5A15EBAEFA36_F978DC4CD080184AF61C15CE8320138656C18C3B.PDF)  
14. Contratos Futuros de DI \- Depósitos Interfinanceiros \- Nelogica Sistemas de Software, accessed March 6, 2026, [https://ajuda.nelogica.com.br/hc/pt-br/articles/12218382561051-Contratos-Futuros-de-DI-Dep%C3%B3sitos-Interfinanceiros](https://ajuda.nelogica.com.br/hc/pt-br/articles/12218382561051-Contratos-Futuros-de-DI-Dep%C3%B3sitos-Interfinanceiros)  
15. Fundos de Investimento: como funciona a tributação e quais impostos incidem \- Tax Group, accessed March 6, 2026, [https://www.taxgroup.com.br/intelligence/fundos-de-investimento-como-funciona-a-tributacao-e-quais-impostos-incidem/](https://www.taxgroup.com.br/intelligence/fundos-de-investimento-como-funciona-a-tributacao-e-quais-impostos-incidem/)  
16. Tributação no Mercado Financeiro e de Capitais, accessed March 6, 2026, [https://b3uxprod.service-now.com/sys\_attachment.do?sys\_id=e42ae00d1bd645d00418a750f54bcb23\&sysparm\_this\_url=kb\_knowledge.do?sys\_id=6ff9e0c91bd645d00418a750f54bcb81\&sysparm\_record\_list=ORDERBYDESCsys\_created\_on\&sysparm\_record\_row=1\&sysparm\_record\_rows=1459\&sysparm\_record\_target=kb\_knowledge](https://b3uxprod.service-now.com/sys_attachment.do?sys_id=e42ae00d1bd645d00418a750f54bcb23&sysparm_this_url=kb_knowledge.do?sys_id%3D6ff9e0c91bd645d00418a750f54bcb81&sysparm_record_list=ORDERBYDESCsys_created_on&sysparm_record_row=1&sysparm_record_rows=1459&sysparm_record_target=kb_knowledge)  
17. Tax Law Highlights | Brazil's Tax on Financial Transactions (IOF) Issues \- Mayer Brown, accessed March 6, 2026, [https://www.mayerbrown.com/en/insights/publications/2025/10/tax-law-highlights--brazils-tax-on-financial-transactions-iof-issues](https://www.mayerbrown.com/en/insights/publications/2025/10/tax-law-highlights--brazils-tax-on-financial-transactions-iof-issues)  
18. Brazilian Government announces substantial tax changes affecting Interest on Net Equity, financial investments, betting operations and IOF regulations | EY \- Global, accessed March 6, 2026, [https://www.ey.com/en\_gl/technical/tax-alerts/brazilian-government-announces-substantial-tax-changes-affecting-interest-on-net-equity-financial-investments-betting-operations-and-iof-regulations](https://www.ey.com/en_gl/technical/tax-alerts/brazilian-government-announces-substantial-tax-changes-affecting-interest-on-net-equity-financial-investments-betting-operations-and-iof-regulations)  
19. Brazilian government changes rules for tax on financial transactions (IOF) \- Mattos Filho, accessed March 6, 2026, [https://www.mattosfilho.com.br/en/unico/government-changes-rules-iof/](https://www.mattosfilho.com.br/en/unico/government-changes-rules-iof/)  
20. Brazil: Understanding the Tax on Financial Operations (IOF) \- International Tax Review, accessed March 6, 2026, [https://www.internationaltaxreview.com/article/2a68rfy5bw2ycq128bf1b/brazil-understanding-the-tax-on-financial-operations-iof](https://www.internationaltaxreview.com/article/2a68rfy5bw2ycq128bf1b/brazil-understanding-the-tax-on-financial-operations-iof)  
21. Brazilian government adjusts IOF and amends rules on financial income taxation, accessed March 6, 2026, [https://www.mattosfilho.com.br/en/unico/government-adjusts-iof/](https://www.mattosfilho.com.br/en/unico/government-adjusts-iof/)  
22. Objeto de curva de juros com interpolação e extrapolação Flat Forward em Python \- Medium, accessed March 6, 2026, [https://medium.com/@milton-rocha/objeto-de-curva-de-juros-com-interpola%C3%A7%C3%A3o-e-extrapola%C3%A7%C3%A3o-flat-forward-em-python-48b58d9d59e3](https://medium.com/@milton-rocha/objeto-de-curva-de-juros-com-interpola%C3%A7%C3%A3o-e-extrapola%C3%A7%C3%A3o-flat-forward-em-python-48b58d9d59e3)  
23. Manual de Apreçamento \- BNY, accessed March 6, 2026, [https://www.bny.com/content/dam/bnymellon/documents/pdf/brazil/manual-de-apre%C3%A7amento.pdf](https://www.bny.com/content/dam/bnymellon/documents/pdf/brazil/manual-de-apre%C3%A7amento.pdf)  
24. Manual de Curvas Financeiras B3 | PDF | Métodos e Materiais de Ensino \- Scribd, accessed March 6, 2026, [https://pt.scribd.com/document/666377427/Manual-de-Curvas](https://pt.scribd.com/document/666377427/Manual-de-Curvas)  
25. Manual de Curvas da B3 | PDF | Juros | Swap (finanças) \- Scribd, accessed March 6, 2026, [https://pt.scribd.com/document/862891406/Modelo-de-curvas-B3](https://pt.scribd.com/document/862891406/Modelo-de-curvas-B3)  
26. Linear and Flat forward interpolation with cash dividends \- Chase the Devil, accessed March 6, 2026, [https://chasethedevil.github.io/post/linear\_flat\_forward\_interpolation/](https://chasethedevil.github.io/post/linear_flat_forward_interpolation/)  
27. Interpolation Methods for Curve Construction \- Deriscope, accessed March 6, 2026, [https://www.deriscope.com/docs/Hagan\_West\_curves\_AMF.pdf](https://www.deriscope.com/docs/Hagan_West_curves_AMF.pdf)  
28. Forecasting the Brazilian Yield Curve Using Forward- Looking Variables, accessed March 6, 2026, [https://repositorio.fgv.br/bitstreams/24da9f7c-6bf8-416f-b697-0cbec4b74e24/download](https://repositorio.fgv.br/bitstreams/24da9f7c-6bf8-416f-b697-0cbec4b74e24/download)  
29. Efficient Yield Curve Estimation and Forecasting in Brazil \- ResearchGate, accessed March 6, 2026, [https://www.researchgate.net/publication/227367981\_Efficient\_Yield\_Curve\_Estimation\_and\_Forecasting\_in\_Brazil](https://www.researchgate.net/publication/227367981_Efficient_Yield_Curve_Estimation_and_Forecasting_in_Brazil)  
30. efficient interest rate curve estimation and forecasting in brazil \- Lume UFRGS, accessed March 6, 2026, [https://lume.ufrgs.br/bitstream/handle/10183/30427/000732581.pdf?sequence=1\&isAllowed=y](https://lume.ufrgs.br/bitstream/handle/10183/30427/000732581.pdf?sequence=1&isAllowed=y)  
31. Forecasting the Brazilian yield curve using forward-looking variables \- IDEAS/RePEc, accessed March 6, 2026, [https://ideas.repec.org/a/eee/intfor/v33y2017i1p121-131.html](https://ideas.repec.org/a/eee/intfor/v33y2017i1p121-131.html)  
32. Beware the bear (steepener) | AJ Bell Investcentre, accessed March 6, 2026, [https://www.investcentre.co.uk/articles/beware-bear-steepener](https://www.investcentre.co.uk/articles/beware-bear-steepener)  
33. Yield Curve Spread Trades: Opportunities & Applications \- CME, accessed March 6, 2026, [https://www.cmegroup.com/education/files/yield-curve-spread-trades.pdf](https://www.cmegroup.com/education/files/yield-curve-spread-trades.pdf)  
34. Yield Curve Dynamics: Impact on Markets and Trading Strategies \- Bookmap, accessed March 6, 2026, [https://bookmap.com/blog/yield-curve-dynamics-impact-on-markets-and-trading-strategies](https://bookmap.com/blog/yield-curve-dynamics-impact-on-markets-and-trading-strategies)  
35. All About Yield Curves, Bulls and Bears | Bond Investment Mentor, accessed March 6, 2026, [https://bondinvestmentmentor.com/all-about-yield-curves-bulls-and-bears/](https://bondinvestmentmentor.com/all-about-yield-curves-bulls-and-bears/)  
36. What Investors Need to Know About the Steepening Yield Curve | Morningstar Europe, accessed March 6, 2026, [https://global.morningstar.com/en-eu/markets/what-investors-need-know-about-steepening-yield-curve](https://global.morningstar.com/en-eu/markets/what-investors-need-know-about-steepening-yield-curve)  
37. The message from bond bear steepening \- Janus Henderson Investors \- US Institutional, accessed March 6, 2026, [https://www.janushenderson.com/en-us/institutional/article/the-message-from-bond-bear-steepening/](https://www.janushenderson.com/en-us/institutional/article/the-message-from-bond-bear-steepening/)  
38. Yield Curve Shifts Create Trading Opportunities \- CME, accessed March 6, 2026, [https://www.cmegroup.com/trading/interest-rates/files/Yield\_Curve\_Strategy\_Paper.pdf](https://www.cmegroup.com/trading/interest-rates/files/Yield_Curve_Strategy_Paper.pdf)  
39. Fixed Income Update: Trading the Treasury Yield Curve \- Saxo Bank, accessed March 6, 2026, [https://www.home.saxo/content/articles/bonds/fixed-income-update-2023-04-04-04042023](https://www.home.saxo/content/articles/bonds/fixed-income-update-2023-04-04-04042023)  
40. A MELHOR ESTRATÉGIA para investir em ações no LONGO PRAZO Ramiro Responde \#49 \- YouTube, accessed March 6, 2026, [https://www.youtube.com/watch?v=qZR2v74OYto](https://www.youtube.com/watch?v=qZR2v74OYto)  
41. One-Factor Risk Metrics and Hedges | AnalystPrep \- FRM Part 1 Study Notes, accessed March 6, 2026, [https://analystprep.com/study-notes/frm/part-1/valuation-and-risk-management/one-factor-risk-metrics-and-hedges/](https://analystprep.com/study-notes/frm/part-1/valuation-and-risk-management/one-factor-risk-metrics-and-hedges/)  
42. How would I price out and set up a steepening yield curve strategy in which Im long 5yr UST and short 30yr UST futures \[closed\], accessed March 6, 2026, [https://quant.stackexchange.com/questions/68347/how-would-i-price-out-and-set-up-a-steepening-yield-curve-strategy-in-which-im-l](https://quant.stackexchange.com/questions/68347/how-would-i-price-out-and-set-up-a-steepening-yield-curve-strategy-in-which-im-l)  
43. DV01 \- Meaning, Formula, Examples, Advantages \- WallStreetMojo, accessed March 6, 2026, [https://www.wallstreetmojo.com/dv01/](https://www.wallstreetmojo.com/dv01/)  
44. CALCULATING THE DOLLAR VALUE OF A BASIS POINT \- CME Group, accessed March 6, 2026, [https://www.cmegroup.com/trading/interest-rates/files/Calculating\_the\_Dollar\_Value\_of\_a\_Basis\_Point\_Final\_Dec\_4.pdf](https://www.cmegroup.com/trading/interest-rates/files/Calculating_the_Dollar_Value_of_a_Basis_Point_Final_Dec_4.pdf)  
45. Hedge Funds | Bloomberg Professional Services, accessed March 6, 2026, [https://professional.bloomberg.com/solutions/hedge-funds/](https://professional.bloomberg.com/solutions/hedge-funds/)  
46. Charts | Bloomberg Professional Services, accessed March 6, 2026, [https://www.bloomberg.com/professional/products/bloomberg-terminal/charts/](https://www.bloomberg.com/professional/products/bloomberg-terminal/charts/)  
47. Brazilian Pricing Models \- Everysk Support, accessed March 6, 2026, [https://support.everysk.com/hc/en-us/articles/360058417193-Brazilian-Pricing-Models](https://support.everysk.com/hc/en-us/articles/360058417193-Brazilian-Pricing-Models)  
48. What you need to know about FUTURE INTEREST RATES \- Part 2 ..., accessed March 6, 2026, [https://www.youtube.com/watch?v=w9vBYWCQNbQ](https://www.youtube.com/watch?v=w9vBYWCQNbQ)  
49. CALC Powered by B3, accessed March 6, 2026, [https://calculadorarendafixa.com.br/](https://calculadorarendafixa.com.br/)