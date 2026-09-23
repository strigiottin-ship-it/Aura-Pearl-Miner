# Scale WhatToMine 60 TH/s hour figures to live 65.33 TH/s @ 82W
live_th = 65.33
base_th = 60.0
rev_h_usd = 0.10 * (live_th/base_th)
rev_h_btc = 0.000001 * (live_th/base_th)
power_w = 82
kwh_price = 0.10  # EUR/USD-ish; Germany often 0.30 EUR - note both
cost_h_01 = (power_w/1000) * 0.10
cost_h_30 = (power_w/1000) * 0.30  # typical DE household-ish EUR
print(f"est_rev_usd_h {rev_h_usd:.3f}")
print(f"est_rev_btc_h {rev_h_btc:.8f}")
print(f"elec_01 {cost_h_01:.4f} elec_30eur {cost_h_30:.4f}")
print(f"profit_01 {rev_h_usd-cost_h_01:.3f}")
print(f"profit_30 {rev_h_usd-cost_h_30:.3f}")
# from balance growth if session uptime
bal = 0.00000095
uptime = 1059
# balance is cumulative not only this session - use WhatToMine primary
print(f"shares_per_h {10/(uptime/3600):.1f} accepted/h so far")
