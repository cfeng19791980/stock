# -*- coding: utf-8 -*-
"""
csi10 备份回滚系统
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import shutil
from datetime import datetime
import subprocess

CSI10_DIR = r'E:\csi10'
BACKUP_DIR = r'E:\csi10_backups'

print("=" * 60)
print("csi10 备份回滚系统")
print("=" * 60)

def backup_system():
    """创建完整备份"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'csi10_backup_{timestamp}')
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    print(f"\n创建备份: {backup_path}")
    
    # 备份关键文件
    key_files = [
        'stocks.db',
        '波段股票Top30.csv',
        'holdings.json',
        'analyzer_v4.py',
        'analyzer_v5.py',
        'result.json',
    ]
    
    os.makedirs(backup_path, exist_ok=True)
    
    for f in key_files:
        src = os.path.join(CSI10_DIR, f)
        if os.path.exists(src):
            dst = os.path.join(backup_path, f)
            shutil.copy2(src, dst)
            print(f"  ✓ {f}")
    
    # 备份模型缓存
    model_cache = os.path.join(CSI10_DIR, 'model_cache')
    if os.path.exists(model_cache):
        dst_cache = os.path.join(backup_path, 'model_cache')
        shutil.copytree(model_cache, dst_cache)
        print(f"  ✓ model_cache/")
    
    # Git commit
    try:
        subprocess.run(['git', 'add', '.'], cwd=CSI10_DIR, capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'Backup {timestamp}'], cwd=CSI10_DIR, capture_output=True)
        subprocess.run(['git', 'tag', f'backup-{timestamp}'], cwd=CSI10_DIR, capture_output=True)
        print(f"  ✓ Git tag: backup-{timestamp}")
    except:
        print("  ⚠ Git操作失败（非致命）")
    
    # 记录备份信息
    info = {
        'timestamp': timestamp,
        'backup_path': backup_path,
        'files': key_files,
        'model_cached': os.path.exists(model_cache),
    }
    
    with open(os.path.join(backup_path, 'backup_info.json'), 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"\n备份完成!")
    return backup_path

def rollback(backup_tag=None):
    """回滚到指定备份"""
    if backup_tag:
        # Git rollback
        try:
            subprocess.run(['git', 'checkout', backup_tag], cwd=CSI10_DIR, capture_output=True)
            print(f"Git回滚到: {backup_tag}")
        except:
            print("Git回滚失败")
    
    # 查找最新备份
    backups = sorted([d for d in os.listdir(BACKUP_DIR) if d.startswith('csi10_backup_')])
    
    if backups:
        latest = backups[-1]
        backup_path = os.path.join(BACKUP_DIR, latest)
        print(f"\n回滚到: {latest}")
        
        for f in os.listdir(backup_path):
            if f == 'backup_info.json':
                continue
            src = os.path.join(backup_path, f)
            dst = os.path.join(CSI10_DIR, f)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            print(f"  ✓ {f}")
        
        print("回滚完成!")
    else:
        print("无备份可用")

def list_backups():
    """列出所有备份"""
    if not os.path.exists(BACKUP_DIR):
        print("无备份目录")
        return
    
    backups = sorted([d for d in os.listdir(BACKUP_DIR) if d.startswith('csi10_backup_')])
    
    print(f"\n可用备份 ({len(backups)}个):")
    for b in backups:
        info_path = os.path.join(BACKUP_DIR, b, 'backup_info.json')
        if os.path.exists(info_path):
            with open(info_path) as f:
                info = json.load(f)
            print(f"  {b} - {info.get('timestamp', 'N/A')}")
        else:
            print(f"  {b}")

# 主菜单
if len(sys.argv) > 1:
    cmd = sys.argv[1]
    if cmd == 'backup':
        backup_system()
    elif cmd == 'rollback':
        tag = sys.argv[2] if len(sys.argv) > 2 else None
        rollback(tag)
    elif cmd == 'list':
        list_backups()
else:
    print("\n用法:")
    print("  python backup_rollback.py backup   - 创建备份")
    print("  python backup_rollback.py rollback - 回滚到最新备份")
    print("  python backup_rollback.py rollback <tag> - 回滚到指定Git tag")
    print("  python backup_rollback.py list     - 列出所有备份")

print("=" * 60)