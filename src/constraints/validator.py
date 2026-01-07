from collections import defaultdict
from typing import List, Dict, Tuple, Set
from .hard import HardConstraintRules
from .soft import SoftConstraintRules

class ScheduleValidator:
    def __init__(self, instructors: List[Dict], courses: List[Dict], rooms: List[Dict], curriculum: Dict):
        """
        Initialize with static data once.
        """
        self.instructor_map = {str(i['instructor_id']): i for i in instructors}
        self.course_map = {str(c['course_id']): c for c in courses}
        self.room_map = {str(r['room_id']): r for r in rooms}
        
        self.course_to_semester_map = {}
        if curriculum:
            for sem, course_list in curriculum.items():
                for c in course_list:
                    self.course_to_semester_map[str(c['course_id'])] = sem

    def validate_hard_constraints(self, schedule: List[Dict]) -> Tuple[Set[str], Dict[str, List[str]]]:
        """
        Runs all hard constraint checks.
        Returns: (Set of violating course IDs, Dict of violations per course)
        """
        valid_courses = [
            c for c in schedule 
            if c.get('time_slot') not in [None, "<>"] and c.get('room_id') not in [None, "<>"]
        ]
        
        sched_by_ts = defaultdict(list)
        inst_sched = defaultdict(lambda: defaultdict(list))
        room_sched = defaultdict(lambda: defaultdict(list))

        for c in valid_courses:
            ts = c['time_slot']
            inst = c['assigned_instructor']
            rid = c['room_id']
            
            sched_by_ts[ts].append(c)
            inst_sched[inst][ts].append(c)
            room_sched[rid][ts].append(c)

        # 2. Run Checks
        violating_ids = set()
        details = defaultdict(list)

        HardConstraintRules.check_instructor_conflict(inst_sched, violating_ids, details)
        HardConstraintRules.check_room_conflict(room_sched, violating_ids, details)
        HardConstraintRules.check_room_capacity(valid_courses, self.room_map, self.course_map, violating_ids, details)
        HardConstraintRules.check_room_type(valid_courses, self.room_map, self.course_map, violating_ids, details)
        HardConstraintRules.check_availabilities(valid_courses, self.instructor_map, 'assigned_instructor', 'Instructor Availability', violating_ids, details)
        HardConstraintRules.check_availabilities(valid_courses, self.room_map, 'room_id', 'Room Availability', violating_ids, details)
        HardConstraintRules.check_instructor_load(inst_sched, self.instructor_map, violating_ids, details)
        HardConstraintRules.check_intra_semester(sched_by_ts, self.course_to_semester_map, violating_ids, details)

        return violating_ids, details

    def validate_soft_constraints(self, schedule: List[Dict]) -> Dict:
        """
        Runs soft constraint checks.
        Returns a dictionary containing scores and details.
        """
        valid_courses = [c for c in schedule if c.get('time_slot') not in [None, "<>"]]
        
        inst_sched = defaultdict(list)
        for c in valid_courses:
            inst_sched[c['assigned_instructor']].append(c['time_slot'])

        gap_penalty, gap_details = SoftConstraintRules.calculate_instructor_gaps(inst_sched)
        room_penalty, _ = SoftConstraintRules.calculate_room_usage(valid_courses)

        # Weights could be moved to config later
        W_GAP = 1.0
        W_ROOM = 1.0
        
        total_score = (gap_penalty * W_GAP) + (room_penalty * W_ROOM)

        return {
            "total_weighted_penalty": total_score,
            "penalties": {
                "instructor_gaps": {"raw": gap_penalty, "weighted": gap_penalty * W_GAP, "details": gap_details},
                "room_usage": {"raw": room_penalty, "weighted": room_penalty * W_ROOM}
            }
        }