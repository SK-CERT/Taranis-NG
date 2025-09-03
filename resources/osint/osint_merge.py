#!/usr/bin/env python3

"""This script is used by GitHub Actions to merge all OSINT data files into a single files.

!PLEASE DO NOT RUN THIS MANUALLY!
"""

import json
import logging
import os
from pathlib import Path

ALL_FILENAME = "all"

VERSION = 1

logger = logging.getLogger(__name__)


def merge_osint_files(base_folder_path: Path) -> None:
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
    files_processed = 0
    files_skipped = 0

    for root, _, files in os.walk(base_folder_path):
        folder_data = []
        for file in files:
            if file.endswith(".json") and file != f"{ALL_FILENAME}.json":
                file_path = Path(root) / file
                try:
                    with file_path.open() as f:
                        json_data = json.load(f)
                        if "data" in json_data:
                            folder_data.extend(json_data["data"])
                            files_processed += 1
                except (json.JSONDecodeError, OSError):
                    logger.exception("Failed to process %s: ", file_path)
                    files_skipped += 1
        if folder_data:
            folder_merged_data[root] = sorted(folder_data, key=lambda x: x.get("name", ""))
    logger.info("Processed %d files, skipped %d files due to errors.", files_processed, files_skipped)

    # Save merged data for each folder
    if not folder_merged_data:
        logger.warning("No JSON files found to merge in %s.", base_folder_path)
        return
    for folder, data in folder_merged_data.items():
        merged_file_path = Path(folder) / f"{ALL_FILENAME}.json"
        with merged_file_path.open("w") as f:
            json.dump({"version": VERSION, "data": data}, f, indent=4)
            f.write("\n")
        logger.info("Merged data saved to %s", merged_file_path)
        logger.info("Merged %d items in folder %s", len(data), folder)

    # Save all merged data
    all_merged_data = [item for sublist in folder_merged_data.values() for item in sublist]
    if all_merged_data:
        all_merged_file_path = Path(base_folder_path) / f"{ALL_FILENAME}.json"
        with all_merged_file_path.open("w") as f:
            json.dump(
                {
                    "version": VERSION,
                    "data": sorted(all_merged_data, key=lambda x: x.get("name", "")),
                },
                f,
                indent=4,
            )
            f.write("\n")
        logger.info("All merged data saved to %s", all_merged_file_path)
    logger.info("Total merged items: %d", len(all_merged_data))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    base_folder_path = Path(__file__).resolve().parent
    merge_osint_files(base_folder_path)
