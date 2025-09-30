"""This module provides functions to fetch Open Source Vulnerability (OSV) data."""

import requests


def get_osv_by_id(osv_id):
    """Fetch OSV data by ID from the OSV API.

    Args:
        osv_id (str): The OSV identifier, e.g., "OSV-2020-111".

    Returns:
        dict: The JSON response from the API, or None if not found or error.
    """
    url = f"https://api.osv.dev/v1/vulns/{osv_id}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"Error fetching OSV data: {error}")
        return None


print(get_osv_by_id("OSV-2020-111"))
