"""
Repo Collateral & Margin Call Simulator
-----------------------------------------
Simulates a repo (repurchase agreement) financing trade: a bond posted as
collateral against borrowed cash, marked to market daily against a
haircut-adjusted margin threshold. Detects margin call events, computes
lender exposure over time, and simulates collateral top-up (cure) behavior.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ============================================
# Bond Pricing Function
# ============================================
def bond_price(face_value, coupon_rate, yield_rate, years_remaining, freq=2):
    """Prices a bond as the PV of coupon payments plus PV of face value at maturity."""
    coupon = face_value * coupon_rate / freq
    periods = round(years_remaining * freq)
    price = sum(coupon / (1 + yield_rate / freq) ** t for t in range(1, periods + 1))
    price += face_value / (1 + yield_rate / freq) ** periods
    return price


# ============================================
# Simulate a Moving Yield Path (random walk)
# ============================================
np.random.seed(42)
days = 90
daily_yield_changes = np.random.normal(loc=0, scale=0.0005, size=days)  # ~5bp daily vol
yields = 0.05 + np.cumsum(daily_yield_changes)

plt.figure(figsize=(10, 4))
plt.plot(yields)
plt.title('Simulated Yield Path (90 days)')
plt.ylabel('Yield')
plt.savefig('outputs/yield_path.png')
plt.close()


# ============================================
# Set Up the Repo Trade
# ============================================
face_value = 10_000_000     # $10mm face value bond used as collateral
coupon_rate = 0.05
initial_years = 10

collateral_values = []
for t, y in enumerate(yields):
    years_remaining = initial_years - (t / 365)
    price_per_100 = bond_price(face_value=100, coupon_rate=coupon_rate,
                                 yield_rate=y, years_remaining=years_remaining)
    actual_value = price_per_100 / 100 * face_value
    collateral_values.append(actual_value)

haircut = 0.02
initial_collateral_value = collateral_values[0]
cash_lent = initial_collateral_value * (1 - haircut)
required_collateral = cash_lent / (1 - haircut)

print(f"Initial collateral value: {initial_collateral_value:,.2f}")
print(f"Cash lent: {cash_lent:,.2f}")
print(f"Required collateral threshold: {required_collateral:,.2f}")


# ============================================
# Margin Call Detection
# ============================================
margin_calls = []
for t, cv in enumerate(collateral_values):
    if cv < required_collateral:
        shortfall = required_collateral - cv
        margin_calls.append({'day': t, 'collateral_value': cv, 'shortfall': shortfall})

margin_calls_df = pd.DataFrame(margin_calls)
print("\nMargin call events:")
print(margin_calls_df)


# ============================================
# Lender Exposure
# ============================================
exposure = [cash_lent - cv * (1 - haircut) for cv in collateral_values]


# ============================================
# Visualization
# ============================================
fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

ax[0].plot(collateral_values, label='Collateral Value')
ax[0].axhline(required_collateral, color='red', linestyle='--', label='Required Collateral Threshold')
for mc in margin_calls:
    ax[0].axvline(mc['day'], color='orange', alpha=0.2)
ax[0].legend()
ax[0].set_title('Collateral Value vs Margin Threshold')

ax[1].plot(exposure, color='purple', label='Lender Exposure ($)')
ax[1].axhline(0, color='black', linewidth=0.5)
ax[1].legend()
ax[1].set_title('Lender Exposure Over Time')

plt.tight_layout()
plt.savefig('outputs/margin_calls_exposure.png')
plt.close()


# ============================================
# Cure Logic (borrower posts additional collateral to cure shortfalls)
# ============================================
posted_additional = 0
cured_collateral_values = []

for t, cv in enumerate(collateral_values):
    effective_value = cv + posted_additional
    if effective_value < required_collateral:
        shortfall = required_collateral - effective_value
        posted_additional += shortfall
        effective_value = required_collateral
    cured_collateral_values.append(effective_value)

print(f"\nTotal additional collateral posted over 90 days: {posted_additional:,.2f}")

# Save summary outputs
margin_calls_df.to_csv('outputs/margin_calls.csv', index=False)
summary = pd.DataFrame({
    'day': range(days),
    'yield': yields,
    'collateral_value': collateral_values,
    'exposure': exposure,
    'cured_collateral_value': cured_collateral_values
})
summary.to_csv('outputs/simulation_summary.csv', index=False)
