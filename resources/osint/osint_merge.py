#! /usr/bin/env python3

"""
This script is used by GitHub Actions to merge all OSINT data files into a single files.

                        !PLESE DO NOT RUN THIS MANUALLY!
"""

import os
import json

all_filename = "all"

version = 1


def merge_osint_files(base_folder_path):
    """Merge JSON files containing OSINT data from a specified base folder.

    This function traverses the directory tree rooted at `base_folder_path`,
    finds all JSON files (excluding those named as the category filename),
    and merges their "data" fields. The merged data is saved in two ways:
    1. For each folder, a merged JSON file is created containing the combined
       data from all JSON files in that folder.
    2. A single merged JSON file is created containing the combined data from
       all JSON files in the entire directory tree.
    Args:
        base_folder_path (str): The path to the base folder containing the
                                JSON files to be merged.
    Raises:
        FileNotFoundError: If the specified base folder path does not exist.
        JSONDecodeError: If any of the JSON files are not properly formatted.
    """
    folder_merged_data = {}

    for root, _, files in os.walk(base_folder_path):
        folder_data = []
        for file in files:
            if file.endswith(".json") and file != f"{all_filename}.json":
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    json_data = json.load(f)
                    if "data" in json_data:
                        folder_data.extend(json_data["data"])
        if folder_data:
            folder_merged_data[root] = sorted(folder_data, key=lambda x: x.get("name", ""))

    # Save merged data for each folder
    for folder, data in folder_merged_data.items():
        merged_file_path = os.path.join(folder, f"{all_filename}.json")
        with open(merged_file_path, "w") as f:
            json.dump({"version": version, "data": data}, f, indent=4)
        print(f"Merged data saved to {merged_file_path}")

    # Save all merged data
    all_merged_data = [item for sublist in folder_merged_data.values() for item in sublist]
    if all_merged_data:
        all_merged_file_path = os.path.join(base_folder_path, f"{all_filename}.json")
        with open(all_merged_file_path, "w") as f:
            json.dump({"version": version, "data": sorted(all_merged_data, key=lambda x: x.get("name", ""))}, f, indent=4)
        print(f"All merged data saved to {all_merged_file_path}")


if __name__ == "__main__":
    base_folder_path = os.path.dirname(os.path.abspath(__file__))
    merge_osint_files(base_folder_path)
