"""This module provides functions to fetch European Union Vulnerability Database (EUVd) data."""

import requests


def get_euvd_by_id(euvd_id):
    """Fetch EUVD data by ID from the ENISA EUVD API.

    Args:
        euvd_id (str): The EUVD identifier, e.g., "EUVD-2025-4893".

    Returns:
        dict: The JSON response from the API, or None if not found or error.
    """
    url = "https://euvdservices.enisa.europa.eu/api/enisaid"
    params = {"id": euvd_id}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"Error fetching EUVD data: {error}")
        return None


print(get_euvd_by_id("EUVD-2024-45012"))
