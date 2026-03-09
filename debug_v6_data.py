import json

with open('notebook/schonfeld_fiscal_regime_steepening_strategy.ipynb', 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        if 'v6_data =' in source or 'v6_results =' in source:
            lines = source.split('\n')
            for i, l in enumerate(lines):
                if 'v6_data' in l or 'v6_results' in l:
                    print('\n'.join(lines[max(0, i-5):i+20]))
                    break
