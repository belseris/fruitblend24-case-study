# FruitBlend24 — Analyst Case Study (Atmind Group, Revenue / Data Analyst Intern)

## เป้าหมายของโปรเจกต์
วิเคราะห์ข้อมูล 12 เดือนของแบรนด์สมูทตี้ออนไลน์ FruitBlend24 แล้วให้คำแนะนำเพิ่มกำไรและจัดการสต็อก
ส่งงานเป็น Streamlit app + GitHub repo + P&L xlsx + approach note
ผู้ใช้กำลังเรียนรู้งานนี้ตามบทเรียน 14 บท (บท 1–14) เพื่อสมัครฝึกงาน และต้องอธิบายทุกตัวเลขได้เองตอนสัมภาษณ์

## วิธีทำงานกับผู้ใช้ (สำคัญ)
- คุยและอธิบายกับผู้ใช้ในแชตเป็นภาษาไทยแบบเข้าใจง่าย ไม่เป็นทางการเกินไป ทีละขั้น
- โหมดสอน: หลังทำแต่ละขั้นเสร็จ อธิบายเป็นภาษาไทยว่าทำไมทำแบบนี้ และตัวเลขที่ได้แปลว่าอะไร ถ้าผู้ใช้ขอให้ทดสอบ ให้ถามทีละข้อแล้วรอคำตอบ
- ทุกไฟล์ที่ขึ้น GitHub เป็นภาษาอังกฤษทั้งหมด: คอมเมนต์ในโค้ด, markdown ใน notebook, docs/decisions.md, README, ข้อความในแอป
- คอมเมนต์ภาษาอังกฤษต้องสั้นและง่าย (ระดับ B1): ประโยคสั้น คำศัพท์พื้นฐาน บอก "why" ไม่ใช่แค่ "what" ผู้ใช้ภาษาอังกฤษยังไม่แข็ง
- หลังเขียนโค้ดหรือ notebook ใหม่ ให้สรุปในแชตเป็นภาษาไทยว่าแต่ละส่วนทำอะไร และแปลคำศัพท์เทคนิคที่ใช้ในคอมเมนต์
- โน้ตเรียนรู้ภาษาไทยของผู้ใช้อยู่ใน `notes/` (ไม่ขึ้น GitHub) ถ้าผู้ใช้ขอ ให้เขียนคำอธิบายภาษาไทยลงที่นั่น ห้ามใส่ภาษาไทยในไฟล์ที่จะส่ง
- หัวกราฟในแอปเขียนเป็นข้อสรุป (action title)
- ให้ไฟล์โค้ดที่ครบและรันได้ ไม่ใช่ snippet ครึ่ง ๆ
- ก่อนตัดสินใจเรื่องที่เป็น judgment call (ลบข้อมูล, นิยาม gross profit, โค้ดราคาปกติ, เลือกโมเดล) ให้เสนอทางเลือกและเหตุผลให้ผู้ใช้เลือกก่อน
- ทุกครั้งที่ตัดสินใจหรือตั้ง assumption ให้เพิ่ม 1 บรรทัดภาษาอังกฤษใน `docs/decisions.md` (Date | Lesson | Decision | Reason | Impact) แล้วแปลบรรทัดนั้นเป็นไทยในแชตให้ผู้ใช้ตรวจ
- หลังคำนวณเสร็จ ต้องแสดงผลการรันจริงและ reconciliation check (assert) ไม่ใช่แค่บอกว่าเสร็จ
- ห้ามแก้ไฟล์ใน `data/raw/`
- ชื่อคอลัมน์ที่ไม่ได้อยู่ใน data dictionary (เช่นใน cost_assumptions) ต้องเปิดดูไฟล์จริงก่อนเขียนโค้ด ห้ามเดา

## Writing style for notebooks, comments and docs (must read like a real analyst wrote it)
Write like a working data analyst's notebook, not a tutorial or a chatbot answer.
- Notebook = a chain of questions. Each section header is a question ("Are there duplicate rows?"), not a topic ("Duplicate Analysis").
- Markdown cells: 1-3 short lines, number first. Example: "**1,184 exact duplicates (0.6% of rows, ฿92k).** Same export twice -> drop in lesson 4." Fragments are fine.
- Write what the number means and what we do next. Do not describe what the code does.
- Say what looks normal too, in one line ("Dates: 365 days, no gaps. OK.").
- Keep open questions visible: "? Is RC000 the normal price - check conditions." and "TODO:".
- Keep dead ends short: "Checked hour 25+ - none."
- Code comments: only where the reason is not obvious. No comment that repeats the code. No "===== Cell 1 =====" banners.
- Docstrings: one line.
- Tables: only the columns needed for the point. Round numbers (฿92k, 0.6%).
- Chart titles state the finding.
- BANNED: emojis, ✅/❌, "Let's", "dive into", "comprehensive", "robust", "leverage", "crucial", "it's worth noting", "In conclusion", "Key takeaways", "This analysis provides", bold on every line, a summary that repeats the cells above, long bullet lists, perfectly symmetric sections, em dashes.
- End of notebook: a short "Findings -> next steps" list (max 5 lines), each with a number.

## ข้อมูล (data/raw/FruitBlend24_Intern_Case_Data.xlsx)
- ช่วงข้อมูล: 2025-09-01 ถึง 2026-08-31 (12 เดือน)
- 4 ครัว: Pattaya_Central, Pattaya_Beach, BKK_Sukhumvit, BKK_Ladprao
- 2 platform: LINE MAN, Grab (ขายออนไลน์ 100%, เปิด 24 ชม.)
- MixedBerryPremium เปิดตัว 2026-03-01 → เทียบเมนูอย่างยุติธรรมใช้ช่วง 2026-03 ถึง 2026-08 และใช้ "แก้วต่อวัน" ไม่ใช่ยอดรวม
- Forecast horizon: 2026-09 ถึง 2026-11 (ใช้ ก.ย.–พ.ย. 2025 เป็น sanity check ฤดูกาลของ 4 เมนูเดิม)

ชีต:
- `orders_hourly`: date, hour (0-23), day_of_week (0=Mon), kitchen, item_name_raw, price_thb (ราคาหลังส่วนลดแล้ว), units_sold, gross_revenue_thb (= units × price), rate_code
- `weekly_fruit_cost`: week_start (วันจันทร์), sku, fruit_cost_per_cup_thb
- `platform_commission_rate`: platform_code, platform_name, commission_rate (สัดส่วนของ gross revenue, คงที่)
- `waste_daily`: date, kitchen, sku, units_wasted, est_waste_cost_thb (ผลไม้ + แพ็กเกจ เท่านั้น)
- `rate_code_dim`: base_code, rate_code_name, discount_pct, code_pattern, conditions (อ่าน conditions ก่อนตัดสินว่าโค้ดไหนคือราคาปกติ)
- `platform_dim`: platform_code, platform_name
- `sku_code_dim`: sku_code, sku (ใช้กับโค้ด RC101 เท่านั้น)
- `cost_assumptions`: 2 ตารางในชีตเดียว (ต้นทุนต่อแก้ว + overhead ครัว) แยกแล้วใน `load_tables()` เป็น `unit_cost` และ `kitchen_overhead`
- `monthly_budget`: month, budget_revenue_thb, budget_gross_profit_thb, note (อ่าน note ก่อนนิยาม GP)

## ชื่อจริงในโค้ดของโปรเจกต์ (ใช้ชื่อนี้ ไม่ใช่ชื่อในบทเรียน)
- `src/load_clean.py`: SKUS, BERRY, BERRY_LAUNCH, KEY, week_monday(), load_raw(), load_mapping(), load_tables(raw=None, return_log=False), clean_orders(raw=None, mapping=None), reconcile(raw_orders, clean, log), load_clean()
- `load_tables()` keys: rate_code_dim, platform_dim, sku_code_dim, platform_commission_rate, unit_cost (มี pack_labor_per_cup_thb, base_price_thb), kitchen_overhead (fixed_monthly_overhead_thb), monthly_budget (month เป็น datetime), weekly_fruit_cost (มี is_filled), waste_daily (มี is_filled)
- clean orders columns: date, hour, day_of_week, kitchen, item_name_raw, sku, rate_code, platform_code (LM/GB), base_code, sku_code, price_thb, units_sold, gross_revenue_thb, flag_unknown_code, flag_rc101_mismatch — ไม่มีคอลัมน์ month ต้องสร้างเอง
- `src/economics.py`: enrich(df, sheets) เพิ่ม week_start, commission_rate, discount_pct, fruit_cost_per_cup_thb, pack_labor_per_cup_thb, base_price_thb, list_price_thb, list_revenue_thb, discount_thb, commission_thb, net_revenue_thb, fruit_cost_thb, pack_labor_thb, cm_thb · unit_economics(e, by) คืน cups, list_price, avg_sell_price, cm_per_cup, cm_pct ฯลฯ
- CM ที่ราคาเต็มต่อแก้ว = list_price_thb × (1 − commission_rate) − fruit_cost_per_cup_thb − pack_labor_per_cup_thb
- `src/pnl.py`: SUMS, month_key(), add_ratios(), contribution(e, sheets) (month เป็นข้อความ "YYYY-MM"; คอลัมน์ cups, list_revenue, discount, gross_revenue, commission, net_revenue, fruit, pack_labor, cm, waste_units, waste_cost, gp_a, gp_b, gross_profit, gp_pct, waste_rate_pct) · kitchen_pnl(c, sheets) (+overhead, operating_profit, op_margin_pct) · company_pnl(k) · as_statement(df) · budget_variance(m, sheets) · margin_gap(c, v, by) · gp_bridge(v, item_gap) · menu_matrix(c, months, by=None)
- `src/forecast.py`: daily_panel(e, sheets) (date×kitchen×sku: sold, wasted, waste_cost, promo_day, dow, month) · critical_ratio · prep_rule(p, q) (คืน prep, mu, sd; shift(1)) · score_prep · normal_waste_short · METHODS (seasonal_naive, weekday_mean_8w, holt_winters_damped) · forecast_all · wape_bias · forecast_horizon(p, method) · demand_cv
- `src/scenario.py`: build_inputs(fc, p, e, sheets, promo_inc, cv, cost_months) · run(d, spec, eps=-1.5) (spec keys: kill, prices, rule_items, z, delist, demand_mult, fruit_mult) · rule_z · summary
- `src/pnl_excel.py`: write_pnl_xlsx(path, company, kitchen, contrib, variance, overhead), FormulaCheck (ตรวจสูตร Excel ด้วย Python เพราะเครื่องนี้ไม่มี LibreOffice)

## ข้อเท็จจริงที่ยืนยันแล้ว (notebook 01-02, decisions.md)
- หลัง clean: 123,655 แถว, 618,123 แก้ว, revenue 31,146,932.57 THB; ไม่มีแถว same-key
- Rate codes: RC000 ราคาปกติ 0% · RC101 Bundle 15% (1 SKU, สุ่ม ~1 ใน 10 วัน, ครอบคลุมทั้งวัน, 3-8 วันต่อเมนู) · RC102 Double Day 20% (12 วัน, 5 วันเป็นวันอังคาร) · RC103 Seasonal 12% (หน้าฝน: ก.ย.-ต.ค. 2025, มิ.ย.-ส.ค. 2026)
- Commission LM 0.30, GB 0.24; LM มี 56% ของ revenue ทุกครัวและทุกชั่วโมง
- พีค: พัทยา 22:00, กรุงเทพ 12:00; ส-อา 22:00 สูงสุด; ช่วงเงียบ = Morning 6-10 และ Late night 22-5 (~40 แก้ว/ชม. vs ~100-110)
- ฤดู: เมนูเดิมพีคเมษายน (สัปดาห์สงกรานต์ 13 เม.ย. สูงผิดปกติ), ต่ำสุดหน้าฝน
- Berry: CM 10.02/แก้ว, waste 20.5%, CM หลัง waste −1.92/แก้ว; ยอดลด 67% ตั้งแต่เปิดตัว
- Elasticity หลัก (RC101 vs RC000): −1.1 (berry) ถึง −1.8 (Guava); day-level −1.5 ถึง −2.1
- การตัดสินราคาบทที่ 6 อยู่ใน decisions.md (Watermelon 49, PassionFruit 69, Pineapple/Guava test 55, Berry fix cost/review delist, platform price test only)
- บทที่ 7 (notebook 03, outputs/promo_decision.csv): ทุกโปรขาดทุนหลัง waste + side effects (−14.6k THB/เดือน); Kill = RC101 Watermelon/PassionFruit/berry + RC103 ทั้ง 2 platform (+7.0k/เดือน); Modify + test = RC101 Pineapple (quiet hours), RC101 Guava (10%), RC102 (12%, ไม่รวม berry) (+1.9k/เดือนถ้าผ่าน); วันโปร waste มากขึ้น (RC102 +81%)
- บทที่ 8-9 (notebook 04): GP-C 7.64M (24.5%) · operating profit −404k (−1.3%), ติดลบ 8/12 เดือน · GP vs budget −764k = revenue effect −325k + margin effect −439k · item gap: berry −686k, PassionFruit −420k, Watermelon +357k, Pineapple +233k, Guava +77k · Ladprao −51.7k/เดือน (ติดลบ 12/12), Sukhumvit −40.5k (9/12), Pattaya Beach +27.7k, Central +31.0k · menu (มี.ค.-ส.ค.): Star Watermelon/Pineapple, Puzzle Guava, Dog PassionFruit/berry · portfolio plan +70.5k (low) ถึง +191.4k (high)/เดือน (outputs/portfolio_decision.csv, in_plan=True เท่านั้นที่บวกกันได้)
- บทที่ 10-11 (notebook 05): berry 39% ของ waste THB (แก้ว 4.5%) · CR berry 0.05, PF 0.16, เมนูถูก 0.44-0.49 · กฎเตรียมของใช้เฉพาะ berry + PF ที่ CR+0.1 (+29.6k/เดือนใน backtest ส.ค.) เมนูถูกใช้แบบเดิม · forecast ชนะ = seasonal naive (WAPE 46.6%, ทุกวิธีพลาดฤดู 45-63%) · ก.ย.-พ.ย. 2026 เมนูเดิม −2.0% vs 2025 · Scenario 3 เดือน operating profit: Base −685k, Action −408k (+92.4k/เดือน: rule 40.2k, ราคา W/PF 27.2k, berry 99 13.5k, kill โปร 11.5k), Action+delist −450k, Downside −787k (Base downside −1,106k) · ไม่ delist berry ตอนนี้ ใช้ stop rule
- ตัวเลขทั้งปีที่ใช้ตรวจ P&L: revenue 31,146,932.57 · commission ≈ 8.52M · CM (ก่อน waste) ≈ 8.50M · waste (filled) ≈ 860.3k · overhead 670k/เดือน = 8.04M/ปี · budget ทั้งปี revenue 32.4M, GP 8.4M (25.9%)

## การตัดสินใจล่วงหน้าสำหรับบท 8–14 (ผู้ใช้เลือกแล้ว ไม่ต้องหยุดถาม)
- Gross profit หลัก = GP-C (หัก commission, fruit, pack+labor, waste) เพราะ waste เป็นต้นทุนผันแปรจริงและ note ของ budget ไม่ได้นิยาม; แสดง GP-A/GP-B เทียบ GP% ของ budget เป็น check
- Variance vs budget: revenue effect + margin effect (assert ปิด); margin effect แยกเป็น gap ต่อเมนูและต่อครัว; waterfall Budget GP → Actual GP
- Overhead ไม่ปันลงเมนู; ครัววัดด้วย operating profit
- Forecast ก.ย.–พ.ย. 2026: ระดับ ก.ย. จากวิธีที่ชนะ backtest (train ≤ 2026-05-31, test มิ.ย.–ส.ค.); ต.ค./พ.ย. = ก.ย. × อัตราเปลี่ยนรายเดือนของปี 2025 (ต.ค./ก.ย., พ.ย./ก.ย.) ของเมนูเดิม; berry ใช้ค่าเฉลี่ยวันในสัปดาห์ 4 สัปดาห์ล่าสุดแบบคงที่ (ไม่มีปีก่อน)
- Budget ก.ย.–พ.ย. 2026 = flat 2.7M / 0.7M ต่อเดือนเหมือนเดิม
- Scenario: Base (ราคา/โปรเดิม) · Action (ราคาบท 6 + โปรบท 7 + กฎเตรียมของบท 10 + berry 99 บาท) · Action + delist berry · Downside (fruit +15%, demand −10%); คำนวณในโมเดลเดียวต่อ เดือน × ครัว × เมนู เพื่อไม่นับผลซ้ำ
- ถ้าเจอ judgment call ใหม่ที่ไม่อยู่ในรายการนี้: เลือกทางที่ระวังที่สุด (กำไรต่ำกว่า), จดลง decisions.md, แล้วบอกผู้ใช้ตอนจบ ไม่ต้องหยุดรอ (ผู้ใช้ต้องส่งงานวันนี้)

## ปัญหาข้อมูลที่รู้แล้ว
- `item_name_raw` สะกด/ภาษา/ตัวพิมพ์ไม่สม่ำเสมอ มีสินค้าที่ไม่ใช่เมนู และมีแถวซ้ำแบบ exact
- ต้อง map ไปยังชื่อมาตรฐาน 5 ตัวนี้เท่านั้น (ตรงกับคอลัมน์ sku ในชีตอื่น):
  `Watermelon`, `Pineapple`, `Guava`, `PassionFruit`, `MixedBerryPremium` หรือ `DROP`
- mapping เก็บที่ `data/processed/item_mapping.csv` (เสนออัตโนมัติ แล้วผู้ใช้ตรวจด้วยมือ ห้ามเหลือ REVIEW)
- หลักตัดสิน: ไม่ใช่ยอดขายจริง → ตัด · ยอดขายจริงแต่บันทึกเพี้ยน → แก้ · ไม่แน่ใจ → เก็บแต่ flag · บอกผลกระทบเป็นบาทเสมอ
- Key duplicate หลังรวมชื่อ (date-hour-kitchen-sku-rate_code) → รวมยอด ไม่ลบ
- ทุกการลบ/แก้ ต้องลง Data Quality Log (category, issue, rows, %, revenue ดิบ, action) และ reconcile ยอดดิบ − ที่ตัด = ยอดหลัง clean

## กฎการแยก rate_code
รูปแบบ `PLATFORM-BASECODE[-SKUCODE]` เช่น `LM-RC000`, `GB-RC101-WM`
- ส่วนที่ 1 → platform_code (join กับ platform_commission_rate, platform_dim)
- ส่วนที่ 2 → base_code (join กับ rate_code_dim)
- ส่วนที่ 3 (มีเฉพาะ RC101) → sku_code (join กับ sku_code_dim) ต้องตรงกับเมนูของแถวนั้น
- ราคาเต็ม = price_thb / (1 - discount_pct)

## สูตรหลัก
- CM ต่อแก้ว = price_thb × (1 − commission_rate) − fruit_cost_per_cup (สัปดาห์นั้น) − packaging_labor_per_cup
- ค่าเฉลี่ยต่อแก้ว: รวมเงินก่อนแล้วหารด้วยจำนวนแก้ว (weighted) ห้ามเฉลี่ยต่อแถว
- Discount cost = (ราคาเต็ม − price_thb) × units_sold
- Break-even lift = CM_full / CM_promo − 1 (ถ้า CM_promo ≤ 0 = Kill)
- Baseline โปร = แก้วเฉลี่ยของช่องเดียวกันที่ไม่มีโปร (kitchen, sku, platform_code, month, day_of_week, hour) — ต้องมี month เพราะ RC103 จัดเฉพาะหน้าฝน; ทดสอบซ้ำโดยตัดสัปดาห์สงกรานต์ออกจาก baseline; Incremental CM = CM จริง − baseline × CM ที่ราคาเต็ม; รวมผล waste ในวันโปรด้วย; RC102 มีแค่ 12 วัน → ความมั่นใจต่ำ, วัดลูกค้าใหม่ไม่ได้
- Scenario 3 เดือน: budget ก.ย.–พ.ย. 2026 สมมติว่า flat 2.7M/0.7M เหมือนเดิม; ต้นทุนผลไม้เทียบ 2 แบบ (เฉลี่ย มิ.ย.–ส.ค. 2026 vs สัปดาห์เดียวกันปี 2025 × อัตราเปลี่ยนปีต่อปี)
- Elasticity: log-log OLS ต่อเมนู ควบคุม hour, weekday, kitchen, platform, month (HC1 SE) + sensitivity ε = −0.5/−1.0/−1.5
- Waste rate = units_wasted / (units_sold + units_wasted)
- Critical ratio (newsvendor) = Cu / (Cu + Co), Cu = CM ต่อแก้ว, Co = ต้นทุนแก้วที่ทิ้ง; สมมติฐาน: เตรียม = ขาย + ทิ้ง
- GP variance vs budget = revenue effect + margin effect (ต้อง assert ว่าบวกกันเท่ากับ variance)
- PVM bridge ก่อน vs หลัง 2026-03-01 (ต่อเดือนเฉลี่ย): volume, mix, price, fruit, pack, waste, new item (ต้อง assert ว่าปิดพอดี)
- Join ต้นทุนผลไม้: แปลง date เป็นวันจันทร์ของสัปดาห์ (`date - pd.to_timedelta(date.dt.dayofweek, unit="D")`)

## นิยาม P&L
- Gross revenue − Commission = Net revenue
- Net revenue − Fruit − Packaging/labor − Waste = **Gross profit (GP-C, นิยามหลัก)**
- เทียบ GP-A (ไม่หักค่าคอม/waste) และ GP-B (ไม่หัก waste) กับ GP% ของ budget แล้วให้ผู้ใช้เลือก พร้อมเหตุผล
- Gross profit − Kitchen overhead = Operating profit
- ห้ามปันส่วน overhead ลงเมนู: วัดเมนูด้วย GP/contribution วัดครัวด้วย operating profit

## Forecast
- Backtest: train ถึง 2026-05-31, test 2026-06-01 ถึง 2026-08-31 (3 เดือน เท่ากับ horizon จริง)
- วิธีเทียบ: seasonal naive, weekday mean (8 สัปดาห์), Holt-Winters (damped trend, seasonal 7); วัด WAPE + bias
- ใช้ last-year × growth เป็น sanity check ตอนพยากรณ์ ก.ย.–พ.ย. เท่านั้น
- ระวัง look-ahead: rolling ต้อง shift(1)
- Scenario P&L: Base / Action plan (ตัวเลขจากผลบท 6, 7, 10 จริง) / Downside; ห้ามนับผลซ้ำ ใส่ผลยอดลดจากการตัดโปรด้วย

## โครงโปรเจกต์
- `data/raw/` ต้นฉบับ (ห้ามแก้) · `data/processed/` item_mapping.csv, orders_clean.parquet, orders_enriched.parquet, data_quality_log.csv
- `notebooks/01_data_quality` → `02_demand_pricing` → `03_promotions` → `04_pnl_budget` → `05_forecast_inventory`
- `src/` load_clean.py, economics.py (enrich, unit_economics), pnl.py, forecast.py — notebook และแอปเรียกจากที่เดียวกัน
- บทเรียนเป็นแนวทาง ข้อมูลและโค้ดจริงชนะเสมอ: ถ้าต่างจากบทเรียน ให้ใช้ของจริงแล้วบอกผู้ใช้ว่าต่างตรงไหน
- `outputs/` ตารางผลลัพธ์ที่แอปอ่าน: dq_log, unit_economics, promo_decision, company_pnl, kitchen_pnl, item_kitchen_pnl, budget_variance, gp_bridge, item_gap, portfolio_decision, pvm_bridge, menu_matrix, waste_summary, prep_rule_backtest, forecast_backtest, forecast_monthly, inventory_plan, scenarios, scenario_summary, profit_plan, recommendations (.csv) + FruitBlend24_PnL.xlsx
- `app/streamlit_app.py` (Executive Summary) + `app/common.py` + `app/pages/1_Data_Quality … 6_Assumptions_and_Method`
- แอปอ่านจาก outputs/ เท่านั้น ไม่คำนวณหนักตอนเปิด ใช้ `@st.cache_data`
- `docs/decisions.md` บันทึกการตัดสินใจ · `docs/executive_summary.md` (ภาษาอังกฤษ)
- `notes/` โน้ตเรียนรู้ภาษาไทยส่วนตัว (อยู่ใน .gitignore)

## Stack
Python 3.11+, pandas, pyarrow, openpyxl, numpy, scipy, plotly, statsmodels, streamlit, jupyter
ผู้ใช้ใช้ Windows (PowerShell, `.venv\Scripts\Activate.ps1`); deploy บน Streamlit Community Cloud (Linux, path แยกตัวพิมพ์)

## Checks ที่ต้องผ่านเสมอ
- revenue ดิบ − ที่ตัดออก = revenue หลัง clean (assert)
- ผลรวมทุกครัว/เมนูเท่ากับยอดรวมบริษัท และ waste ใน P&L = ผลรวม waste_daily ดิบ + ส่วนที่เติม (6 kitchen-days ≈฿457 + berry วันเปิดตัว ≈฿4,002) = ≈฿860.3k (ดู decisions.md)
- ทุกแถวใน orders join กับ dim tables และต้นทุนได้ครบ (ใช้ merge indicator=True / validate=)
- notebook รัน Restart & Run All ได้ไม่ error
- ตัวเลขในแอป = notebook = P&L xlsx
