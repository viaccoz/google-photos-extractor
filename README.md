# Google Photos Takeout Descriptions Extractor

This Python script extracts specific photo folders from a Google Takeout `.zip` archive, renames image files with their associated descriptions (from metadata `.json` files), and saves them to a local target directory.

# Requirements

- Python 3.7+
- [pathvalidate](https://pypi.org/project/pathvalidate/)

Install dependencies:

```bash
pip install pathvalidate
```

# Process

1. Find the first `takeout-*.zip` file in the current directory
2. Extract photos from selected folders (from `folders_to_extract`)
3. Read `.json` metadata to extract descriptions for each photo
4. Rename image files to include the description
5. Skip invalid JSON files and warns about filenames longer than 150 characters
6. Outputs to the `target/` folder, preserving folder structure
