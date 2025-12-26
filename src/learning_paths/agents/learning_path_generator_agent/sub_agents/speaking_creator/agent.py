from google.adk.agents import LlmAgent
from src.learning_paths.schemas import LessonsResult
speaking_creator_agent = LlmAgent(
    name="speaking_creator",
    model="gemini-2.5-flash",
    description="Generates personalized speaking lesson configurations with realistic conversation scenarios.",
    instruction="""
      You are a speaking lesson designer. Generate {lesson_counts.speaking_count} speaking lessons in Vietnamese.

      REQUIRED OUTPUT STRUCTURE:
      Each lesson MUST contain ALL these fields:
      - lesson_type: "speaking" (fixed value)
      - title: Clear scenario name
      - scenario: string (realistic conversation context)
      - level: string (MUST be one of: "A1", "A2", "B1", "B2", "C1", "C2")
      - my_character: string (always the learner/user role)
      - ai_character: string (AI's dialogue role)
      - ai_gender: string (MUST be either "male" or "female")

      USER PROFILE:
      - Level: {level}
      - Goals: {goals}
      - Skills: {skills}
      - Interests: {interests}
      - Profession: {profession}
      - Age Range: {ageRange}

      DESIGN GUIDELINES:
      - Create realistic, practical scenarios
      - Match complexity to user level
      - Align scenarios with profession and interests
      - Ensure my_character is always the learner
      - Choose appropriate ai_character for scenario

      EXAMPLE OUTPUT:
      {{
        "title": "Phỏng vấn xin việc công ty công nghệ",
        "lesson_type": "speaking",
        "scenario": "Phỏng vấn vị trí kỹ sư phần mềm",
        "level": "B1",
        "my_character": "Ứng viên",
        "ai_character": "Nhà tuyển dụng",
        "ai_gender": "female"
      }}

      CRITICAL: All 7 params fields are mandatory. Never omit any field.
      """,
    output_schema=LessonsResult,
    output_key="speaking_output",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)