"""This module provides functions to fetch vulnerability data from the VulDB API."""

import requests


def get_vuldb_by_cve(cve_id, apikey):
    """
    Fetch VulDB data by CVE ID using VulDB API.

    Args:
        cve_id (str): The CVE identifier, e.g., "CVE-2022-27225".
        apikey (str): Your VulDB API key.

    Returns:
        dict: The JSON response from the API, or None if not found or error.
    """
    url = "https://vuldb.com/?api"
    data = {"apikey": apikey, "advancedsearch": f"cve:{cve_id}"}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"}
    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"Error fetching VulDB data: {error}")
        return None


print(get_vuldb_by_cve("CVE-2022-27225", "3f16fb7414aefdb1d375947c911c7141"))
