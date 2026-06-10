

import os
import json
import requests

class QueryEnricher():


    URL_1 = "https://api.example.com/endpoint1"
    URL_2 = "https://api.example.com/endpoint2"

    STORAGE_PATH = os.path.join("storage", "query_enriching.json")

    def __init__(self):

        os.makedirs(os.path.dirname(self.STORAGE_PATH), exist_ok=True)
        self.data = self._load_json(self.STORAGE_PATH)

    def fetch_and_store(self):
        """
        Fetch JSON from both APIs, transform if needed, combine,
        and save to disk and memory.
        """
        resp1 = requests.get(self.URL_1)
        resp1.raise_for_status()
        raw1 = resp1.json()

        resp2 = requests.get(self.URL_2)
        resp2.raise_for_status()
        raw2 = resp2.json()

        data1 = self._transform1(raw1)
        data2 = self._transform2(raw2)

        combined = {**data1, **data2}

        self._save_json(combined, self.STORAGE_PATH)
        
        self.data = combined

    def _transform1(self, raw: dict) -> dict:
        return raw

    def _transform2(self, raw: dict) -> dict:
        return raw

    def _load_json(self, path: str) -> dict:
        """
        Load JSON from disk, or return empty dict if missing/invalid.
        """
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print(f"Warning: could not load JSON from {path}, starting fresh.")
            return {}

    def _save_json(self, data: dict, path: str):
        """
        Save dict as JSON to disk.
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Saved combined JSON to {path}")


    def get_info_to_enrich_query(self, query):
        #TODO aquesta classe encara no s-ha provat ni esta a l indexador i al chatbot, es un pas previ per a donar context al llm.
        if "GEI" in query:
            return "GEI: grau enginyeria informatica"
        
        return ""