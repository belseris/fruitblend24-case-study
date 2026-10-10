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
- `cost_assumptions`: ต้นทุนแพ็กเกจ/แรงงานต่อแก้วต่อ SKU + overhead คงที่รายเดือนต่อครัว (ชื่อคอลัมน์ต้องเช็กจากไฟล์จริง)
- `monthly_budget`: month, budget_revenue_thb, budget_gross_profit_thb, note (อ่าน note ก่อนนิยาม GP)

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
- Baseline โปร = แก้วเฉลี่ยของช่องเดียวกันที่ไม่มีโปร (kitchen, sku, platform, day_of_week, hour); Incremental CM = CM จริง − baseline × CM_full
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
- `outputs/` ตารางผลลัพธ์ที่แอปอ่าน: dq_log, unit_economics, promo_decision, company_pnl, budget_variance, pvm_bridge, menu_matrix, waste_summary, forecast_monthly, scenarios, recommendations (.csv) + FruitBlend24_PnL.xlsx
- `app/streamlit_app.py` (Executive Summary) + `app/common.py` + `app/pages/1_Data_Quality … 6_Assumptions_and_Method`
- แอปอ่านจาก outputs/ เท่านั้น ไม่คำนวณหนักตอนเปิด ใช้ `@st.cache_data`
- `docs/decisions.md` บันทึกการตัดสินใจ · `docs/executive_summary.md` (ภาษาอังกฤษ)
- `notes/` โน้ตเรียนรู้ภาษาไทยส่วนตัว (อยู่ใน .gitignore)

## Stack
Python 3.11+, pandas, pyarrow, openpyxl, numpy, scipy, plotly, statsmodels, streamlit, jupyter
ผู้ใช้ใช้ Windows (PowerShell, `.venv\Scripts\Activate.ps1`); deploy บน Streamlit Community Cloud (Linux, path แยกตัวพิมพ์)

## Checks ที่ต้องผ่านเสมอ
- revenue ดิบ − ที่ตัดออก = revenue หลัง clean (assert)
- ผลรวมทุกครัว/เมนูเท่ากับยอดรวมบริษัท และ waste ใน P&L = ผลรวม waste_daily + ส่วนที่เติม 6 kitchen-days (≈฿457, ดู decisions.md)
- ทุกแถวใน orders join กับ dim tables และต้นทุนได้ครบ (ใช้ merge indicator=True / validate=)
- notebook รัน Restart & Run All ได้ไม่ error
- ตัวเลขในแอป = notebook = P&L xlsx
