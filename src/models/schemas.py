from typing import List, Optional
from pydantic import BaseModel, Field

# 1. The fundamental unit: A single course assignment
class ScheduleAssignment(BaseModel):
    course_id: str = Field(description="The unique identifier of the course (e.g., '502045-1-0')")
    time_slot: str = Field(description="The assigned day (Mon to Sat) and period (1 to 4) (e.g., '2-1', '2-4'). Use '<>' if unscheduled.")
    room_id: str = Field(description="The assigned room identifier (e.g., 'A508'). Use '<>' if unscheduled.")

# 2. For the Generator (which returns a list of courses)
class ScheduleBatchOutput(BaseModel):
    schedules: List[ScheduleAssignment]