# FILE KIỂM THỬ INTERACTIVE - TÙY CHỈNH KỊCH BẢN
# Filename: run_custom_test.py

import subprocess
import time
import os
from datetime import datetime

# =====================================
# DANH SÁCH KỊCH BẢN CÓ SẴN
# =====================================

AVAILABLE_SCENARIOS = {
    "1": {
        "name": "quick_test",
        "users": 20,
        "spawn_rate": 5,
        "duration": "1m",
        "description": "⚡ Test nhanh - 20 users, 1 phút"
    },
    "2": {
        "name": "warmup",
        "users": 50,
        "spawn_rate": 10,
        "duration": "3m",
        "description": "🔥 Khởi động - 50 users, 3 phút"
    },
    "3": {
        "name": "normal_load",
        "users": 100,
        "spawn_rate": 20,
        "duration": "5m",
        "description": "📊 Tải bình thường - 100 users, 5 phút"
    },
    "4": {
        "name": "target_200",
        "users": 200,
        "spawn_rate": 40,
        "duration": "10m",
        "description": "🎯 MỤC TIÊU - 200 users, 10 phút (TEST CHÍNH)"
    },
    "5": {
        "name": "peak_load",
        "users": 250,
        "spawn_rate": 50,
        "duration": "5m",
        "description": "🔴 Tải cao điểm - 250 users, 5 phút"
    },
    "6": {
        "name": "stress_test",
        "users": 500,
        "spawn_rate": 100,
        "duration": "10m",
        "description": "💥 Stress test - 500 users, 10 phút"
    },
    "7": {
        "name": "endurance",
        "users": 100,
        "spawn_rate": 20,
        "duration": "30m",
        "description": "⏰ Endurance - 100 users, 30 phút"
    },
    "custom": {
        "name": "custom",
        "users": 0,
        "spawn_rate": 0,
        "duration": "0m",
        "description": "✏️  Tùy chỉnh - Tự nhập tham số"
    }
}

# =====================================
# CẤU HÌNH
# =====================================

REQUIRED_CONCURRENT_USERS = 200
PERFORMANCE_CRITERIA = {
    "max_avg_response_time": 500,
    "max_95th_percentile": 1000,
    "max_failure_rate": 1.0,
    "min_rps": 50
}

# =====================================
# HÀM HIỂN THỊ MENU
# =====================================

def display_menu():
    """Hiển thị menu chọn kịch bản"""
    print("\n" + "="*70)
    print("📋 CHỌN KỊCH BẢN KIỂM THỬ")
    print("="*70)
    
    for key, scenario in AVAILABLE_SCENARIOS.items():
        if key == "custom":
            print(f"\n{key}. {scenario['description']}")
        else:
            print(f"{key}. {scenario['description']}")
            print(f"   → {scenario['users']} users | {scenario['spawn_rate']} users/s | {scenario['duration']}")
    
    print("\n0. ❌ Thoát")
    print("="*70)

def get_user_choice():
    """Lấy lựa chọn từ user"""
    while True:
        choice = input("\n👉 Chọn kịch bản (0-7, hoặc nhiều: 1,2,4): ").strip()
        
        if choice == "0":
            return None
        
        # Cho phép chọn nhiều: "1,2,4" hoặc "1 2 4"
        if "," in choice:
            choices = [c.strip() for c in choice.split(",")]
        else:
            choices = choice.split()
        
        # Validate
        valid_choices = []
        for c in choices:
            if c in AVAILABLE_SCENARIOS:
                valid_choices.append(c)
            else:
                print(f"⚠️  '{c}' không hợp lệ. Vui lòng chọn 0-7 hoặc 'custom'")
                return get_user_choice()
        
        return valid_choices

def get_custom_scenario():
    """Lấy tham số tùy chỉnh"""
    print("\n" + "="*70)
    print("✏️  TÙY CHỈNH KỊCH BẢN")
    print("="*70)
    
    try:
        users = int(input("👥 Số users đồng thời (ví dụ: 100): "))
        spawn_rate = int(input("📈 Spawn rate - users/giây (ví dụ: 20): "))
        duration = input("⏱️  Thời gian (ví dụ: 5m hoặc 300s): ").strip()
        test_name = input("📝 Tên test (ví dụ: my_test): ").strip() or "custom"
        
        return {
            "name": test_name,
            "users": users,
            "spawn_rate": spawn_rate,
            "duration": duration,
            "description": f"Tùy chỉnh - {users} users, {duration}"
        }
    except ValueError:
        print("❌ Giá trị không hợp lệ! Thử lại.")
        return get_custom_scenario()

def get_endpoint():
    """Lấy endpoint cần test"""
    print("\n" + "="*70)
    print("🔗 ENDPOINT CẦN TEST")
    print("="*70)
    
    print("\nNhập endpoint của bạn:")
    print("Ví dụ: /api/v1/background-videos/")
    print("       /api/v1/users/")
    print("       /api/v1/products/")
    
    endpoint = input("\n👉 Endpoint: ").strip()
    
    if not endpoint:
        endpoint = "/api/v1/background-video-types/"
        print(f"   → Dùng mặc định: {endpoint}")
    
    return endpoint

def get_host():
    """Lấy host"""
    print("\n" + "="*70)
    print("🌐 CHỌN HOST")
    print("="*70)
    
    print("\n1. http://localhost:8000 (Local)")
    print("2. https://api.aeiouly.online (Production)")
    print("3. Tùy chỉnh")
    
    choice = input("\n👉 Chọn (1-3): ").strip()
    
    if choice == "1":
        return "http://localhost:8000"
    elif choice == "2":
        return "https://api.aeiouly.online"
    elif choice == "3":
        custom_host = input("👉 Nhập host: ").strip()
        return custom_host if custom_host else "http://localhost:8000"
    else:
        return "http://localhost:8000"

# =====================================
# LOCUST FILE GENERATOR
# =====================================

def create_locustfile(endpoint):
    """Tạo file locustfile.py với endpoint tùy chỉnh"""
    locustfile_content = f"""
from locust import HttpUser, task, between
import random

class LoadTest(HttpUser):
    wait_time = between(1, 2)
    
    @task
    def get_endpoint(self):
        page = random.randint(1, 10)
        size = random.choice([10, 20, 50])
        
        self.client.get(
            "{endpoint}",
            params={{"page": page, "size": size}},
            headers={{"accept": "application/json"}}
        )
"""
    
    with open("locustfile.py", "w", encoding="utf-8") as f:
        f.write(locustfile_content)
    
    print(f"\n✅ Đã tạo locustfile.py với endpoint: {endpoint}")

# =====================================
# HÀM PHÂN TÍCH
# =====================================

def parse_csv_results(csv_prefix):
    """Đọc file CSV và trích xuất metrics"""
    try:
        import csv
        stats_file = f"{csv_prefix}_stats.csv"
        
        if not os.path.exists(stats_file):
            return None
        
        with open(stats_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Type'] == 'Aggregated' or 'Total' in row.get('Name', ''):
                    return {
                        'total_requests': int(row.get('Request Count', 0)),
                        'failure_count': int(row.get('Failure Count', 0)),
                        'avg_response_time': float(row.get('Average Response Time', 0)),
                        'min_response_time': float(row.get('Min Response Time', 0)),
                        'max_response_time': float(row.get('Max Response Time', 0)),
                        'requests_per_sec': float(row.get('Requests/s', 0)),
                        'failure_rate': (int(row.get('Failure Count', 0)) / 
                                       max(int(row.get('Request Count', 1)), 1) * 100)
                    }
        return None
    except Exception as e:
        print(f"⚠️  Không thể đọc CSV: {e}")
        return None

def check_performance(metrics, users):
    """Kiểm tra performance"""
    if not metrics:
        return False, ["Không có dữ liệu"]
    
    issues = []
    passed_criteria = []
    
    if metrics['avg_response_time'] > PERFORMANCE_CRITERIA['max_avg_response_time']:
        issues.append(f"Avg Response Time: {metrics['avg_response_time']:.0f}ms (Yêu cầu: <{PERFORMANCE_CRITERIA['max_avg_response_time']}ms)")
    else:
        passed_criteria.append(f"Avg Response Time: {metrics['avg_response_time']:.0f}ms ✅")
    
    if metrics['failure_rate'] > PERFORMANCE_CRITERIA['max_failure_rate']:
        issues.append(f"Failure Rate: {metrics['failure_rate']:.2f}% (Yêu cầu: <{PERFORMANCE_CRITERIA['max_failure_rate']}%)")
    else:
        passed_criteria.append(f"Failure Rate: {metrics['failure_rate']:.2f}% ✅")
    
    if metrics['rps'] < PERFORMANCE_CRITERIA['min_rps']:
        issues.append(f"RPS: {metrics['requests_per_sec']:.1f} (Yêu cầu: >{PERFORMANCE_CRITERIA['min_rps']})")
    else:
        passed_criteria.append(f"RPS: {metrics['requests_per_sec']:.1f} ✅")
    
    passed = len(issues) == 0
    return passed, issues if issues else passed_criteria

# =====================================
# CHẠY TEST
# =====================================

def run_test(scenario, host):
    """Chạy 1 test scenario"""
    name = scenario["name"]
    users = scenario["users"]
    spawn_rate = scenario["spawn_rate"]
    duration = scenario["duration"]
    description = scenario["description"]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report = f"report_{name}_{timestamp}.html"
    csv_prefix = f"results_{name}_{timestamp}"
    
    print("\n" + "="*70)
    print(f"🚀 {description}")
    print(f"   👥 Users: {users} | 📈 Spawn: {spawn_rate}/s | ⏱️  Duration: {duration}")
    print(f"   🌐 Host: {host}")
    print("="*70 + "\n")
    
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", host,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", duration,
        "--html", html_report,
        "--csv", csv_prefix,
        "--headless"
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode == 0:
            print(f"\n✅ Test '{name}' hoàn thành!")
            
            time.sleep(2)
            metrics = parse_csv_results(csv_prefix)
            
            if metrics:
                print(f"\n📊 KẾT QUẢ:")
                print(f"   • Total Requests: {metrics['total_requests']:,}")
                print(f"   • Failed: {metrics['failure_count']} ({metrics['failure_rate']:.2f}%)")
                print(f"   • Avg Response: {metrics['avg_response_time']:.0f}ms")
                print(f"   • Min/Max: {metrics['min_response_time']:.0f}ms / {metrics['max_response_time']:.0f}ms")
                print(f"   • RPS: {metrics['requests_per_sec']:.1f} req/s")
                
                if users == REQUIRED_CONCURRENT_USERS:
                    passed, result = check_performance(metrics, users)
                    print(f"\n{'='*70}")
                    if passed:
                        print(f"✅ ĐẠT YÊU CẦU {REQUIRED_CONCURRENT_USERS} USERS!")
                        for item in result:
                            print(f"   • {item}")
                    else:
                        print(f"❌ CHƯA ĐẠT YÊU CẦU:")
                        for issue in result:
                            print(f"   • {issue}")
                    print("="*70)
            
            print(f"\n   📄 HTML: {html_report}")
            print(f"   📊 CSV: {csv_prefix}_*.csv")
            
            return True, metrics
        else:
            print(f"\n❌ Test thất bại!")
            return False, None
            
    except FileNotFoundError:
        print("\n❌ Chưa cài Locust! Chạy: pip install locust")
        return False, None
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        return False, None

def check_server(host):
    """Kiểm tra server"""
    print(f"\n🔍 Kiểm tra server tại {host}...")
    try:
        import requests
        response = requests.get(host, timeout=5)
        print(f"✅ Server đang chạy (Status: {response.status_code})")
        return True
    except Exception as e:
        print(f"❌ Không kết nối được!")
        print(f"   Lỗi: {e}")
        return False

# =====================================
# MAIN
# =====================================

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║           LOAD TESTING TOOL - INTERACTIVE MODE                        ║
║                                                                       ║
║           Chọn kịch bản và tùy chỉnh test theo ý muốn                ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
    
    # Lấy cấu hình
    host = get_host()
    endpoint = get_endpoint()
    
    # Kiểm tra server
    if not check_server(host):
        proceed = input("\n⚠️  Server không phản hồi. Vẫn tiếp tục? (y/n): ")
        if proceed.lower() != 'y':
            print("\n👋 Thoát chương trình.")
            return
    
    # Tạo locustfile
    create_locustfile(endpoint)
    
    # Chọn kịch bản
    all_results = []
    
    while True:
        display_menu()
        choices = get_user_choice()
        
        if choices is None:
            print("\n👋 Thoát chương trình.")
            break
        
        # Xử lý từng lựa chọn
        selected_scenarios = []
        
        for choice in choices:
            if choice == "custom":
                scenario = get_custom_scenario()
                selected_scenarios.append(scenario)
            else:
                selected_scenarios.append(AVAILABLE_SCENARIOS[choice])
        
        # Xác nhận
        print("\n" + "="*70)
        print("📋 CÁC TEST SẼ CHẠY:")
        print("="*70)
        
        total_time = 0
        for i, s in enumerate(selected_scenarios, 1):
            print(f"{i}. {s['description']}")
            
            # Ước tính thời gian
            duration_str = s['duration']
            if 'm' in duration_str:
                total_time += int(duration_str.replace('m', ''))
            elif 's' in duration_str:
                total_time += int(duration_str.replace('s', '')) / 60
        
        print(f"\n⏰ Ước tính thời gian: ~{int(total_time)} phút")
        
        confirm = input("\n👉 Bắt đầu test? (y/n): ")
        if confirm.lower() != 'y':
            continue
        
        # Chạy tests
        for i, scenario in enumerate(selected_scenarios, 1):
            print(f"\n{'#'*70}")
            print(f"# TEST {i}/{len(selected_scenarios)}")
            print(f"{'#'*70}")
            
            success, metrics = run_test(scenario, host)
            all_results.append((scenario, metrics))
            
            if not success:
                retry = input("\n⚠️  Test thất bại. Tiếp tục? (y/n): ")
                if retry.lower() != 'y':
                    break
            
            # Nghỉ giữa các test
            if i < len(selected_scenarios):
                wait = 10
                print(f"\n⏸️  Nghỉ {wait}s...")
                time.sleep(wait)
        
        # Hỏi có muốn chạy test khác không
        print("\n" + "="*70)
        print("✅ HOÀN THÀNH CÁC TEST ĐÃ CHỌN!")
        print("="*70)
        
        continue_testing = input("\n👉 Chạy thêm test khác? (y/n): ")
        if continue_testing.lower() != 'y':
            break
    

    print("\n👋 Cảm ơn đã sử dụng Load Testing Tool!\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Đã dừng chương trình!")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()


# =====================================
# HƯỚNG DẪN SỬ DỤNG
# =====================================
"""
CÁCH DÙNG:

1. Cài đặt:
   pip install locust requests

2. Chạy:
   python run_custom_test.py

3. Làm theo hướng dẫn trên màn hình:
   - Chọn host (local/production/custom)
   - Nhập endpoint cần test
   - Chọn 1 hoặc nhiều kịch bản test
   - Hoặc tùy chỉnh tham số riêng

4. Xem kết quả:
   - Màn hình hiển thị kết quả real-time
   - File HTML và CSV tự động tạo

TÍNH NĂNG:
✅ Chọn nhiều test cùng lúc: 1,2,4
✅ Tùy chỉnh hoàn toàn: users, spawn rate, duration
✅ Đổi endpoint và host dễ dàng
✅ Xem kết quả ngay sau mỗi test
✅ So sánh với yêu cầu 200 users tự động

VÍ DỤ:
- Test nhanh: Chọn 1
- Test đầy đủ: Chọn 2,3,4,5
- Test tùy chỉnh: Chọn custom
- Test một lần: Chọn 4 (test 200 users)
"""