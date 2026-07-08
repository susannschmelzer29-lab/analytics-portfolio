import pandas as pd

df = pd.read_csv("output/rossmann_master_tableau.csv", low_memory=False)

print("Shape (rows, columns):", df.shape)
print("\nColumns:")
print(df.columns.tolist())
print("\nFirst rows:")
print(df.head(10))
print("\nInfo:")
print(df.info())
