# Schedule K-1 (Form 1065) — Complete Field Catalog

**Purpose**: Reference catalog for building a PDF text extraction parser for IRS Schedule K-1 (Form 1065).  
**Tax Years Covered**: 2020–2025  
**Date**: 2026-03-04

---

## Table of Contents

1. [Form Overview & Layout](#1-form-overview--layout)
2. [Part I — Information About the Partnership](#2-part-i--information-about-the-partnership)
3. [Part II — Information About the Partner](#3-part-ii--information-about-the-partner)
4. [Part III — Partner's Share of Current Year Income, Deductions, Credits, and Other Items](#4-part-iii--partners-share-of-current-year-income-deductions-credits-and-other-items)
5. [Multi-Code Line Detail (Lines 11–23)](#5-multi-code-line-detail-lines-1123)
6. [Supplemental Statement Patterns](#6-supplemental-statement-patterns)
7. [Data Type Reference](#7-data-type-reference)
8. [Year-over-Year Stability (2020–2025)](#8-year-over-year-stability-20202025)
9. [Parsing Notes & Edge Cases](#9-parsing-notes--edge-cases)

---

## 1. Form Overview & Layout

### Physical Layout

| Property | Value |
|----------|-------|
| **IRS Form Number** | Schedule K-1 (Form 1065) |
| **Full Title** | Partner's Share of Income, Deductions, Credits, and Other Items |
| **Standard page count** | 2 pages (base form), + 0–N supplemental statement pages |
| **Page 1 layout** | Left half: Part I + Part II; Right half: Part III lines 1–11 |
| **Page 2 layout** | Left half: Part II continued (Sections J–N); Right half: Part III lines 12–20 (and overflow area for 21–23) |
| **Orientation** | Portrait |
| **Column structure** | Part III is a two-column grid: lines 1–11 on the left column, lines 12–20+ on the right column |

### Key Structural Notes

- The form header contains: "Schedule K-1 (Form 1065)", the tax year ("20XX"), "Department of the Treasury — Internal Revenue Service"
- The **Calendar year field** or **Fiscal year beginning/ending** dates appear at the very top
- Part I and Part II occupy the LEFT side of page 1 (and continue to page 2 for sections J–N)
- Part III occupies the RIGHT side of both pages
- Lines 21, 22, 23 appear in a footer/overflow area at the bottom right of page 2

---

## 2. Part I — Information About the Partnership

All fields in this section are **single-value**. This section is in the upper-left of page 1.

| Line | Label | Data Type | Format / Pattern | Parsing Notes |
|------|-------|-----------|-----------------|---------------|
| **Header** | Calendar year ___ or tax year beginning ___ / ending ___ | `date` | `YYYY` or `MM/DD/YYYY` | Two variants: calendar year (just a 4-digit year) or fiscal year (two dates). Extract both patterns. |
| **A** | Partnership's employer identification number | `ein` | `XX-XXXXXXX` (2 digits, hyphen, 7 digits) | Always 9 digits. May appear with or without hyphen. Regex: `\d{2}-?\d{7}` |
| **B** | Partnership's name, address, city, state, and ZIP code | `text` (multiline) | Free text, typically 3–4 lines | May span 3–4 lines in the box. Parse as: Line 1 = name, Line 2 = street, Line 3 = city/state/ZIP. ZIP may be 5 or 9 digits (XXXXX or XXXXX-XXXX). |
| **C** | IRS Center where partnership filed return | `text` | IRS service center name | Common values: "Ogden, UT", "Kansas City, MO", "Cincinnati, OH", "Austin, TX". Some K-1s leave blank or show an e-file code. |
| **D** | Check if this is a publicly traded partnership (PTP) | `boolean` | Checkbox ☐ / ☑ | True if checked. PDF text extraction: look for an "X" or filled box near the label. |

---

## 3. Part II — Information About the Partner

This section spans the left side of page 1 (lines E–I) and continues on page 2 (lines J–N).

### Page 1 Fields (Lines E–I)

| Line | Label | Data Type | Multiplicity | Format / Pattern | Parsing Notes |
|------|-------|-----------|-------------|-----------------|---------------|
| **E** | Partner's identifying number | `tin` | Single | `XXX-XX-XXXX` (SSN) or `XX-XXXXXXX` (EIN) | May be partially masked: `***-**-1234`. Regex for full: `\d{3}-\d{2}-\d{4}` or `\d{2}-\d{7}` |
| **F** | Partner's name, address, city, state, and ZIP code | `text` (multiline) | Single | Free text, 3–4 lines | Same parsing as Line B. |
| **G** | ☐ General partner or LLC member-manager / ☐ Limited partner or other LLC member | `boolean` (pair) | Single (one-of-two) | Two checkboxes | Exactly one should be checked. Extract as enum: `"general"` or `"limited"` |
| **H1** | ☐ Domestic partner / ☐ Foreign partner | `boolean` (pair) | Single (one-of-two) | Two checkboxes | Extract as enum: `"domestic"` or `"foreign"` |
| **H2** | If the partner is a disregarded entity (DE), enter the partner's TIN and name | `text` + `tin` | Single (optional) | TIN + name text | Only present when partner is a DE. May be blank. |
| **I1** | What type of entity is this partner? | `text` | Single | Checkbox list or text | Common values: "Individual", "Corporation", "Estate", "Trust", "Partnership", "Exempt Organization", "Foreign Government", "Other". Some forms use checkboxes, others print the type as text. |
| **I2** | If this partner is a retirement plan (IRA/SEP/Keogh/etc.), check here | `boolean` | Single | Checkbox ☐ / ☑ | Usually blank for most partners. |

### Page 2 Fields (Lines J–N)

| Line | Label | Data Type | Multiplicity | Format / Pattern | Parsing Notes |
|------|-------|-----------|-------------|-----------------|---------------|
| **J** | Partner's share of profit, loss, and capital | `percentage` (table) | 6 values | `XX.XXXXX%` | A 3×2 grid: {Profit, Loss, Capital} × {Beginning, Ending}. Percentages typically 0–4 decimal places. Parse as decimal (e.g., 50.00000% → 50.0). |
| **K1** | Partner's share of liabilities | `currency` (table) | 6 values | Dollars (no cents typically) | A 3×2 grid: {Nonrecourse, Qualified nonrecourse financing, Recourse} × {Beginning, Ending}. All dollar amounts. |
| **K2** | Does the partner's share include lower tier partnership liabilities? | `boolean` | Single | "Yes" / "No" or checkbox | Some forms use checkboxes, others print "Yes"/"No" |
| **K3** | Does partner have guarantee/payment obligations? | `boolean` | Single | "Yes" / "No" or checkbox | Same as K2 |
| **L** | Partner's Capital Account Analysis | `currency` (table) | 6 values | Dollar amounts (may include negative with parentheses) | A single-row table with 6 columns: Beginning capital account, Capital contributed during year, Current year net income (loss), Other increase (decrease), Withdrawals & distributions, Ending capital account. **Also includes a tax basis checkbox area** (Tax basis / GAAP / Section 704(b) / Other). |
| **L (basis)** | Tax basis method indicator | `text` (enum) | Single | Checkbox set | Options: "Tax basis", "GAAP", "Section 704(b)", "Other (explain)". One should be checked. |
| **M** | Did the partner contribute property with a built-in gain or loss? | `boolean` | Single | "Yes" / "No" or checkbox | |
| **M (sub)** | If "Yes," attach statement | `text` | Single (optional) | Reference text | May say "SEE ATTACHED" or similar |
| **N** | Partner's Share of Net Unrecognized Section 704(c) Gain or (Loss) | `currency` (pair) | 2 values | Dollar amounts | Two values: Beginning and Ending. Can be negative (shown in parentheses). |

#### Section J Detail Grid

```
                    Beginning    Ending
  Profit            ____%        ____%
  Loss              ____%        ____%
  Capital           ____%        ____%
```

#### Section K1 Detail Grid

```
                                        Beginning ($)    Ending ($)
  Nonrecourse                           $________        $________
  Qualified nonrecourse financing       $________        $________
  Recourse                              $________        $________
```

#### Section L Detail Grid

```
  Beginning    Capital       Current year    Other inc/    Withdrawals    Ending
  capital      contributed   net income      (decrease)    & distrib.     capital
  account      during year   (loss)                                       account
  $_______     $_______      $_______        $_______      $_______       $_______
```

---

## 4. Part III — Partner's Share of Current Year Income, Deductions, Credits, and Other Items

### Layout Overview

Part III is divided across the right side of pages 1 and 2:
- **Page 1 right column**: Lines 1–11
- **Page 2 right column**: Lines 12–20 (and 21–23 in footer area)

Each line has:
- A **line number** (left margin)
- A **label/description** 
- A **value field** (right-aligned dollar amount, or code+amount for multi-code lines)

### Single-Value Lines (Simple Amount Fields)

These lines have exactly **one numeric value** — a dollar amount (positive or negative).

| Line | Label | Data Type | Parsing Notes |
|------|-------|-----------|---------------|
| **1** | Ordinary business income (loss) | `currency` | Can be negative (loss). Core income line. |
| **2** | Net rental real estate income (loss) | `currency` | Can be negative. |
| **3** | Other net rental income (loss) | `currency` | Can be negative. Less common. |
| **4a** | Guaranteed payments for services | `currency` | Sub-line of line 4. |
| **4b** | Guaranteed payments for capital | `currency` | Sub-line of line 4. |
| **4c** | Total guaranteed payments (4a + 4b) | `currency` | Computed total. |
| **5** | Interest income | `currency` | |
| **6a** | Ordinary dividends | `currency` | |
| **6b** | Qualified dividends | `currency` | Subset of 6a. |
| **6c** | Dividend equivalents | `currency` | Added in 2021+. |
| **7** | Royalties | `currency` | |
| **8** | Net short-term capital gain (loss) | `currency` | Can be negative. |
| **9a** | Net long-term capital gain (loss) | `currency` | Can be negative. |
| **9b** | Collectibles (28%) gain (loss) | `currency` | Special rate gain. |
| **9c** | Unrecaptured section 1250 gain | `currency` | Always ≥ 0. |
| **10** | Net section 1231 gain (loss) | `currency` | Can be negative. |
| **12** | Section 179 deduction | `currency` | |
| **16** | Foreign transactions — (various codes) | Multi-code (see below) | See multi-code section. In some years this was single, in recent years it's multi-code. |

### Multi-Code Lines (Code + Amount Pairs)

These lines can hold **multiple entries**, each identified by a **letter code** (A, B, C, ...). When only one or two values are present, they may be printed inline. When many values are present, the form prints **"SEE STMT"** or **"STMT"** and the details appear on supplemental pages.

| Line | Label | Multiplicity | Code Range | Notes |
|------|-------|-------------|-----------|-------|
| **11** | Other income (loss) | Multi-code | A–F, and special code `ZZ*` | Code ZZ* = "Other" catch-all. See detail below. |
| **13** | Other deductions | Multi-code | A–R (varies by year), `ZZ*` | Large set of possible codes. See detail below. |
| **14** | Self-employment earnings (loss) | Multi-code | A–C | A = Net earnings from self-employment, B = Gross farming/fishing income, C = Gross non-farm income |
| **15** | Credits | Multi-code | A–P+ (varies by year) | Wide range of tax credits. See detail below. |
| **16** | Foreign transactions | Multi-code | A–R+ (varies by year) | Foreign income, taxes paid, etc. See detail below. |
| **17** | Alternative minimum tax (AMT) items | Multi-code | A–F+ | AMT adjustments and preferences. |
| **18** | Tax-exempt income and nondeductible expenses | Multi-code | A–C | A = Tax-exempt interest, B = Other tax-exempt income, C = Nondeductible expenses |
| **19** | Distributions | Multi-code | A–C | A = Cash & marketable securities, B = Distribution subject to §737, C = Other property |
| **20** | Other information | Multi-code | A–AH+ (extensive) | Catch-all for dozens of items. See detail below. |
| **21** | More information (overflow) | Multi-code | (continuation) | Overflow area for additional 20-series items. |
| **22** | More information (overflow) | Multi-code | (continuation) | Second overflow area. Per 2023+ forms. |
| **23** | More information (overflow) | Multi-code | (continuation) | Third overflow area. Per 2024+ forms. |

---

## 5. Multi-Code Line Detail (Lines 11–23)

### Line 11 — Other Income (Loss)

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Other portfolio income (loss) | `currency` |
| B | Involuntary conversions | `currency` |
| C | Sec. 1256 contracts & straddles | `currency` |
| D | Mining exploration costs recapture | `currency` |
| E | Cancellation of debt | `currency` |
| F | Other income (loss) | `currency` |
| ZZ* | Other (see statement) | `currency` / `text` |

**ZZ\* note**: Code "ZZ*" (or sometimes displayed as just a free-text description) is a catch-all. The asterisk indicates a non-standard code. The actual description is usually on a supplemental statement.

### Line 13 — Other Deductions

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Cash contributions (50%) | `currency` |
| B | Cash contributions (30%) | `currency` |
| C | Noncash contributions (50%) | `currency` |
| D | Noncash contributions (30%) | `currency` |
| E | Capital gain property to a 50% organization (30%) | `currency` |
| F | Capital gain property (20%) | `currency` |
| G | Contributions (100%) | `currency` |
| H | Investment interest expense | `currency` |
| I | Deductions—royalty income | `currency` |
| J | Section 59(e)(2) expenditures | `currency` |
| K | Deductions—portfolio (other) | `currency` |
| L | Amounts paid for medical insurance | `currency` |
| M | Educational assistance benefits | `currency` |
| N | Dependent care benefits | `currency` |
| O | Preproductive period expenses | `currency` |
| P | Commercial revitalization deduction from rental real estate | `currency` |
| Q | Pensions and IRAs | `currency` |
| R | Reforestation expense deduction | `currency` |
| S | Domestic production activities deduction (pre-2018) | `currency` |
| T | Other deductions (catch-all) | `currency` |
| ZZ* | Other (see statement) | `currency` / `text` |

**Note**: Charitable contribution codes (A–G) changed starting in 2020 to reflect CARES Act changes. The 2020–2021 forms added "100% limitation" contributions. By 2022, the codes largely reverted but letter assignments shifted in some tax software.

### Line 14 — Self-Employment Earnings (Loss)

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Net earnings (loss) from self-employment | `currency` |
| B | Gross farming or fishing income | `currency` |
| C | Gross non-farm income | `currency` |

### Line 15 — Credits

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Low-income housing credit (section 42(j)(5)) from pre-2008 buildings | `currency` |
| B | Low-income housing credit (other) from pre-2008 buildings | `currency` |
| C | Low-income housing credit (section 42(j)(5)) from post-2007 buildings | `currency` |
| D | Low-income housing credit (other) from post-2007 buildings | `currency` |
| E | Disabled access credit | `currency` |
| F | Renewable electricity, refined coal, and Indian coal production credit | `currency` |
| G | Other rental real estate credits | `currency` |
| H | Other rental credits | `currency` |
| I | Undistributed capital gains credit | `currency` |
| J | Biofuel producer credit | `currency` |
| K | Work opportunity credit | `currency` |
| L | Research activities credit | `currency` |
| M | Other credits | `currency` |
| N | Recapture of credits | `currency` |
| O | Look-back interest — completed long-term contracts | `currency` |
| P | Look-back interest — income forecast method | `currency` |

### Line 16 — Foreign Transactions

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Name of country or U.S. possession | `text` |
| B | Gross income from all sources | `currency` |
| C | Gross income sourced at partner level | `currency` |
| D–F | Foreign gross income by category (passive, general, other) | `currency` |
| G | Interest expense apportioned at partner level | `currency` |
| H | Other apportioned at partner level | `currency` |
| I–K | Deductions allocated/apportioned at partnership level (by category) | `currency` |
| L | Total foreign taxes paid | `currency` |
| M | Total foreign taxes accrued | `currency` |
| N | Reduction in taxes available for credit | `currency` |
| O | Foreign trading gross receipts | `currency` |
| P | Extraterritorial income exclusion | `currency` |
| Q | Other foreign transactions | `currency` / `text` |

**Note**: Line 16 structure changed significantly in 2021 with the introduction of **Schedule K-3** (Form 1065). Post-2021, many Line 16 details moved to the separate K-3 form. The K-1 line 16 may simply say "See Schedule K-3" or contain minimal summary data.

### Line 17 — Alternative Minimum Tax (AMT) Items

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Post-1986 depreciation adjustment | `currency` |
| B | Adjusted gain or loss | `currency` |
| C | Depletion (other than oil & gas) | `currency` |
| D | Oil, gas, & geothermal—gross income | `currency` |
| E | Oil, gas, & geothermal—deductions | `currency` |
| F | Other AMT items | `currency` |

### Line 18 — Tax-Exempt Income and Nondeductible Expenses

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Tax-exempt interest income | `currency` |
| B | Other tax-exempt income | `currency` |
| C | Nondeductible expenses | `currency` |

### Line 19 — Distributions

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Cash and marketable securities | `currency` |
| B | Distribution subject to section 737 | `currency` |
| C | Other property | `currency` |

**Critical for portfolio tracking**: Line 19A is the primary distribution amount used to create Distribution records.

### Line 20 — Other Information

This is the most extensive multi-code line. Codes vary by tax year but the common set includes:

| Code | Description | Data Type |
|------|-------------|-----------|
| A | Investment income | `currency` |
| B | Investment expenses | `currency` |
| C | Fuel tax credit information | `currency` |
| D | Qualified rehabilitation expenditures (rental real estate) | `currency` |
| E | Basis of energy property | `currency` |
| F | Recapture of low-income housing credit — section 42(j)(5) | `currency` |
| G | Recapture of low-income housing credit — other | `currency` |
| H | Recapture of investment credit | `currency` |
| I | Recapture of other credits | `currency` |
| J | Look-back interest — completed long-term contracts | `currency` |
| K | Look-back interest — income forecast method | `currency` |
| L | Dispositions of property with section 179 deductions | `currency` |
| M | Recapture of section 179 deduction | `currency` |
| N | Interest expense for corporate partners | `currency` |
| O | Section 453(l)(3) information | `currency` |
| P | Section 453A(c) information | `currency` |
| Q | Section 1260(b) information | `currency` |
| R | Interest allocable to production expenditures | `currency` |
| S | CCF nonqualified withdrawals | `currency` |
| T | Depletion information—oil and gas | `currency` |
| U | Reserved (or amortization of reforestation costs in some years) | `currency` |
| V | Unrelated business taxable income (UBTI) | `currency` |
| W | Precontribution gain (loss) | `currency` |
| X | Section 108(i) information | `currency` |
| Y | Net investment income (section 1411) | `currency` |
| Z | Section 199A information (Qualified Business Income) | `currency` / complex |
| AA | Section 704(c) information | `currency` |
| AB | Section 751 gain (loss) | `currency` |
| AC | Excess taxable income | `currency` |
| AD | Gross receipts for section 448(c) | `currency` |
| AE | Excess business interest income | `currency` |
| AF | Section 163(j) — business interest items | `currency` |
| AG | Partner's interest in partnership profits (for 163(j)) | `percentage` |
| AH | Qualified opportunity zone information | `currency` / `text` |

**Code Z (Section 199A) note**: This is particularly complex. Code Z often references a supplemental statement containing multiple sub-items for each qualified business: ordinary income, W-2 wages, UBIA of qualified property, SSTB indicator, etc. The statement can be multi-page.

### Lines 21–23 — Overflow / More Information

Lines 21, 22, and 23 are overflow areas that use the **same code system** as line 20. They were added progressively:
- **Line 21**: Present on all 2020–2025 forms 
- **Line 22**: Added ~2023 for additional overflow
- **Line 23**: Added ~2024 for additional overflow

These lines use their own codes but are effectively continuations of multi-code data.

---

## 6. Supplemental Statement Patterns

### When Supplemental Statements Appear

A K-1 line shows **"SEE STMT"**, **"STMT"**, or **"SEE ATTACHED STATEMENT"** when the line has more coded items than can fit in the printed box. The supplemental detail appears on additional pages after page 2.

### Common Trigger Lines

| Line | Likelihood of Supplemental | Reason |
|------|---------------------------|--------|
| 11 | Medium | Multiple categories of other income |
| 13 | High | Multiple charitable contribution types + other deductions |
| 16 | High (post-2021: "See Schedule K-3") | Foreign transaction details |
| 17 | Low–Medium | AMT items |
| 20 | **Very High** | Catch-all line with dozens of possible codes, especially Code Z (199A) |
| 21–23 | High | Overflow by definition |

### Supplemental Statement Format Patterns

Tax software generates supplemental statements in varying formats. Common patterns:

**Pattern 1 — Tabular (most common)**
```
Schedule K-1, Line 20 - Other Information
Code    Description                                     Amount
A       Investment income                            1,234.00
B       Investment expenses                            567.00
Z       Section 199A - QBI Deduction Information          *
        Ordinary income (loss)                       8,910.00
        W-2 wages                                    3,456.00
        UBIA of qualified property                   2,100.00
```

**Pattern 2 — Labeled pairs**
```
LINE 20 CODE A - INVESTMENT INCOME .............. $1,234
LINE 20 CODE B - INVESTMENT EXPENSES .............. $567
```

**Pattern 3 — Condensed (Drake Software)**
```
20A  1,234
20B    567
20Z  SEE DETAIL
```

**Pattern 4 — Verbose (UltraTax)**
```
Partner's Share of Other Information (Line 20)
   Code A  Investment income                     $    1,234.
   Code B  Investment expenses                   $      567.
```

### "SEE STMT" Detection

When parsing the main K-1 form and encountering these patterns in a value field, set a flag and look for the supplemental pages:
- `SEE STMT`
- `STMT`
- `SEE ATTACHED`
- `SEE STATEMENT`
- `*` (asterisk, sometimes used alone)
- `VARIOUS` (less common)

---

## 7. Data Type Reference

### Data Type Definitions

| Type | Description | Regex Pattern | Normalization |
|------|-------------|---------------|---------------|
| `currency` | Dollar amount, may be negative | `\$?\s*\(?\d{1,3}(,\d{3})*(\.\d{1,2})?\)?` or `-?\d+\.?\d*` | Strip `$`, `,`, spaces. Convert `(1,234)` → `-1234`. Convert trailing period `1,234.` → `1234.00`. |
| `percentage` | Percentage value | `\d{1,3}(\.\d{1,5})?%?` | Strip `%`. Represent as string/decimal, not divided by 100 (50.00000 = 50%). |
| `ein` | Employer Identification Number | `\d{2}-?\d{7}` | Normalize to `XX-XXXXXXX` format with hyphen. |
| `tin` | Taxpayer ID (SSN or EIN) | `\d{3}-?\d{2}-?\d{4}` or `\d{2}-?\d{7}` or `\*{3}-\*{2}-\d{4}` | Preserve masking if present. Normalize to hyphenated format. |
| `text` | Free-form text | N/A | Trim whitespace. Collapse multiple spaces. |
| `boolean` | Checkbox (checked/unchecked) | Look for "X", "✓", filled box | `true` if checked, `false` if empty. |
| `date` | Date value | `\d{1,2}/\d{1,2}/\d{2,4}` or `\d{4}` (year only) | Normalize to ISO `YYYY-MM-DD` or just `YYYY` for tax year. |
| `enum` | One-of-N labeled options | N/A | Map to enum string matching checked option. |
| `code_value` | Letter code + dollar amount | `[A-Z]{1,2}\*?\s+[\d,\.\(\)\$-]+` | Parse code and amount separately. |

### Negative Value Conventions

K-1 forms represent negative values in two ways:
1. **Parentheses**: `(1,234)` means -1,234
2. **Minus sign**: `-1,234` (less common on printed forms)
3. **"Loss" label**: Context implies the value is negative when the label says "loss"

Parser must handle both conventions.

### Currency Formatting Variants

| Raw Extracted Text | Normalized Value |
|-------------------|-----------------|
| `$1,234,567` | `1234567.00` |
| `1,234,567` | `1234567.00` |
| `(1,234)` | `-1234.00` |
| `$ (1,234)` | `-1234.00` |
| `1234.` | `1234.00` |
| `1,234.56` | `1234.56` |
| `-0-` | `0.00` |
| `—` (em dash) | `0.00` |
| (blank) | `null` |
| `STMT` | `null` (flag as see-statement) |

---

## 8. Year-over-Year Stability (2020–2025)

### Summary: Field positions are largely stable with minor additions

The IRS revises the K-1 form infrequently. The core field layout (Part I, Part II, Part III lines 1–20) has been stable since at least 2018. Key changes by year:

| Tax Year | Notable Changes |
|----------|----------------|
| **2020** | Baseline for this catalog. Added 100% charitable contribution deduction (CARES Act) — affected Line 13 codes. |
| **2021** | **Line 6c (Dividend equivalents)** added as new sub-line. **Schedule K-3 introduced** — Line 16 (Foreign Transactions) often now references K-3 instead of inline codes. Some partnerships began providing K-3 alongside K-1 for all partners (IRS Notice 2021-39). |
| **2022** | K-3 reporting expanded; Line 16 frequently shows "See Schedule K-3" rather than individual codes. Line 20 Code Z (199A) supplemental format became more standardized across tax software. |
| **2023** | **Line 22 added** as additional overflow area. Minor code additions in Line 20 (energy credit items from Inflation Reduction Act). |
| **2024** | **Line 23 added** as third overflow area. Additional energy credit codes on Line 15 and Line 20 for IRA (Inflation Reduction Act) clean energy credits. |
| **2025** | Expected to be largely stable vs 2024. Watch for corporate AMT adjustments. |

### What's Stable (Parser Can Rely On)

- **Part I fields (A–D)**: Unchanged since at least 2017.
- **Part II fields (E–N)**: Unchanged since at least 2017. The only addition was minor label clarifications.
- **Part III lines 1–10**: Completely stable. Same labels, positions, meaning.
- **Part III lines 12, 14, 17, 18, 19**: Stable codes and meanings.
- **Section J, K, L, M, N structure**: Unchanged.

### What Changes (Parser Must Account For)

- **Line 6c**: Not present before 2021. Parser should handle its absence on pre-2021 forms.
- **Line 16**: Changed dramatically post-2021 (K-3 introduction). May contain codes OR a "See K-3" reference.
- **Lines 13, 15, 20**: Code letters shift occasionally (new codes added, old codes deprecated). Parser should not hardcode the full code list but should be flexible about which codes appear.
- **Lines 22, 23**: Don't exist on pre-2023/pre-2024 forms respectively.
- **Physical coordinates**: May shift by a few points between tax years and between software vendors. Use **anchor-relative positioning** rather than absolute coordinates.

### Position Stability by Tax Software

| Software | Position Consistency | Notes |
|----------|---------------------|-------|
| Drake Software | High across years | Very consistent layout. Minor font/spacing changes. |
| UltraTax (Thomson Reuters) | High | Consistent with slightly different spacing than Drake. |
| TurboTax / Lacerte (Intuit) | High | Consistent. TurboTax consumer K-1s are rare (mostly 1040 filers). |
| GoSystem Tax (Thomson) | Medium–High | Corporate-focused, consistent but unique layout. |
| CCH Axcess / ProSystem fx | High | Consistent layout. |
| IRS fillable PDF | Very high | The canonical reference — direct from IRS forms library. |

**Recommendation**: Calibrate initial bounding boxes from the IRS fillable PDF, then build tolerance margins (±5–10 points) to handle vendor variations. Use anchor detection (find "Schedule K-1 (Form 1065)" header and "Part I" / "Part II" / "Part III" labels) to compute coordinate offsets dynamically.

---

## 9. Parsing Notes & Edge Cases

### Checkbox Detection in PDF Text Extraction

Checkboxes in digitally-generated PDFs are typically represented as:
- A form field (`/AcroForm`) with a value — pdfplumber may extract this via form field parsing
- A Unicode character: ☑ (U+2611), ☐ (U+2610), ✓ (U+2713), ✗ (U+2717)
- An "X" character positioned inside a box region
- A filled rectangle (graphical element, not text)

**Strategy**: First check AcroForm fields. If not present, look for "X" or check-mark characters in the checkbox region. Fall back to visual/graphical element detection.

### Multi-Line Address Parsing (Lines B, F)

Addresses span multiple lines within a single box. Common structures:
```
ACME CAPITAL PARTNERS LP
123 MAIN STREET SUITE 400  
NEW YORK NY 10001
```
or
```
ACME CAPITAL PARTNERS LP
C/O FUND ADMINISTRATOR INC
123 MAIN STREET
NEW YORK, NY 10001-1234
```

**Strategy**: Extract all text in the box, split by newlines. First line = name. Last line = city/state/ZIP. Middle lines = street address.

### Percentage Field Precision

Section J percentages can have up to 5 decimal places:
- `50.00000%`
- `0.12345%`
- `100.00000%`

Store as `Decimal` with precision sufficient for 5 decimal places.

### Empty vs Zero vs Missing

| Displayed | Meaning | Stored Value |
|-----------|---------|-------------|
| Blank / empty | Not applicable or zero | `null` or `0` depending on context |
| `0` or `$0` | Explicitly zero | `0.00` |
| `—` or `-0-` | Explicitly zero | `0.00` |
| `N/A` | Not applicable | `null` |
| `SEE STMT` | Value on supplemental page | `null` + flag `has_statement=true` |

### Two-Column Layout Parsing

Part III uses a two-column layout:
```
┌─────────────────────┬─────────────────────┐
│ 1  Ordinary income  │ 12 Section 179      │
│ 2  Net rental RE    │ 13 Other deductions  │
│ 3  Other rental     │ 14 Self-employment   │
│ 4a Guar. payments   │ 15 Credits           │
│ 4b Guar. payments   │ 16 Foreign trans.    │
│ 4c Total guar.      │ 17 AMT items         │
│ 5  Interest income  │ 18 Tax-exempt        │
│ 6a Ordinary divs    │ 19 Distributions     │
│ 6b Qualified divs   │ 20 Other info        │
│ 6c Div equivalents  │ 21 More info         │
│ 7  Royalties        │ 22 More info         │
│ 8  Net ST cap gain  │ 23 More info         │
│ 9a Net LT cap gain  │                      │
│ 9b Collectibles     │                      │
│ 9c Unrecaptured     │                      │
│ 10 Net sec 1231     │                      │
│ 11 Other income     │                      │
└─────────────────────┴─────────────────────┘
```

**Strategy**: Divide the Part III region into left/right halves using x-coordinate midpoint. Left half contains lines 1–11, right half contains lines 12–23.

### Common Extraction Failures to Handle

| Scenario | Root Cause | Mitigation |
|----------|-----------|------------|
| Value appears in wrong line | Coordinate drift between vendors | Anchor-relative positioning + tolerance |
| Missing decimal in currency | Some software prints `1,234` not `1,234.00` | Accept both integer and decimal formats |
| Merged text (no spaces) | Font/kerning issue in PDF | Use character-level extraction and reconstruct words |
| "STMT" parsed as a dollar amount | Text in value field position | Check for known non-numeric strings before attempting numeric parse |
| Negative sign separated from number | `-  1,234` with extra space | Strip internal whitespace before parsing |
| Partner TIN completely masked | Privacy masking `***-**-****` | Store as null, flag as masked |
| Multiple K-1s in one PDF | Multi-partner package from partnership | Detect form boundaries (look for "Schedule K-1" headers) and split into individual K-1s |
| Rotated or skewed text | Poor scan quality | OCR fallback with deskew preprocessing |

---

## Appendix A — Complete Field Inventory (Flat List)

Total unique fields/line-items on a K-1 form:

| Category | Count | Type |
|----------|-------|------|
| Part I single fields | 5 | (A, B, C, D + header year) |
| Part II single fields | 13 | (E, F, G, H1, H2, I1, I2, J×6, K1×6, K2, K3, L×7, M, N×2) |
| Part III single-value lines | 16 | (1, 2, 3, 4a, 4b, 4c, 5, 6a, 6b, 6c, 7, 8, 9a, 9b, 9c, 10, 12) |
| Part III multi-code lines | 10 | (11, 13, 14, 15, 16, 17, 18, 19, 20, 21–23) |
| Multi-code unique codes | ~90+ | Across all multi-code lines |
| **Total distinct parseable fields** | **~130+** | Including all sub-fields and code entries |

---

## Appendix B — Suggested Parser Field ID Convention

For mapping extracted text to database fields, use a hierarchical ID system:

```
part1.a                          → Partnership EIN
part1.b                          → Partnership name/address
part1.c                          → IRS center
part1.d                          → PTP checkbox

part2.e                          → Partner TIN
part2.f                          → Partner name/address
part2.g                          → General/limited partner
part2.h1                         → Domestic/foreign
part2.h2                         → DE info
part2.i1                         → Entity type
part2.i2                         → Retirement plan
part2.j.profit.beginning         → Profit % beginning
part2.j.profit.ending            → Profit % ending
part2.j.loss.beginning           → Loss % beginning
part2.j.loss.ending              → Loss % ending
part2.j.capital.beginning        → Capital % beginning
part2.j.capital.ending           → Capital % ending
part2.k1.nonrecourse.beginning   → Nonrecourse beginning
part2.k1.nonrecourse.ending      → Nonrecourse ending
part2.k1.qualified.beginning     → Qualified nonrecourse beginning
part2.k1.qualified.ending        → Qualified nonrecourse ending
part2.k1.recourse.beginning      → Recourse beginning
part2.k1.recourse.ending         → Recourse ending
part2.k2                         → Lower tier liabilities
part2.k3                         → Guarantee obligations
part2.l.beginning                → Beginning capital account
part2.l.contributed              → Capital contributed during year
part2.l.net_income               → Current year net income (loss)
part2.l.other                    → Other increase (decrease)
part2.l.withdrawals              → Withdrawals & distributions
part2.l.ending                   → Ending capital account
part2.l.basis_method             → Tax basis method (Tax/GAAP/704b/Other)
part2.m                          → Built-in gain/loss indicator
part2.n.beginning                → 704(c) beginning
part2.n.ending                   → 704(c) ending

part3.line1                      → Ordinary business income
part3.line2                      → Net rental real estate income
part3.line3                      → Other net rental income
part3.line4a                     → Guaranteed payments for services
part3.line4b                     → Guaranteed payments for capital
part3.line4c                     → Total guaranteed payments
part3.line5                      → Interest income
part3.line6a                     → Ordinary dividends
part3.line6b                     → Qualified dividends
part3.line6c                     → Dividend equivalents
part3.line7                      → Royalties
part3.line8                      → Net short-term capital gain
part3.line9a                     → Net long-term capital gain
part3.line9b                     → Collectibles (28%) gain
part3.line9c                     → Unrecaptured section 1250 gain
part3.line10                     → Net section 1231 gain
part3.line11.{code}              → Other income (code = A, B, C, ...)
part3.line12                     → Section 179 deduction
part3.line13.{code}              → Other deductions (code = A, B, C, ...)
part3.line14.{code}              → Self-employment (code = A, B, C)
part3.line15.{code}              → Credits (code = A, B, C, ...)
part3.line16.{code}              → Foreign transactions (code = A, B, ...)
part3.line17.{code}              → AMT items (code = A, B, C, ...)
part3.line18.{code}              → Tax-exempt income (code = A, B, C)
part3.line19.{code}              → Distributions (code = A, B, C)
part3.line20.{code}              → Other information (code = A, B, ...)
part3.line21.{code}              → Overflow 1
part3.line22.{code}              → Overflow 2
part3.line23.{code}              → Overflow 3
```

This convention allows the parser to produce a flat dictionary that maps directly to database storage and the review UI.
