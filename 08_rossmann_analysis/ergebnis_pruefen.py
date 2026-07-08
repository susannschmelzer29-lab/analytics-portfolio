import pandas as pd

df = pd.read_csv("output/rossmann_master_tableau.csv", low_memory=False)

print("Form (Zeilen, Spalten):", df.shape)
print("\nSpalten:")
print(df.columns.tolist())
print("\nErste Zeilen:")
print(df.head(10))
print("\nInfo:")
print(df.info())
