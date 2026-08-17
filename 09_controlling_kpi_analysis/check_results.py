"""Quick QA check of the controlling KPI outputs."""
import pandas as pd

kpi = pd.read_csv("output/kpi_controlling.csv")
print("KPI cockpit:")
print(kpi.to_string(index=False))

pnl = pd.read_csv("output/pnl_by_storetype.csv")
print("\nP&L by store type (rows, columns):", pnl.shape)
print(pnl[["StoreType", "Stores", "Revenue", "OperatingProfit", "OperatingMarginPct"]].to_string(index=False))

store = pd.read_csv("output/profit_by_store.csv")
print("\nLoss-making stores under the assumed model:",
      int((store["OperatingProfit"] < 0).sum()), "of", store.shape[0])
