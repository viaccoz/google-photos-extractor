import json
import re
import zipfile
from pathlib import Path
from pathvalidate import sanitize_filename

zip_path = next(Path().glob('takeout-*.zip'))
target_directory = Path('target')
folders_to_extract = ['Photos from 2024', 'Photos from 2025']

def sanitize_description(description: str) -> str:
    description = description.strip()
    description = sanitize_filename(description)
    description = re.sub(r'\s{2,}', ' ', description)
    return description

def extract_sort_date(description: str) -> str | None:
    description = description.lower()

    # Exact date: DD[./-]MM[./-]YYYY or DD[./-]MM[./-]YY
    match = re.search(r'\b(\d{2})[./-](\d{2})[./-](\d{2}|\d{4})\b', description)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            if int(year) > 30:
                year = f"19{year}"
            else:
                year = f"20{year}"
        return f"{year}-{month}-{day}"

    # Exact month: MM[./-]YY
    match = re.search(r'\b(\d{2})[./-](\d{4})\b', description)
    if match:
        month, year = match.groups()
        return f"{year}-{month}"

    # Exact season
    seasons = {
        'printemps': '03',
        'été': '06',
        'ete': '06',
        'automne': '09',
        'hiver': '12'
    }
    for season, month in seasons.items():
        match = re.search(rf'{season}\s+(\d{{4}})', description)
        if match:
            year = match.group(1)
            return f"{year}-{month}"

    # Exact year
    match = re.search(r'\b(19|20)\d{2}\b', description)
    if match:
        return match.group(0)

    return None

with zipfile.ZipFile(zip_path, 'r') as zf:
    target_files = [f for f in zf.namelist() if any(f.startswith(f"Takeout/Google Photos/{folder}/") for folder in folders_to_extract)]
    #target_files = [f for f in zf.namelist() if f.startswith(f"Takeout/Google Photos/")] # Extract everything

    print('[*] Reading JSON files')

    descriptions = {}
    for file in target_files:
        if file.endswith('.json'):
            json_path = Path(file)
            base_path = str(json_path.with_suffix('').with_suffix('')) # Remove ".supplemental-metadata.json" or similar

            with zf.open(file) as jf:
                try:
                    jsondata = json.load(jf)
                    description = jsondata.get('description')
                    if description:
                        sanitized_description = sanitize_description(description)
                        if description.strip() != sanitized_description:
                            print(f"[*] Sanitized description:\n    {description}\n    {sanitized_description}")
                        descriptions[base_path] = sanitized_description
                except json.JSONDecodeError:
                    print(f"[-] Ignored invalid JSON: {file}")

    print('[*] Extracting image files')

    for file in target_files:
        if not file.endswith('.json') and not file.endswith('/'):
            file_path = Path(file)

            description = descriptions.get(file)
            if description:
                sort_date = extract_sort_date(description)
                if sort_date:
                    target_file_name = f"{sort_date}___{description}___{file_path.stem}{file_path.suffix}"
                else:
                    target_file_name = f"{description}___{file_path.stem}{file_path.suffix}"
            else:
                target_file_name = file_path.name

            current_target_directory = target_directory / file_path.parent
            current_target_directory.mkdir(parents=True, exist_ok=True)
            target_path = current_target_directory / target_file_name

            #print(f"[*] Extracting image: {target_file_name}")

            if len(str(target_path)) > 256:
                print(f"[-] Path exceeds length limit: {target_path}")

            with zf.open(file) as source, open(target_path, 'wb') as target:
                target.write(source.read())
                #print(f"[+] Extracted image: {file_path.name}")
