"""
Learning Path Service - Updated to work with current database model
"""
import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from src.config import get_sync_database_url
from src.utils.agent_utils import call_agent_with_logging, build_agent_query, get_agent_state
from src.learning_paths.models import LearningPath, DailyLessonPlan, UserLessonProgress
from src.learning_paths.schemas import (
    LearningPathForm, LearningPathResponse, DailyLessonPlanResponse,
    UserLessonProgressResponse, LearningPathGenerationResult,
    LessonWithProgressResponse, LessonParams
)
from src.learning_paths.exceptions import (
    LearningPathNotFoundException, UserLessonProgressNotFoundException,
    LearningPathGenerationException, InvalidLessonIndexException, DailyLessonPlanNotFoundException
)
from src.learning_paths.agents.learning_path_generator_agent.agent import learning_path_generator_agent
from typing import List, Optional
logger = logging.getLogger(__name__)
APP_NAME = "LearningPath"

# Import state key từ aggregator agent
FINAL_LEARNING_PATH_STATE_KEY = "final_learning_path"


class LearningPathService:
    def __init__(self):
        self.session_service = DatabaseSessionService(
            db_url=get_sync_database_url())
        self.learning_path_generator_runner = Runner(
            agent=learning_path_generator_agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )

    async def generate_learning_path(
        self,
        user_id: int,
        form_data: LearningPathForm,
        db: AsyncSession
    ) -> LearningPathResponse:
        try:
            # 1. Khởi tạo
            duration_map = {"7_days": 7, "30_days": 30, "90_days": 90}
            days = duration_map.get(form_data.planDuration, 7)

            db_lp = LearningPath(
                user_id=user_id,
                form_data=form_data.model_dump(),
                status="generating"
            )
            total_lessons = form_data.dailyLessonCount * days
            db.add(db_lp)
            await db.flush()

            # 2. Chạy Agent Pipeline
            await self.session_service.create_session(
                app_name=APP_NAME,
                user_id=str(user_id),
                session_id=str(db_lp.id),
                state={
                    "learning_path_id": db_lp.id,
                    "days": days,
                    "dailyLessonCount": form_data.dailyLessonCount,
                    "total_lessons": total_lessons,
                    "level": form_data.level.value,
                    "skills": form_data.skills,
                    "interests": form_data.interests,
                    "profession": form_data.profession,
                    "ageRange": form_data.ageRange,
                    "goals": [g.value for g in form_data.goals],
                }
            )

            await call_agent_with_logging(
                runner=self.learning_path_generator_runner,
                user_id=str(user_id),
                session_id=str(db_lp.id),
                query=build_agent_query("system", "Generate path"),
                logger=logger
            )

            # 3. Lấy kết quả đã được callback xử lý
            final_state = await get_agent_state(
                self.session_service,
                APP_NAME,
                str(user_id),
                str(db_lp.id)
            )

            gen_dict = final_state.get(FINAL_LEARNING_PATH_STATE_KEY)

            if not gen_dict:
                generation_error = final_state.get("generation_error")
                if generation_error:
                    raise LearningPathGenerationException(
                        f"Failed to generate learning path: {generation_error}"
                    )
                else:
                    raise LearningPathGenerationException(
                        "Aggregator callback failed to produce final learning path. "
                        "Check logs for details."
                    )

            content = LearningPathGenerationResult.model_validate(gen_dict)

            actual_days = len(content.daily_plans)
            total_lessons_created = sum(len(d.lessons)
                                        for d in content.daily_plans)

            logger.info(
                f"Generated {actual_days} days with {total_lessons_created} total lessons "
                f"(requested: {days} days with {total_lessons} lessons)"
            )

            generation_warning = final_state.get("generation_warning")
            if generation_warning:
                logger.warning(
                    f"Generation adjustments made: {generation_warning}")

            if not content.daily_plans:
                raise LearningPathGenerationException(
                    "No daily plans could be generated. "
                    "Agents may have failed to create lessons."
                )

            for day_data in content.daily_plans:
                db_plan = DailyLessonPlan(
                    learning_path_id=db_lp.id,
                    day_number=day_data.day_number,
                    status="pending"
                )
                db.add(db_plan)
                await db.flush()

                for idx, lesson_params in enumerate(day_data.lessons):
                    db.add(UserLessonProgress(
                        user_id=user_id,
                        daily_lesson_plan_id=db_plan.id,
                        lesson_index=idx,
                        title=lesson_params.title,
                        lesson_type=lesson_params.lesson_type,
                        status="start",
                        metadata_=lesson_params.model_dump()
                    ))

            db_lp.status = "generated"
            await db.commit()
            await db.refresh(db_lp)

            logger.info(
                f"Successfully saved learning path {db_lp.id} for user {user_id}")

            daily_plans = await self.get_daily_lesson_plans(db_lp.id, user_id, db)
            
            lp_data = {
                "id": db_lp.id,
                "user_id": db_lp.user_id,
                "form_data": db_lp.form_data,
                "status": db_lp.status,
                "created_at": db_lp.created_at,
                "warning": generation_warning,
                "daily_plans": daily_plans
            }

            return LearningPathResponse.model_validate(lp_data)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error generating learning path: {e}", exc_info=True)
            raise LearningPathGenerationException(str(e))

    async def start_lesson(
        self, 
        progress_id: int,
        user_id: int, 
        db: AsyncSession, 
        session_id: Optional[int] = None
    ) -> UserLessonProgressResponse:
        """Bắt đầu bài học dựa trên ID tiến độ của người dùng"""
        # 1. Tìm bản ghi tiến độ
        res = await db.execute(
            select(UserLessonProgress).where(
                UserLessonProgress.id == progress_id,
                UserLessonProgress.user_id == user_id
            )
        )
        db_p = res.scalar_one_or_none()
        
        if not db_p:
            raise UserLessonProgressNotFoundException()

        # 2. Cập nhật trạng thái và session_id
        db_p.status = "in_progress"
        if session_id:
            db_p.session_id = session_id
        
        await db.commit()

        # 3. Cập nhật trạng thái DailyPlan liên quan nếu nó vẫn là 'pending'
        plan_res = await db.execute(
            select(DailyLessonPlan).where(DailyLessonPlan.id == db_p.daily_lesson_plan_id)
        )
        db_plan = plan_res.scalar_one_or_none()
        if db_plan and db_plan.status == "pending":
            db_plan.status = "in_progress"
            await db.commit()

        await db.refresh(db_p)
        return UserLessonProgressResponse.model_validate(db_p)


    async def complete_lesson(self, progress_id: int, user_id: int, db: AsyncSession) -> UserLessonProgressResponse:
        res = await db.execute(select(UserLessonProgress).where(
            UserLessonProgress.id == progress_id, UserLessonProgress.user_id == user_id
        ))
        db_p = res.scalar_one_or_none()
        if not db_p: raise UserLessonProgressNotFoundException()

        db_p.status = "done"
        await db.commit()

        # Kiểm tra hoàn thành ngày
        all_res = await db.execute(select(UserLessonProgress).where(
            UserLessonProgress.daily_lesson_plan_id == db_p.daily_lesson_plan_id,
            UserLessonProgress.user_id == user_id
        ))
        if all(p.status == "done" for p in all_res.scalars().all()):
            await db.execute(
                update(DailyLessonPlan).where(DailyLessonPlan.id == db_p.daily_lesson_plan_id)
                .values(status="completed")
            )
            await db.commit()

        await db.refresh(db_p)
        return UserLessonProgressResponse.model_validate(db_p)


    async def get_daily_lesson_plans(
        self,
        learning_path_id: int,
        user_id: int,
        db: AsyncSession
    ) -> List[DailyLessonPlanResponse]:
        """
        Lấy danh sách các ngày học kèm theo tiến độ chi tiết của từng bài học.
        """
        # 1. Lấy tất cả các ngày trong lộ trình
        result = await db.execute(
            select(DailyLessonPlan).where(
                DailyLessonPlan.learning_path_id == learning_path_id
            ).order_by(DailyLessonPlan.day_number)
        )
        plans = result.scalars().all()

        response = []
        for p in plans:
            # 2. Lấy tất cả tiến độ (UserLessonProgress) của user cho ngày này
            progress_res = await db.execute(
                select(UserLessonProgress).where(
                    UserLessonProgress.daily_lesson_plan_id == p.id,
                    UserLessonProgress.user_id == user_id
                ).order_by(UserLessonProgress.lesson_index)
            )
            progress_list = progress_res.scalars().all()

            lessons = []
            for prog in progress_list:
                # 3. Parse LessonParams từ metadata lưu trong DB
                lesson_params = LessonParams.model_validate(prog.metadata_)
                
                lessons.append(LessonWithProgressResponse(
                    id=prog.id,
                    lesson_index=prog.lesson_index,
                    config=lesson_params,
                    title=prog.title,  # Tiêu đề bài học lưu trong bảng UserLessonProgress
                    status=prog.status,
                    session_id=prog.session_id
                ))

            # 4. Tạo response cho từng ngày (lưu ý: schema DailyLessonPlanResponse không còn trường title)
            response.append(DailyLessonPlanResponse(
                id=p.id,
                day_number=p.day_number,
                status=p.status,
                lessons=lessons
            ))
        return response

    async def get_current_learning_path(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Optional[LearningPathResponse]:
        """
        Lấy lộ trình học tập mới nhất của người dùng kèm theo toàn bộ kế hoạch bài học.
        Giải quyết lỗi MissingGreenlet bằng cách fetch dữ liệu trước khi validate.
        """
        # 1. Tìm LearningPath mới nhất của user
        result = await db.execute(
            select(LearningPath)
            .where(LearningPath.user_id == user_id)
            .order_by(LearningPath.created_at.desc())
            .limit(1)
        )
        lp = result.scalar_one_or_none()
        
        if not lp:
            return None

        # 2. Lấy toàn bộ daily plans thông qua hàm helper vừa viết ở trên
        daily_plans_data = await self.get_daily_lesson_plans(lp.id, user_id, db)

        # 3. Đóng gói dữ liệu vào dict để Pydantic không gọi lazy load vào model
        lp_data = {
            "id": lp.id,
            "user_id": lp.user_id,
            "form_data": lp.form_data,
            "status": lp.status,
            "created_at": lp.created_at,
            "warning": getattr(lp, "warning", None),
            "daily_plans": daily_plans_data 
        }
        
        return LearningPathResponse.model_validate(lp_data)
