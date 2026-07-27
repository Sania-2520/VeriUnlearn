import json
with open('evaluation/results/phase2_complete/.checkpoint.json') as f:
    data = json.load(f)
completed = data['completed']
print(f'Completed: {len(completed)}')

from collections import Counter
algos = Counter(k.split('|')[0] for k in completed)
datasets = Counter(k.split('|')[1] for k in completed)
ratios = Counter(k.split('|')[2] for k in completed)
print(f'Algorithms: {dict(algos)}')
print(f'Datasets: {dict(datasets)}')
print(f'Ratios: {dict(ratios)}')
assert len(completed) == 300, f'Expected 300, got {len(completed)}'
print('SUCCESS: All 300 runs complete!')
