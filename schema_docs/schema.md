
# Financial Transactions Database — Schema Reference

## Database Overview
A banking dataset covering transactions from 2010s, containing 2,000 customers,
6,146 cards, and 13M+ transactions. Fraud labels available for ~8.9M transactions.
Fraud rate is approximately 0.15% (highly imbalanced).

---

## Table: transactions
**Grain**: One row = one transaction  
**Row count**: ~13.3M  
**Primary key**: id

| Column         | Type    | Description |
|----------------|---------|-------------|
| id             | int     | Unique transaction ID |
| date           | string  | Timestamp of transaction (YYYY-MM-DD HH:MM:SS) |
| client_id      | int     | FK → users.id |
| card_id        | int     | FK → cards.id |
| amount         | float   | Transaction amount in USD (negative = refund) |
| use_chip       | string  | Payment method: 'Swipe Transaction', 'Chip Transaction', 'Online Transaction' |
| merchant_id    | int     | Merchant identifier |
| merchant_city  | string  | City where transaction occurred |
| merchant_state | string  | State where transaction occurred (2-letter code) |
| zip            | float   | Merchant ZIP code |
| mcc            | int     | FK → mcc_codes.mcc (merchant category code) |
| errors         | string  | Transaction error flags, NULL if none |

**Gotchas**:
- `amount` can be negative (refunds/reversals) — use `amount > 0` for spend analysis
- `errors` is NULL for most rows — don't filter it out unless specifically needed
- `date` is a string, cast with `CAST(date AS TIMESTAMP)` for date math

---

## Table: users
**Grain**: One row = one customer  
**Row count**: 2,000  
**Primary key**: id

| Column           | Type   | Description |
|------------------|--------|-------------|
| id               | int    | Unique user ID |
| current_age      | int    | Customer's current age |
| retirement_age   | int    | Expected retirement age |
| birth_year       | int    | Year of birth |
| birth_month      | int    | Month of birth |
| gender           | string | 'Male' or 'Female' |
| address          | string | Street address |
| latitude         | float  | Home location latitude |
| longitude        | float  | Home location longitude |
| per_capita_income| float  | Per capita income in USD (already cleaned, no $ sign) |
| yearly_income    | float  | Annual income in USD |
| total_debt       | float  | Total debt in USD |
| credit_score     | int    | Credit score (300–850 range) |
| num_credit_cards | int    | Number of credit cards held |

---

## Table: cards
**Grain**: One row = one card (users can have multiple cards)  
**Row count**: 6,146  
**Primary key**: id

| Column               | Type   | Description |
|----------------------|--------|-------------|
| id                   | int    | Unique card ID |
| client_id            | int    | FK → users.id |
| card_brand           | string | 'Visa', 'Mastercard', 'Amex', 'Discover' |
| card_type            | string | 'Debit', 'Credit' |
| card_number          | int    | Card number (synthetic) |
| expires              | string | Expiry date MM/YYYY |
| cvv                  | int    | CVV code |
| has_chip             | string | 'YES' or 'NO' |
| num_cards_issued     | int    | Number of cards issued on this account |
| credit_limit         | float  | Credit limit in USD (already cleaned, no $ sign) |
| acct_open_date       | string | Account open date MM/YYYY |
| year_pin_last_changed| int    | Year PIN was last changed |
| card_on_dark_web     | string | 'Yes' or 'No' — whether card appears on dark web |

**Gotchas**:
- One user can have multiple cards — JOIN on cards.client_id = users.id
- `card_on_dark_web = 'Yes'` is a high-risk signal worth flagging in fraud analysis

---

## Table: mcc_codes
**Grain**: One row = one merchant category  
**Row count**: 109  
**Primary key**: mcc

| Column      | Type   | Description |
|-------------|--------|-------------|
| mcc         | int    | Merchant Category Code |
| description | string | Human-readable category name (e.g. 'Eating Places and Restaurants') |

---

## Table: fraud_labels
**Grain**: One row = one labeled transaction  
**Row count**: ~8.9M (training set only, not all transactions are labeled)  
**Primary key**: transaction_id

| Column         | Type | Description |
|----------------|------|-------------|
| transaction_id | int  | FK → transactions.id |
| is_fraud       | int  | 1 = fraudulent, 0 = legitimate |

**Gotchas**:
- Only ~67% of transactions have labels — always use INNER JOIN (not LEFT JOIN)
  when fraud label is required, to avoid NULL confusion
- Fraud rate is 0.15% — when calculating fraud rates use COUNT + AVG(is_fraud),
  not SUM, to avoid confusion

---

## Common Join Patterns

### Full enriched transaction view
```sql
SELECT
    t.*,
    u.gender, u.credit_score, u.yearly_income,
    c.card_brand, c.card_type, c.card_on_dark_web,
    m.description AS merchant_category,
    fl.is_fraud
FROM transactions t
JOIN users u         ON t.client_id = u.id
JOIN cards c         ON t.card_id   = c.id
JOIN mcc_codes m     ON t.mcc       = m.mcc
JOIN fraud_labels fl ON t.id        = fl.transaction_id
```

### Fraud rate by merchant category
```sql
SELECT
    m.description,
    COUNT(*)              AS total_txns,
    SUM(fl.is_fraud)      AS fraud_count,
    AVG(fl.is_fraud)*100  AS fraud_rate_pct
FROM transactions t
JOIN mcc_codes m     ON t.mcc = m.mcc
JOIN fraud_labels fl ON t.id  = fl.transaction_id
GROUP BY m.description
ORDER BY fraud_rate_pct DESC
```
