import os
import requests
from datasets import load_dataset

DATA_DIR = "ddxplus_data"
CONDITIONS_URL = "https://huggingface.co/datasets/aai530-group6/ddxplus/resolve/main/release_conditions.json"
EVIDENCES_URL = "https://huggingface.co/datasets/aai530-group6/ddxplus/resolve/main/release_evidences.json"

def download_file(url, dest_path):
    print(f"Downloading {url} to {dest_path}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("Download complete.")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    csv_path = os.path.join(DATA_DIR, "validate.csv")
    if not os.path.exists(csv_path):
        print("Downloading validate split from HuggingFace datasets...")
        ds = load_dataset("aai530-group6/ddxplus", split="validate")
        df = ds.to_pandas()
        df.to_csv(csv_path, index=False)
        print(f"Saved {csv_path} with {len(df)} records.")
    else:
        print(f"Found {csv_path}, skipping download.")
        
    conditions_json_path = os.path.join(DATA_DIR, "release_conditions.json")
    if not os.path.exists(conditions_json_path):
        try:
            download_file(CONDITIONS_URL, conditions_json_path)
        except Exception as e:
            print(f"Error downloading conditions json: {e}")
    else:
        print(f"Found {conditions_json_path}, skipping download.")

    evidences_json_path = os.path.join(DATA_DIR, "release_evidences.json")
    if not os.path.exists(evidences_json_path):
        try:
            download_file(EVIDENCES_URL, evidences_json_path)
        except Exception as e:
            print(f"Error downloading evidences json: {e}")
    else:
        print(f"Found {evidences_json_path}, skipping download.")

if __name__ == "__main__":
    main()
