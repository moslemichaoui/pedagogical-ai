"""Verify _truth.py correctness + generate our pedagogical_ai _truth_out for diffing."""
import os, pathlib, sys
sys.stdin.reconfigure(encoding='utf-8', errors='replace')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def load(path):
    path = str(path).rstrip('/\\')
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

# Source of truth comparison: sibling tree tool pair
sibling_truth = r'C:\Users\ichao\Documents\pedagogical_ai\app\services\_truth_run.py'
sib_truth = load(sibling_truth)
host_truth = load(r'C:\Users\ichao\Documents\pedagogical_ai\app\services\_truth.py')
PROJECT = r'C:\Users\ichao\Documents\pedagogical_ai'

lines = []
lines.append('=== TRUTH: pedagogy_ai (our canonical) vs tree_tool_pair (source of truth) ===')
lines.append('')

pal_in_exports = 'EXPORTS' in host_truth and 'MODELS' in host_truth and 'APP' in host_truth
lines.append(f'host_truth file size: {len(host_truth)}')
lines.append(f'host_truth mentions EXPORTS/MODELS/APP: {pal_in_exports}')
lines.append('')

# Also the pedagogical_ai pedagogical pack services listing
msvc = os.path.join(PROJECT, 'app', 'services')
lines.append(f'message_services_dir exists: {os.path.isdir(msvc)}')
if os.path.isdir(msvc):
    lines.append('message_services_files: ' + ', '.join(sorted(os.listdir(msvc))))
lines.append('')

out = '\n'.join(lines)
out_path = os.path.join(r'C:\Users\ichao\Documents\pedagogical_ai', '_verify_truth_out.txt')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(out)
print(out)
print('---WROTE---', out_path)
