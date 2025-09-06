import os
import pandas as pd

# =========================
# CSV HELPERS
# =========================
def ensure_csv_header(csv_path):
    """
    Ensure the CSV file has the correct header.
    
    Parameter:
        csv_path: Path to the CSV file
    """
    if not os.path.exists(csv_path):
        df = pd.DataFrame(columns=["timestamp", "text"])
        df.to_csv(csv_path, index=False, encoding="utf-8")

def save_batch(csv_path, batch):
    """
    Save a batch of tweets to the CSV file.
    """
    if not batch:
        return

    df = pd.DataFrame(batch)
    df.to_csv(csv_path, index=False, mode='a', header=False, encoding="utf-8")