"""This module provides functions to fetch Common Weakness Enumeration (CWE) data."""

import requests


def get_cwe_by_id(cwe_id):
    """Fetch CWE data by ID from the MITRE CWE API.

    Args:
        cwe_id (str): The CWE identifier, e.g., "CWE-79".

    Returns:
        dict: The JSON response from the API, or None if not found or error.
    """
    id = cwe_id.split("-")[-1]
    url = f"https://cwe-api.mitre.org/api/v1/cwe/weakness/{id}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"Error fetching CWE data: {error}")
        return None


print(get_cwe_by_id("CWE-79"))
