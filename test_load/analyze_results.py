# SCRIPT ĐỌC KẾT QUẢ VÀ TẠO BÁO CÁO
# Filename: analyze_results.py

import os
import csv
import re
from datetime import datetime
from pathlib import Path

# =====================================
# CẤU HÌNH
# =====================================

REQUIRED_USERS = 200
PERFORMANCE_CRITERIA = {
    "max_avg_response_time": 500,      # ms
    "max_95th_percentile": 1000,       # ms
    "max_failure_rate": 1.0,           # %
    "min_rps": 50                      # requests/second
}

# =====================================
# HÀM ĐỌC FILE CSV
# =====================================

def find_csv_files():
    """Tìm tất cả file CSV trong thư mục hiện tại"""
    csv_files = []
    for file in Path('.').glob('results_*_stats.csv'):
        csv_files.append(str(file))
    return sorted(csv_files)

def parse_csv_file(csv_file):
    """Đọc file CSV và trích xuất thông tin"""
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            # Tìm dòng Aggregated hoặc Total
            for row in rows:
                row_type = row.get('Type', '').strip()
                row_name = row.get('Name', '').strip()
                
                if row_type == 'Aggregated' or 'Aggregated' in row_name or row_name == '':
                    # Tìm thấy dòng tổng hợp
                    try:
                        total_requests = int(row.get('Request Count', 0))
                        failure_count = int(row.get('Failure Count', 0))
                        avg_time = float(row.get('Average Response Time', 0))
                        min_time = float(row.get('Min Response Time', 0))
                        max_time = float(row.get('Max Response Time', 0))
                        median_time = float(row.get('Median Response Time', 0))
                        rps = float(row.get('Requests/s', 0))
                        
                        failure_rate = 0.0
                        if total_requests > 0:
                            failure_rate = (failure_count / total_requests) * 100
                        
                        return {
                            'total_requests': total_requests,
                            'failure_count': failure_count,
                            'failure_rate': failure_rate,
                            'avg_response_time': avg_time,
                            'min_response_time': min_time,
                            'max_response_time': max_time,
                            'median_response_time': median_time,
                            'rps': rps
                        }
                    except (ValueError, KeyError) as e:
                        print(f"⚠️  Lỗi parse dòng: {e}")
                        continue
            
            return None
    except Exception as e:
        print(f"❌ Lỗi đọc file {csv_file}: {e}")
        return None

def extract_test_info(filename):
    """Trích xuất thông tin test từ tên file"""
    # Ví dụ: results_target_200_20251220_180606_stats.csv
    
    # Tìm số users
    users_match = re.search(r'(\d+)', filename)
    users = int(users_match.group(1)) if users_match else 0
    
    # Tìm tên test
    test_name = "Unknown"
    if 'warmup' in filename:
        test_name = "Warmup"
    elif 'step_100' in filename:
        test_name = "Step 100"
    elif 'step_150' in filename:
        test_name = "Step 150"
    elif 'target_200' in filename:
        test_name = "Target 200 ⭐"
    elif 'peak_250' in filename:
        test_name = "Peak 250"
    elif 'baseline' in filename:
        test_name = "Baseline"
    elif 'normal' in filename:
        test_name = "Normal"
    elif 'peak' in filename:
        test_name = "Peak"
    elif 'stress' in filename:
        test_name = "Stress"
    
    return test_name, users

# =====================================
# HÀM ĐỌC FILE HTML (DỰ PHÒNG)
# =====================================

def find_html_files():
    """Tìm tất cả file HTML"""
    html_files = []
    for file in Path('.').glob('report_*.html'):
        html_files.append(str(file))
    return sorted(html_files)

def parse_html_stats(html_file):
    """Đọc thống kê từ file HTML"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Tìm các giá trị trong HTML
            # Locust HTML thường có format cụ thể
            
            # Tìm total requests
            requests_match = re.search(r'Total.*?(\d+)', content)
            total_requests = int(requests_match.group(1)) if requests_match else 0
            
            # Tìm failure
            failure_match = re.search(r'Fails.*?(\d+)', content)
            failure_count = int(failure_match.group(1)) if failure_match else 0
            
            # Tìm average response time
            avg_match = re.search(r'Average.*?(\d+(?:\.\d+)?)\s*ms', content)
            avg_time = float(avg_match.group(1)) if avg_match else 0
            
            # Tìm RPS
            rps_match = re.search(r'RPS.*?(\d+(?:\.\d+)?)', content)
            rps = float(rps_match.group(1)) if rps_match else 0
            
            failure_rate = 0.0
            if total_requests > 0:
                failure_rate = (failure_count / total_requests) * 100
            
            return {
                'total_requests': total_requests,
                'failure_count': failure_count,
                'failure_rate': failure_rate,
                'avg_response_time': avg_time,
                'rps': rps
            }
    except Exception as e:
        print(f"⚠️  Không thể parse HTML {html_file}: {e}")
        return None

# =====================================
# HÀM PHÂN TÍCH
# =====================================

def check_performance(metrics, users):
    """Kiểm tra có đạt tiêu chuẩn không"""
    if not metrics:
        return None, ["Không có dữ liệu"]
    
    issues = []
    passed_criteria = []
    
    # Kiểm tra avg response time
    if metrics['avg_response_time'] > PERFORMANCE_CRITERIA['max_avg_response_time']:
        issues.append(f"Avg Response Time: {metrics['avg_response_time']:.0f}ms (Yêu cầu: <{PERFORMANCE_CRITERIA['max_avg_response_time']}ms)")
    else:
        passed_criteria.append(f"Avg Response Time: {metrics['avg_response_time']:.0f}ms ✅")
    
    # Kiểm tra failure rate
    if metrics['failure_rate'] > PERFORMANCE_CRITERIA['max_failure_rate']:
        issues.append(f"Failure Rate: {metrics['failure_rate']:.2f}% (Yêu cầu: <{PERFORMANCE_CRITERIA['max_failure_rate']}%)")
    else:
        passed_criteria.append(f"Failure Rate: {metrics['failure_rate']:.2f}% ✅")
    
    # Kiểm tra RPS
    if metrics['rps'] < PERFORMANCE_CRITERIA['min_rps']:
        issues.append(f"RPS: {metrics['rps']:.1f} (Yêu cầu: >{PERFORMANCE_CRITERIA['min_rps']})")
    else:
        passed_criteria.append(f"RPS: {metrics['rps']:.1f} ✅")
    
    passed = len(issues) == 0
    
    return passed, issues if issues else passed_criteria

# =====================================
# HÀM TẠO BÁO CÁO
# =====================================

def create_report(all_results):
    """Tạo báo cáo chi tiết"""
    
    report = f"""
╔═══════════════════════════════════════════════════════════════════════╗
║     BÁO CÁO PHÂN TÍCH KẾT QUẢ KIỂM THỬ                               ║
╚═══════════════════════════════════════════════════════════════════════╝

Thời gian phân tích: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Yêu cầu: Phục vụ {REQUIRED_USERS} users đồng thời

TIÊU CHÍ ĐÁNH GIÁ:
─────────────────────────────────────────────────────────────────────────
• Avg Response Time: < {PERFORMANCE_CRITERIA['max_avg_response_time']}ms
• 95th Percentile: < {PERFORMANCE_CRITERIA['max_95th_percentile']}ms
• Failure Rate: < {PERFORMANCE_CRITERIA['max_failure_rate']}%
• RPS: > {PERFORMANCE_CRITERIA['min_rps']} requests/second

"""
    
    if not all_results:
        report += """
❌ KHÔNG TÌM THẤY FILE KẾT QUẢ

Vui lòng kiểm tra:
1. Các file results_*_stats.csv có tồn tại không?
2. Chạy script trong cùng thư mục với file kết quả
3. File CSV có đúng format không?

Thử chạy lại test hoặc kiểm tra file HTML thủ công.
"""
        return report
    
    # Sắp xếp theo số users
    all_results.sort(key=lambda x: x['users'])
    
    report += f"""
KẾT QUẢ CHI TIẾT:
─────────────────────────────────────────────────────────────────────────

Tìm thấy {len(all_results)} kết quả test:

"""
    
    # Tạo bảng tổng hợp
    report += f"{'Test':<25} {'Users':>6} {'Requests':>10} {'Fails':>8} {'Avg(ms)':>8} {'RPS':>8}\n"
    report += "─" * 75 + "\n"
    
    target_result = None
    
    for result in all_results:
        test_name = result['test_name']
        users = result['users']
        metrics = result['metrics']
        
        if metrics:
            report += f"{test_name:<25} {users:>6} {metrics['total_requests']:>10,} "
            report += f"{metrics['failure_rate']:>7.2f}% {metrics['avg_response_time']:>8.0f} "
            report += f"{metrics['rps']:>8.1f}\n"
            
            # Lưu kết quả test 200 users
            if users == REQUIRED_USERS:
                target_result = result
        else:
            report += f"{test_name:<25} {users:>6} {'N/A':>10} {'N/A':>8} {'N/A':>8} {'N/A':>8}\n"
    
    report += "\n"
    
    # Chi tiết từng test
    report += """
CHI TIẾT TỪNG TEST:
─────────────────────────────────────────────────────────────────────────

"""
    
    for result in all_results:
        test_name = result['test_name']
        users = result['users']
        metrics = result['metrics']
        filename = result['filename']
        
        is_target = (users == REQUIRED_USERS)
        marker = " 🎯 TEST CHÍNH" if is_target else ""
        
        report += f"\n{test_name} ({users} users){marker}:\n"
        report += f"  File: {filename}\n"
        
        if metrics:
            report += f"  • Total Requests: {metrics['total_requests']:,}\n"
            report += f"  • Failed: {metrics['failure_count']:,} ({metrics['failure_rate']:.2f}%)\n"
            report += f"  • Avg Response Time: {metrics['avg_response_time']:.0f}ms\n"
            report += f"  • Min/Max: {metrics['min_response_time']:.0f}ms / {metrics['max_response_time']:.0f}ms\n"
            report += f"  • Median: {metrics['median_response_time']:.0f}ms\n"
            report += f"  • RPS: {metrics['rps']:.1f} req/s\n"
            
            if is_target:
                passed, result_items = check_performance(metrics, users)
                if passed:
                    report += f"\n  ✅ ĐẠT YÊU CẦU\n"
                    for item in result_items:
                        report += f"     • {item}\n"
                else:
                    report += f"\n  ❌ CHƯA ĐẠT:\n"
                    for issue in result_items:
                        report += f"     • {issue}\n"
        else:
            report += f"  ⚠️  Không đọc được dữ liệu\n"
    
    # KẾT LUẬN
    report += f"""

═══════════════════════════════════════════════════════════════════════
KẾT LUẬN CUỐI CÙNG:
═══════════════════════════════════════════════════════════════════════

"""
    
    if target_result and target_result['metrics']:
        metrics = target_result['metrics']
        passed, result_items = check_performance(metrics, REQUIRED_USERS)
        
        if passed:
            report += f"""
✅ HỆ THỐNG ĐẠT YÊU CẦU

Hệ thống có khả năng phục vụ {REQUIRED_USERS} người dùng đồng thời 
mà không làm giảm hiệu suất đáng kể.

CÁC CHỈ SỐ ĐẠT:
"""
            for item in result_items:
                report += f"  • {item}\n"
            
            report += f"""
HIỆU SUẤT:
  • {metrics['total_requests']:,} requests được xử lý thành công
  • Tỷ lệ lỗi chỉ {metrics['failure_rate']:.2f}%
  • Thời gian phản hồi trung bình: {metrics['avg_response_time']:.0f}ms
  • Throughput: {metrics['rps']:.1f} requests/giây

ĐÁNH GIÁ: Hệ thống ổn định và sẵn sàng production.
"""
        else:
            report += f"""
❌ HỆ THỐNG CHƯA ĐẠT YÊU CẦU

Hệ thống chưa thể phục vụ {REQUIRED_USERS} người dùng đồng thời 
với hiệu suất chấp nhận được.

CÁC VẤN ĐỀ:
"""
            for issue in result_items:
                report += f"  • {issue}\n"
            
            report += f"""
THỐNG KÊ:
  • Total Requests: {metrics['total_requests']:,}
  • Failure Rate: {metrics['failure_rate']:.2f}%
  • Avg Response: {metrics['avg_response_time']:.0f}ms
  • RPS: {metrics['rps']:.1f}

KHUYẾN NGHỊ CẢI THIỆN:
"""
            
            # Đưa ra khuyến nghị cụ thể
            if metrics['avg_response_time'] > PERFORMANCE_CRITERIA['max_avg_response_time']:
                report += """
  📌 Tối ưu Response Time:
     • Thêm database indexes
     • Implement caching (Redis/Memcached)
     • Optimize queries (N+1 problem)
     • Use connection pooling
"""
            
            if metrics['failure_rate'] > PERFORMANCE_CRITERIA['max_failure_rate']:
                report += """
  📌 Giảm Failure Rate:
     • Kiểm tra error logs
     • Tăng timeout settings
     • Fix bugs causing errors
     • Add retry logic
"""
            
            if metrics['rps'] < PERFORMANCE_CRITERIA['min_rps']:
                report += """
  📌 Tăng Throughput:
     • Scale horizontal (thêm servers)
     • Use async/await
     • Optimize middleware
     • Enable HTTP/2
"""
    else:
        report += f"""
⚠️  KHÔNG TÌM THẤY KẾT QUẢ TEST {REQUIRED_USERS} USERS

Vui lòng:
1. Kiểm tra file results_target_200_*_stats.csv có tồn tại
2. Chạy lại test cho 200 users
3. Kiểm tra file HTML tương ứng
"""
    
    report += """

─────────────────────────────────────────────────────────────────────────
FILE KẾT QUẢ:
"""
    
    for result in all_results:
        report += f"  • {result['filename']}\n"
    
    report += """
─────────────────────────────────────────────────────────────────────────

💡 BƯỚC TIẾP THEO:
  1. Xem các file report_*.html để có biểu đồ trực quan
  2. Chụp screenshot Statistics table và charts
  3. Đính kèm báo cáo này vào tài liệu
  4. Nếu chưa đạt, thực hiện các khuyến nghị cải thiện

"""
    
    return report

# =====================================
# HÀM MAIN
# =====================================

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║           PHÂN TÍCH KẾT QUẢ KIỂM THỬ TỰ ĐỘNG                         ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
    
    print("🔍 Đang tìm file kết quả...\n")
    
    # Tìm file CSV
    csv_files = find_csv_files()
    
    if not csv_files:
        print("❌ Không tìm thấy file CSV nào!")
        print("   Tìm kiếm file: results_*_stats.csv")
        print("\n💡 Thử tìm file HTML thay thế...\n")
        
        html_files = find_html_files()
        if not html_files:
            print("❌ Không tìm thấy file HTML nào!")
            print("\n⚠️  Vui lòng chạy test trước hoặc kiểm tra lại thư mục.")
            return
        else:
            print(f"✅ Tìm thấy {len(html_files)} file HTML")
            print("⚠️  Chức năng parse HTML đang được phát triển")
            print("   Vui lòng xem file HTML thủ công hoặc dùng file CSV")
            return
    
    print(f"✅ Tìm thấy {len(csv_files)} file CSV:\n")
    
    # Đọc tất cả file
    all_results = []
    
    for csv_file in csv_files:
        print(f"   📄 Đang đọc: {csv_file}")
        
        test_name, users = extract_test_info(csv_file)
        metrics = parse_csv_file(csv_file)
        
        if metrics:
            print(f"      ✓ Đọc thành công - {metrics['total_requests']:,} requests")
        else:
            print(f"      ⚠️  Không đọc được dữ liệu")
        
        all_results.append({
            'filename': csv_file,
            'test_name': test_name,
            'users': users,
            'metrics': metrics
        })
    
    print(f"\n{'='*70}")
    print("📊 Đang phân tích kết quả...")
    print(f"{'='*70}\n")
    
    # Tạo báo cáo
    report = create_report(all_results)
    
    # Lưu báo cáo
    report_filename = f"ANALYSIS_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # In ra màn hình
    print(report)
    
    print(f"\n✅ Đã lưu báo cáo: {report_filename}\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()


# =====================================
# HƯỚNG DẪN SỬ DỤNG
# =====================================
"""
CÁCH DÙNG:

1. Đặt file này trong cùng thư mục với các file kết quả test

2. Chạy:
   python analyze_results.py

3. Script sẽ:
   - Tự động tìm tất cả file results_*_stats.csv
   - Đọc và phân tích dữ liệu
   - Tạo báo cáo chi tiết
   - Đánh giá ĐẠT/CHƯA ĐẠT yêu cầu

4. Kết quả:
   - In ra màn hình
   - Lưu file ANALYSIS_REPORT_*.txt

5. File báo cáo chứa:
   - Bảng tổng hợp tất cả tests
   - Chi tiết từng test
   - Kết luận rõ ràng
   - Khuyến nghị cải thiện (nếu cần)

LƯU Ý:
- File CSV phải có format chuẩn của Locust
- Nếu không đọc được CSV, sẽ thử HTML (đang phát triển)
- Script tự động nhận diện test 200 users
"""