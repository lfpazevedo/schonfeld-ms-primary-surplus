import json

with open('notebook/schonfeld_fiscal_regime_steepening_strategy.ipynb', 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if 'def calculate_position_v6' in source:
            lines = source.split('\n')
            for i, l in enumerate(lines):
                if 'def calculate_position_v6' in l:
                    print('\n'.join(lines[i+45:i+70]))
                    break
