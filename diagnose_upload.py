#!/usr/bin/env python3
"""
診斷腳本：檢查圖片上傳和訪問配置
運行方式：python diagnose_upload.py
"""

import os
import sys

# 添加應用路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config

app = create_app()

with app.app_context():
    print("=" * 60)
    print("圖片上傳配置診斷")
    print("=" * 60)
    
    # 1. 檢查配置
    print("\n1. 配置檢查:")
    upload_folder = app.config["UPLOAD_FOLDER"]
    print(f"   上傳目錄: {upload_folder}")
    print(f"   絕對路徑: {os.path.abspath(upload_folder)}")
    
    # 2. 檢查目錄是否存在
    print("\n2. 目錄檢查:")
    if os.path.exists(upload_folder):
        print(f"   ✓ 目錄存在")
        print(f"   權限: {oct(os.stat(upload_folder).st_mode)[-3:]}")
    else:
        print(f"   ✗ 目錄不存在，嘗試創建...")
        try:
            os.makedirs(upload_folder, exist_ok=True)
            print(f"   ✓ 目錄已創建")
        except Exception as e:
            print(f"   ✗ 無法創建目錄: {e}")
    
    # 3. 檢查目錄是否可寫
    print("\n3. 寫入權限檢查:")
    test_file = os.path.join(upload_folder, ".test_write")
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print(f"   ✓ 目錄可寫")
    except Exception as e:
        print(f"   ✗ 目錄不可寫: {e}")
    
    # 4. 列出現有文件
    print("\n4. 現有文件:")
    if os.path.exists(upload_folder):
        files = [f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))]
        if files:
            print(f"   找到 {len(files)} 個文件:")
            for f in files[:10]:  # 只顯示前10個
                filepath = os.path.join(upload_folder, f)
                size = os.path.getsize(filepath)
                print(f"   - {f} ({size} bytes)")
            if len(files) > 10:
                print(f"   ... 還有 {len(files) - 10} 個文件")
        else:
            print("   目錄為空")
    
    # 5. 檢查路由
    print("\n5. 路由檢查:")
    routes = []
    for rule in app.url_map.iter_rules():
        if 'uploads' in rule.rule:
            routes.append(rule.rule)
    
    if routes:
        print("   找到以下路由:")
        for route in routes:
            print(f"   - {route}")
    else:
        print("   ✗ 未找到 uploads 路由")
    
    # 6. 測試文件路徑
    print("\n6. 測試文件路徑:")
    test_filename = "0019a3a84fac9-c9572c996879.webp"
    test_filepath = os.path.join(upload_folder, test_filename)
    print(f"   測試文件: {test_filename}")
    print(f"   完整路徑: {test_filepath}")
    print(f"   文件存在: {'✓ 是' if os.path.exists(test_filepath) else '✗ 否'}")
    
    print("\n" + "=" * 60)
    print("診斷完成")
    print("=" * 60)

