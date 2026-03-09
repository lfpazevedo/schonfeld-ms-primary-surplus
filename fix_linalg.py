import json

with open('notebook/schonfeld_fiscal_regime_steepening_strategy.ipynb', 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code' and 'def fit_2regime_markov' in ''.join(cell['source']):
        source = cell['source']
        for i, line in enumerate(source):
            if 'except ' in line or 'except:\n' == line:
                source[i] = "    except BaseException:\n"
        cell['source'] = source

with open('notebook/schonfeld_fiscal_regime_steepening_strategy.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)
