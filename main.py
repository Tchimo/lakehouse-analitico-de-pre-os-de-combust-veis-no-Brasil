import pandas as pd
df = pd.read_excel("data/raw/semanal_municipios_2026.xlsx", header=None, nrows=20)
for i, row in df.iterrows():
    print(i, list(row.values))