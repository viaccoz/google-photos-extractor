import json
import re
import zipfile
from pathlib import Path
from pathvalidate import sanitize_filename

zip_path = next(Path().glob('takeout-*.zip'))
target_directory = Path('target')

SEASONS = {
    'printemps': '03',
    'été': '06',
    'ete': '06',
    'automne': '09',
    'hiver': '12'
}

# Exact date: DD[./-]MM[./-]YY or DD[./-]MM[./-]19YY or DD[./-]MM[./-]20YY
REGEXP_EXACT_DATE = re.compile(r'\s*\b(\d{2})[./-](\d{2})[./-](\d{2}|(?:19|20)\d{2})\b\s*')

# Exact month: MM[./-]19YY or MM[./-]20YY
REGEXP_EXACT_MONTH = re.compile(r'\s*\b(\d{2})[./-]((?:19|20)\d{2})\b\s*')

# Exact season: SEASON 19YY or SEASON 20YY
REGEXP_EXACT_SEASON = re.compile(rf'\s*\b({"|".join(SEASONS.keys())})\s+((?:19|20)\d{2})\b\s*', re.IGNORECASE)

# Exact year: 19YY or 20YY
REGEXP_EXACT_YEAR = re.compile(r'\s*\b((?:19|20)\d{2})\b\s*')

def sanitize_description(description: str) -> str:
    description = description.strip()
    description = description.replace('oeu', 'œu')
    description = re.sub(r' -([^ ])', ' - \\1', description)
    description = re.sub(r'([^ ])- ', '\\1 - ', description)
    description = re.sub(r'\s{2,}', ' ', description)
    description = sanitize_filename(description)
    return description

def sanitize_directory(directory: str) -> str:
    directory = directory.strip()
    directory = re.sub(r'\s{2,}', ' ', directory)
    return directory

def format_date(year: str = None, month: str = None, day: str = None) -> str:
    year = f'{int(year):04d}' if year else 'XXXX'
    month = f'{int(month):02d}' if month else 'XX'
    day = f'{int(day):02d}' if day else 'XX'
    return f'{year}-{month}-{day}'

def get_description_without_date(description: str, regular_expression: str) -> str:
    description = re.sub(regular_expression, '', description)
    description = description[:1].upper() + description[1:]
    return description

def extract_sort_date_and_description(description: str) -> str:

    # Exact date
    match = REGEXP_EXACT_DATE.search(description)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            if int(year) > 30:
                year = f'19{year}'
            else:
                year = f'20{year}'
        return format_date(year, month, day), get_description_without_date(description, REGEXP_EXACT_DATE)

    # Exact month
    match = REGEXP_EXACT_MONTH.search(description)
    if match:
        month, year = match.groups()
        return format_date(year, month), get_description_without_date(description, REGEXP_EXACT_MONTH)

    # Exact season
    match = REGEXP_EXACT_SEASON.search(description)
    if match:
        season, year = match.groups()
        return format_date(year, SEASONS.get(season)), get_description_without_date(description, REGEXP_EXACT_SEASON)

    # Exact year
    match = REGEXP_EXACT_YEAR.search(description)
    if match:
        year = match.group(1)
        return format_date(year), get_description_without_date(description, REGEXP_EXACT_YEAR)

    return format_date(), description

with zipfile.ZipFile(zip_path, 'r') as zf:
    target_files = zf.namelist()

    print('[*] Reading JSON files')

    sort_dates_and_descriptions = {}
    for file in target_files:
        if file.endswith('.json'):
            json_path = Path(file)
            base_path = json_path.as_posix()
            base_path = re.sub(r'(?:\.supp?l?e?m?e?n?t?a?l?-?m?e?t?a?d?a?t?a?)?\.json$', '', base_path)

            with zf.open(file) as jf:
                try:
                    jsondata = json.load(jf)
                    description = jsondata.get('description')
                    if description:
                        sort_date, description = extract_sort_date_and_description(description)
                        sanitized_description = sanitize_description(description)
                        if description.rstrip() != sanitized_description:
                            print(f'[*] Sanitized description:\n      {description}\n      {sanitized_description}')
                        if re.search(r'/original_[^/]+_$', base_path):
                            print(f'[*] Dirty fix for original_guid_.json: {base_path}')
                            base_path += 'P.jpg'
                        sort_dates_and_descriptions[base_path] = sort_date, sanitized_description
                except json.JSONDecodeError:
                    print(f'[-] Ignored invalid JSON: {file}')

    print('[*] Handling modified image files')

    files_to_remove = set()
    for file in target_files:
        match = re.search(r'^(.+)(?:-modifié|\(1\))(\.[^.]+)$', file)
        if match:
            original_file = match.group(1) + match.group(2)
            if file not in sort_dates_and_descriptions and original_file in sort_dates_and_descriptions:
                sort_dates_and_descriptions[file] = sort_dates_and_descriptions.pop(original_file)
                files_to_remove.add(original_file)
                print(f'[*] Removed original image:\n      {original_file}\n      {file}')

    print('[*] Extracting image files')

    for file in target_files:
        if not file.endswith('.json') and not file.endswith('/') and file not in files_to_remove:
            file_path = Path(file)

            sort_date, description = sort_dates_and_descriptions.pop(file_path.as_posix(), (None, None))
            if sort_date and description:
                target_file_name = f'{sort_date}___{description}___{file_path.stem}{file_path.suffix}'
            else:
                print(f'[-] Missing data for: {file_path}')
                target_file_name = f'XXXX-XX-XX___-___{file_path.stem}{file_path.suffix}'

            directory = str(file_path.parent)
            sanitized_directory = sanitize_directory(directory)
            if directory != sanitized_directory:
                print(f'[-] Sanitized directory:\n      {directory}\n      {sanitized_directory}')

            current_target_directory = target_directory / sanitized_directory
            current_target_directory.mkdir(parents=True, exist_ok=True)
            target_path = current_target_directory / target_file_name

            #print(f'[*] Extracting image: {target_path}')

            if len(str(target_path)) > 256:
                print(f'[-] Path exceeds length limit: {target_path}')

            with zf.open(file) as source, open(target_path, 'wb') as target:
                target.write(source.read())
                #print(f'[+] Extracted image: {file_path.name}')

    for base_path in sort_dates_and_descriptions.keys():
        print(f'[-] Unused description for: {base_path}')
