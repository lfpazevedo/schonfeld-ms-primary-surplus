import json

with open('notebook/schonfeld_fiscal_regime_steepening_strategy.ipynb', 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if 'def calculate_position_v6' in source:
            print("FOUND v6 function")
            lines = source.split('\n')
            for i, l in enumerate(lines):
                if 'def calculate_position_v6' in l:
                    print(f"Lines around function:")
                    print('\n'.join(lines[i:i+50]))
                    break
        elif 'calculate_position_v6' in source and 'def ' not in source:
            print("FOUND usage:")
            lines = source.split('\n')
            for l in lines:
                if 'calculate_position_v6' in l:
                    print(l)
