from google.adk.agents import LlmAgent
from src.learning_paths.schemas import LessonsResult
writing_creator_agent = LlmAgent(
    name="writing_creator",
    model="gemini-2.5-flash",
    description="Generates personalized writing lesson configurations focusing on practical writing skills.",
    instruction="""
      You are a writing lesson designer. Generate {lesson_counts.writing_count} writing lessons in Vietnamese.

      REQUIRED OUTPUT STRUCTURE:
      Each lesson MUST contain ALL these fields:
      - params: Object with ALL 5 REQUIRED fields:
        - lesson_type: "writing" (fixed value)
        - title: Clear, engaging title
        - topic: string (writing topic/task)
        - level: string (MUST be one of: "A1", "A2", "B1", "B2", "C1", "C2")
        - total_sentences: integer (range: 3-15)

      USER PROFILE:
      - Level: {level}
      - Goals: {goals}
      - Skills: {skills}
      - Interests: {interests}
      - Profession: {profession}
      - Age Range: {ageRange}

      DESIGN GUIDELINES:
      - Match task complexity to user level
      - Align topics with interests and profession
      - Adjust sentence count by level (A1: 3-5, B1: 5-10, C1: 10-15)
      - Provide clear, actionable instructions

      EXAMPLE OUTPUT:
      {{
        "lesson_type": "writing",
        "title": "Viết email xin việc chuyên nghiệp",
        "topic": "Email xin việc vị trí kỹ sư phần mềm",
        "level": "B2",
        "total_sentences": 7
      }}

      CRITICAL: All 5 params fields are mandatory. Never omit any field.
      """,
    output_schema=LessonsResult,
    output_key="writing_output",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)