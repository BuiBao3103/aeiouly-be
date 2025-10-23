"""
CEFR (Common European Framework of Reference) Level Definitions
Tối ưu hóa cho AI Agent.
"""

from enum import Enum
from typing import List

class CEFRLevel(str, Enum):
    """CEFR Language Proficiency Levels"""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

class CEFRLevelInfo:
    """Thông tin chi tiết về các cấp độ CEFR"""
    
    # Mô tả tiếng Anh
    DESCRIPTIONS = {
        CEFRLevel.A1: "Breakthrough or beginner",
        CEFRLevel.A2: "Waystage or elementary", 
        CEFRLevel.B1: "Threshold or intermediate",
        CEFRLevel.B2: "Vantage or upper intermediate",
        CEFRLevel.C1: "Effective operational proficiency or advanced",
        CEFRLevel.C2: "Mastery or proficiency"
    }
    
    # Mô tả tiếng Việt (Đã tối ưu cho Agent)
    VIETNAMESE_DESCRIPTIONS = {
        CEFRLevel.A1: "Sơ cấp 1: Hiểu và dùng câu quen thuộc, biểu đạt nhu cầu tức thời. Giao tiếp rất cơ bản, cần đối thoại chậm rãi.",
        CEFRLevel.A2: "Sơ cấp 2: Hiểu thông tin thường dùng về cá nhân, mua sắm. Trao đổi thông tin trực tiếp trong các tình huống đơn giản.",
        CEFRLevel.B1: "Trung cấp 1: Hiểu ý chính về chủ đề quen thuộc (công việc, du lịch). Diễn tả kinh nghiệm, sự kiện một cách đơn giản, mạch lạc.",
        CEFRLevel.B2: "Trung cấp 2: Hiểu ý chính văn bản phức tạp, thảo luận kỹ thuật. Giao tiếp trôi chảy, tự nhiên mà không gây căng thẳng.",
        CEFRLevel.C1: "Cao cấp 1: Hiểu văn bản dài, phức tạp, nhận biết ý nghĩa ngầm. Biểu đạt trôi chảy, linh hoạt cho học thuật và chuyên môn.",
        CEFRLevel.C2: "Cao cấp 2: Dễ dàng hiểu hầu như mọi thứ nghe/đọc. Tóm tắt và tái cấu trúc lập luận. Biểu đạt cực kỳ trôi chảy, chính xác.",
    }
    
    
    # Mức độ phức tạp Ngữ pháp
    GRAMMAR_COMPLEXITY = {
        CEFRLevel.A1: "Cơ bản (Hiện tại, Quá khứ, Tương lai đơn).",
        CEFRLevel.A2: "Đơn giản và tiếp diễn, câu điều kiện cơ bản, so sánh.",
        CEFRLevel.B1: "Thì phức hợp, thể bị động, câu tường thuật, mệnh đề quan hệ cơ bản.",
        CEFRLevel.B2: "Câu điều kiện nâng cao, giả định (subjunctive), cấu trúc phức tạp.",
        CEFRLevel.C1: "Ngữ pháp tinh tế, cấu trúc đảo ngữ, cách diễn đạt mang tính thành ngữ.",
        CEFRLevel.C2: "Ngữ pháp gần như người bản xứ, nắm bắt được các sắc thái tinh tế.",
    }
    
    # Mức độ phức tạp Từ vựng
    VOCABULARY_COMPLEXITY = {
        CEFRLevel.A1: "Từ vựng cơ bản hàng ngày (khoảng 500-1000 từ).",
        CEFRLevel.A2: "Từ vựng thông dụng, một số thành ngữ cơ bản.",
        CEFRLevel.B1: "Từ vựng trung cấp, một số thuật ngữ chuyên ngành cơ bản.",
        CEFRLevel.B2: "Từ vựng nâng cao, thuật ngữ chuyên môn, từ đa nghĩa.",
        CEFRLevel.C1: "Từ vựng phức tạp, ngôn ngữ học thuật, từ đồng nghĩa/trái nghĩa tinh tế.",
        CEFRLevel.C2: "Từ vựng cấp độ bản xứ, phân biệt được sự khác biệt nghĩa nhỏ nhất.",
    }

def get_cefr_levels() -> List[CEFRLevel]:
    """Lấy tất cả các cấp độ CEFR theo thứ tự"""
    return [CEFRLevel.A1, CEFRLevel.A2, CEFRLevel.B1, CEFRLevel.B2, CEFRLevel.C1, CEFRLevel.C2]

def get_level_description(level: CEFRLevel, language: str = "en") -> str:
    """Lấy mô tả cho một cấp độ CEFR (Mặc định: Tiếng Anh)"""
    if language.lower() == "vi":
        return CEFRLevelInfo.VIETNAMESE_DESCRIPTIONS.get(level, "")
    return CEFRLevelInfo.DESCRIPTIONS.get(level, "")

def get_grammar_complexity(level: CEFRLevel) -> str:
    """Lấy mô tả độ phức tạp ngữ pháp cho cấp độ CEFR"""
    return CEFRLevelInfo.GRAMMAR_COMPLEXITY.get(level, "")

def get_vocabulary_complexity(level: CEFRLevel) -> str:
    """Lấy mô tả độ phức tạp từ vựng cho cấp độ CEFR"""
    return CEFRLevelInfo.VOCABULARY_COMPLEXITY.get(level, "")

# Các hàm tiện ích khác (đã giữ lại từ phiên bản trước)
def is_valid_cefr_level(level: str) -> bool:
    """Kiểm tra xem một chuỗi có phải là cấp độ CEFR hợp lệ không"""
    try:
        CEFRLevel(level)
        return True
    except ValueError:
        return False

def get_level_order(level: CEFRLevel) -> int:
    """Lấy thứ tự số của cấp độ CEFR (A1=1, A2=2, ..., C2=6)"""
    order = {
        CEFRLevel.A1: 1, CEFRLevel.A2: 2, CEFRLevel.B1: 3,
        CEFRLevel.B2: 4, CEFRLevel.C1: 5, CEFRLevel.C2: 6
    }
    return order.get(level, 0)

def compare_levels(level1: CEFRLevel, level2: CEFRLevel) -> int:
    """So sánh hai cấp độ CEFR."""
    order1 = get_level_order(level1)
    order2 = get_level_order(level2)
    
    if order1 < order2:
        return -1 # level1 thấp hơn level2
    elif order1 > order2:
        return 1  # level1 cao hơn level2
    else:
        return 0  # bằng nhau

def get_cefr_definitions_string() -> str:
    """Trả về string định nghĩa về thang CEFR với mô tả tiếng Việt, ngữ pháp và từ vựng"""
    definitions = "THANG CEFR (Common European Framework of Reference):\n\n"
    
    for level in CEFRLevel:
        vi_desc = CEFRLevelInfo.VIETNAMESE_DESCRIPTIONS.get(level, "")
        grammar = CEFRLevelInfo.GRAMMAR_COMPLEXITY.get(level, "")
        vocab = CEFRLevelInfo.VOCABULARY_COMPLEXITY.get(level, "")
        
        definitions += f"{level.value}:\n"
        definitions += f"  Mô tả: {vi_desc}\n"
        definitions += f"  Ngữ pháp: {grammar}\n"
        definitions += f"  Từ vựng: {vocab}\n\n"
    
    return definitions