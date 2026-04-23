# -*- coding: utf-8 -*-
"""
csi10项目临时文件清理脚本
Priority: P0（强制执行）
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path('E:/csi10')
BACKUP_DIR = PROJECT_DIR / 'backups' / datetime.now().strftime('%Y-%m-%d')

# 清理规则
CLEANUP_RULES = {
    'test_scripts': ['test_*.py', 'check_*.py', 'verify_*.py', 'diag_*.py'],
    'fix_scripts': ['fix_*.py', 'upgrade_*.py', 'analyze_*.py'],
    'temp_backups': ['*_backup_*.*', '*.bak'],
    'temp_files': ['*_temp.*', '*_tmp.*', '*.tmp'],
}

# 保留规则
KEEP_RULES = {
    'core_scripts': ['analyzer*.py', 'fetcher*.py', 'main*.js', 'market_index*.py'],
    'config_files': ['*.json', '*.bat', 'package.json'],
    'data_files': ['*.db', '*.csv', 'result.json', 'holdings.json'],
    'doc_files': ['*.md', '*.html'],
}

print("="*70)
print("csi10项目临时文件清理")
print("="*70)

BACKUP_DIR.mkdir(parents=True, exist_ok=True)

files_to_cleanup = []
for rule_type, patterns in CLEANUP_RULES.items():
    for pattern in patterns:
        for file in PROJECT_DIR.glob(pattern):
            if file.is_file() and file.name not in ['analyzer_v4.py', 'market_index_fetcher.py']:
                should_keep = any(file.match(p) for ps in KEEP_RULES.values() for p in ps)
                if not should_keep:
                    files_to_cleanup.append((file, rule_type))

print(f"\n发现 {len(files_to_cleanup)} 个临时文件")
print("-"*70)

for file, rule_type in files_to_cleanup:
    print(f"{file.name:40} ({rule_type})")

cleaned = []
total_size = 0

for file, rule_type in files_to_cleanup:
    try:
        backup_path = BACKUP_DIR / file.name
        shutil.copy2(str(file), str(backup_path))
        file_size = file.stat().st_size
        file.unlink()
        cleaned.append(file.name)
        total_size += file_size
        print(f"✓ 清理: {file.name}")
    except Exception as e:
        print(f"✗ 失败: {file.name} - {e}")

print("\n" + "="*70)
print(f"清理完成: {len(cleaned)}个文件, {total_size/1024:.1f}KB")
print(f"备份位置: {BACKUP_DIR}")
print("="*70)

# 记录到memory
memory_file = Path('memory/2026-04-23.md')
if memory_file.exists():
    with open(memory_file, 'a', encoding='utf-8') as f:
        f.write(f"""
---

## csi10文件清理记录 ({datetime.now().strftime('%H:%M')})

**清理统计**:
- 清理文件: {len(cleaned)}个
- 释放空间: {total_size/1024:.1f}KB
- 备份位置: {BACKUP_DIR}

**清理清单**:
{chr(10).join([f'- {f}' for f in cleaned])}

**项目整洁度**: ✓ 清理完成
""")
    print(f"✓ 记录已写入memory")

print("\n临时文件清理完成 ✓")