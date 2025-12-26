from google.adk.agents import LlmAgent
from src.learning_paths.schemas import LessonsResult

reading_creator_agent = LlmAgent(
    name="reading_creator",
    model="gemini-2.5-flash",
    description="Generates personalized reading lesson configurations based on user profile and learning objectives.",
    instruction="""
      You are a reading lesson designer. Generate {lesson_counts.reading_count} reading lessons in Vietnamese.

      REQUIRED OUTPUT STRUCTURE:
      Each lesson MUST contain ALL these fields:
      - lesson_type: "reading" (fixed value)
      - title: Engaging, concise title
      - topic: string (lesson topic)
      - level: string (MUST be one of: "A1", "A2", "B1", "B2", "C1", "C2")
      - genre: string (MUST be one of: "Bài báo", "Email/Thư từ", "Truyện ngắn", "Hội thoại", "Bài luận", "Đánh giá sản phẩm", "Bài mạng xã hội", "Hướng dẫn sử dụng")
      - word_count: integer (range: 100-1000)

      USER PROFILE:
      - Level: {level}
      - Goals: {goals}
      - Skills: {skills}
      - Interests: {interests}
      - Profession: {profession}
      - Age Range: {ageRange}

      DESIGN GUIDELINES:
      - Match content difficulty to user level
      - Align topics with interests and profession
      - Choose appropriate genres for learning goals
      - Vary word counts based on level (A1: 100-200, B1: 250-500, C1: 600-1000)

      EXAMPLE OUTPUT:
      {{
        "lesson_type": "reading",
        "title": "Xu hướng công nghệ AI năm 2024",
        "topic": "Công nghệ AI",
        "level": "B1",
        "genre": "Bài báo",
        "word_count": 350
      }}

      CRITICAL: All 6 params fields are mandatory. Never omit any field.
      """,
    output_schema=LessonsResult,
    output_key="reading_output",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)