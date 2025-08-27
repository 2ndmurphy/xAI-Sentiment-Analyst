import os
import pandas as pd

def ensure_csv_header(csv_path):
    if not os.path.exists(csv_path):
        df = pd.DataFrame(columns=["timestamp", "raw", "clean"])
        df.to_csv(csv_path, index=False, encoding="utf-8")

def save_batch(csv_path, batch):
    if not batch:
        return
    df = pd.DataFrame(batch, columns=["timestamp", "raw", "clean"])
    df.to_csv(csv_path, mode="a", index=False, header=False, encoding="utf-8")