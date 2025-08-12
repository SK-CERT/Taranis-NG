"""This module provides functions to fetch Exploit Prediction Scoring System (EPSS) data."""

import requests


def get_epss_by_cve_id(cve_id):
    """Fetch EPSS data by ID from the EPSS API.

    Args:
        cve_id (str): The CVE identifier, e.g., "CVE-2022-27225".

    Returns:
        dict: The JSON response from the API, or None if not found or error.
    """
    url = "https://api.first.org/data/v1/epss"
    params = {"cve": cve_id}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"Error fetching EPSS data: {error}")
        return None


print(get_epss_by_cve_id("CVE-2022-27225"))
