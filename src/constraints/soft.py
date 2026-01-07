from collections import defaultdict
from typing import List, Dict, Tuple, Set

from .hard import parse_time_slot, is_assigned

class SoftConstraintRules:
    """
    Stateless logic for calculating soft constraint penalties (Quality of Life metrics).
    Lower scores indicate a better schedule.
    """

    @staticmethod
    def calculate_instructor_gaps(
        instructor_schedule: Dict[str, Dict[str, List]]
    ) -> Tuple[int, Dict[str, Dict[int, int]]]:
        """
        Calculates the total "idle period gaps" for instructors.
        """

        total_penalty = 0
        details = defaultdict(lambda: defaultdict(int))

        for instructor_id, time_slots in instructor_schedule.items():

            daily_periods = defaultdict(list)

            for time_slot in time_slots:
                day, period = parse_time_slot(time_slot)

                if day is not None and period is not None:
                    daily_periods[day].append(period)

            for day, periods in daily_periods.items():
                if len(periods) <= 1:
                    continue

                periods.sort()
                day_gaps = 0

                for i in range(len(periods) - 1):
                    gap = periods[i+1] - periods[i] - 1
                    if gap > 0:
                        day_gaps += gap

                if day_gaps > 0:
                    details[str(instructor_id)][str(day)] = day_gaps
                    total_penalty += day_gaps

        return total_penalty, {k: dict(v) for k, v in details.items()}


    @staticmethod
    def calculate_room_usage(courses: List[Dict]) -> Tuple[int, List[str]]:
        """
        Calculates how many unique rooms are utilized in the schedule.

        """
        used_rooms: Set[str] = set()

        for course in courses:
            room_id = course.get("room_id")

            if is_assigned(room_id):
                used_rooms.add(str(room_id))

        sorted_rooms = sorted(used_rooms, key=lambda x: (len(x), x))

        return len(used_rooms), sorted_rooms