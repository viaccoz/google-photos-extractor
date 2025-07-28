import json
import zipfile
from pathlib import Path
from pathvalidate import sanitize_filename

zip_path = next(Path().glob('takeout-*.zip'))
target_directory = Path('target')
folders_to_extract = ['Photos from 2024', 'Photos from 2025']

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
                        description = description.strip()
                        sanitized_description = sanitize_filename(description)
                        if description != sanitized_description:
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
                target_file_name = f"{file_path.stem}___{description}{file_path.suffix}"
            else:
                target_file_name = file_path.name

            if len(target_file_name) > 200:
                print(f"[*] Name exceeds length limit: {target_file_name}")

            current_target_directory = target_directory / file_path.parent
            current_target_directory.mkdir(parents=True, exist_ok=True)

            with zf.open(file) as source, open(current_target_directory / target_file_name, 'wb') as target:
                target.write(source.read())
                #print(f"[*] Extracted image: {file_path.name}")
