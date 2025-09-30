"""This module provides functions to fetch CVE and CPE data from the NVD API."""

import requests


def get_cve_by_id(cve_id, api_key=None):
    """Fetch CVE data by ID from the NVD API.

    Args:
        cve_id (str): The CVE identifier, e.g., "CVE-2024-12345".

    Returns:
        dict: The JSON response from the API, or None if not found or error.
    """
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {"cveId": cve_id}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"Error fetching CVE data: {error}")
        return None


def get_cpe_by_id(cpeString, api_key=None):
    """Fetch CPE data by ID from the NVD API.

    Args:
        cpe_id (str): The CPE identifier, e.g., "cpe:2.3:a:example:product:1.0:*:*:*:*:*:*:*".

    Returns:
        dict: The JSON response from the API, or None if not found or error.
    """
    url = "https://services.nvd.nist.gov/rest/json/cpes/2.0"
    params = {"cpeMatchString": cpeString}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TaranisNG/1.0; +https://github.com/SK-CERT/Taranis-NG)"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"Error fetching CPE data: {error}")
        return None


print(get_cve_by_id("CVE-2024-12345"))
print(get_cpe_by_id("cpe:2.3:o:microsoft:windows_10"))
