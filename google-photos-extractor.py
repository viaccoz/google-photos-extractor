import json
import re
import zipfile
from pathlib import Path
from pathvalidate import sanitize_filename

zip_path = next(Path().glob('takeout-*.zip'))
target_directory = Path('target')

def sanitize_description(description: str) -> str:
    description = description.strip()
    description = sanitize_filename(description)
    description = re.sub(r'\s{2,}', ' ', description)
    return description

def format_date(year = None, month = None, day = None):
    year = f"{int(year):04d}" if year else "XXXX"
    month = f"{int(month):02d}" if month else "XX"
    day = f"{int(day):02d}" if day else "XX"
    return f"{year}-{month}-{day}"

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
        return format_date(year, month, day)

    # Exact month: MM[./-]YY
    match = re.search(r'\b(\d{2})[./-](\d{4})\b', description)
    if match:
        month, year = match.groups()
        return format_date(year, month)

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
            return format_date(year, month)

    # Exact year
    match = re.search(r'\b(19|20)\d{2}\b', description)
    if match:
        year = match.group(0)
        return format_date(year)

    return format_date()

with zipfile.ZipFile(zip_path, 'r') as zf:
    target_files = zf.namelist()

    print('[*] Reading JSON files')

    descriptions = {}
    for file in target_files:
        if file.endswith('.json'):
            json_path = Path(file)
            base_path = json_path.with_suffix('').with_suffix('').as_posix() # Remove ".supplemental-metadata.json" or similar

            with zf.open(file) as jf:
                try:
                    jsondata = json.load(jf)
                    description = jsondata.get('description')
                    if description:
                        sanitized_description = sanitize_description(description)
                        if description.strip() != sanitized_description:
                            print(f"[*] Sanitized description:\n      {description}\n      {sanitized_description}")
                        descriptions[base_path] = sanitized_description
                except json.JSONDecodeError:
                    print(f"[-] Ignored invalid JSON: {file}")

    print('[*] Handling modified image files')

    files_to_remove = set()
    for file in target_files:
        match = re.search(r'^(.+)-modifié(\.[^.]+)$', file)
        if match:
            original_file = match.group(1) + match.group(2)
            if original_file in descriptions:
                descriptions[file] = descriptions.pop(original_file)
                files_to_remove.add(original_file)
                print(f"[*] Removed original image:\n      {original_file}\n      {file}")

    print('[*] Extracting image files')

    for file in target_files:
        if not file.endswith('.json') and not file.endswith('/') and file not in files_to_remove:
            file_path = Path(file)

            description = descriptions.get(file_path.as_posix())
            if description:
                sort_date = extract_sort_date(description)
                target_file_name = f"{sort_date}___{description}___{file_path.stem}{file_path.suffix}"
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
