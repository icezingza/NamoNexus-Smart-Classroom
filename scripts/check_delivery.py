import os
import json
from pathlib import Path

def report_status():
    print('\n📊 --- สรุปสถานะการส่งงานของ นะโม 2 (เล่ม 23-45) ---')
    print(f'{"เล่มที่":<10} | {"สถานะ":<15} | {"จำนวนรายการ":<15} | {"แหล่งไฟล์"}')
    print('-'*85)
    
    for b in range(23, 46):
        file_found = False
        # นะโม 2 ย้ายข้อมูลมาที่ global_library หมดแล้ว แต่ยังเช็คเผื่อไว้ตามสูตรนะโม 1
        for folder in ['global_library', 'new_zone']:
            dir_path = Path('knowledge') / folder
            if not dir_path.exists(): continue
            
            for p in dir_path.glob(f'book_{b}*.json'):
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        count = len(data) if isinstance(data, list) else 1
                        
                        if count >= 50:
                            status = '✅ ส่งแล้ว'
                        elif count > 0:
                            status = '⚠️ ข้อมูลน้อย'
                        else:
                            status = '❌ ไฟล์ว่าง'
                            
                        print(f'{b:<10} | {status:<15} | {count:<15} | {folder}/{p.name}')
                        file_found = True
                        break
                except Exception as e:
                    pass
            if file_found: break
            
        if not file_found:
            print(f'{b:<10} | {"❌ ยังไม่ส่ง":<15} | {"0":<15} | -')

if __name__ == "__main__":
    report_status()
