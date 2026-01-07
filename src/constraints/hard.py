from collections import defaultdict
from typing import List, Dict, Set, Tuple, Any, Optional

# --- Constants for Readability ---
UNASSIGNED_VALUES = {None, "None", "<>", ""}

# --- Helper Functions ---

def is_assigned(value: Any) -> bool:
    """
    Determines if `value` represents a valid, real assignment.
    Returns False for None, empty strings, "None", "<>".
    """
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in UNASSIGNED_VALUES
    return True

def parse_time_slot(time_slot_str: Any) -> Tuple[Optional[int], Optional[int]]:
    """
    Safely parses a "day-period" string such as "1-3" into integers.
    Returns (None, None) for invalid inputs.
    """
    if not isinstance(time_slot_str, str):
        return None, None

    clean = time_slot_str.strip()
    if "-" not in clean:
        return None, None

    try:
        parts = clean.split("-", maxsplit=1)
        day = int(parts[0].strip())
        period = int(parts[1].strip())
        return day, period
    except (ValueError, IndexError):
        return None, None

def _add_violation(course_id: Any, constraint_name: str, 
                   all_violating_ids: Set[str], 
                   violation_details: Dict[str, List[str]]):
    """
    Records a specific constraint violation for a given course ID.
    """
    cid = str(course_id)
    all_violating_ids.add(cid)
    
    # Initialize list if missing (defensive)
    if cid not in violation_details:
        violation_details[cid] = []
        
    if constraint_name not in violation_details[cid]:
        violation_details[cid].append(constraint_name)

class HardConstraintRules:
    """
    Stateless functional logic for checking specific hard constraints.
    """

    @staticmethod
    def check_instructor_conflict(instructor_schedule: Dict, ids: Set, details: Dict) -> int:
        """
        Ensures an instructor does not teach multiple courses in the same time slot.
        """
        violations = 0
        for _, time_slots in instructor_schedule.items():
            if not isinstance(time_slots, dict): continue
            
            for _, courses in time_slots.items():
                if len(courses) > 1:
                    # Conflict found
                    for course in courses:
                        _add_violation(course['course_id'], "Instructor Conflict", ids, details)
                        violations += 1
        return violations

    @staticmethod
    def check_room_conflict(room_schedule: Dict, ids: Set, details: Dict) -> int:
        """
        Ensures a room is not assigned to more than one course in the same time slot.
        """
        violations = 0
        for _, time_slots in room_schedule.items():
            if not isinstance(time_slots, dict): continue

            for _, courses in time_slots.items():
                if len(courses) > 1:
                    for course in courses:
                        _add_violation(course['course_id'], "Room Conflict", ids, details)
                        violations += 1
        return violations

    @staticmethod
    def check_room_capacity(courses: List[Dict], room_map: Dict, course_map: Dict, ids: Set, details: Dict) -> int:
        """
        Ensures the assigned room has enough capacity for the course.
        """
        violations = 0
        for course in courses:
            course_id = str(course['course_id'])
            room_id = str(course.get('room_id'))
            
            if not is_assigned(room_id):
                continue
            
            course_info = course_map.get(course_id)
            if not course_info: continue

            room_info = room_map.get(room_id)
            if room_info:
                capacity = room_info.get('room_capacity', 0)
                num_students = course_info.get('num_students', 0)
                
                if num_students > capacity:
                    _add_violation(course_id, "Room Capacity", ids, details)
                    violations += 1
        return violations

    @staticmethod
    def check_room_type(courses: List[Dict], room_map: Dict, course_map: Dict, ids: Set, details: Dict) -> int:
        """
        Ensures the assigned room matches the required type.
        """
        violations = 0
        for course in courses:
            course_id = str(course['course_id'])
            room_id = str(course.get('room_id'))
            
            if not is_assigned(room_id):
                continue

            course_info = course_map.get(course_id)
            required_type = course_info.get('required_room_type') if course_info else None
            
            if not required_type:
                continue

            room_info = room_map.get(room_id)
            if room_info and room_info.get('room_type') != required_type:
                _add_violation(course_id, "Room Type", ids, details)
                violations += 1
        return violations

    @staticmethod
    def check_availabilities(courses: List[Dict], entity_map: Dict, entity_key: str, violation_name: str, ids: Set, details: Dict) -> int:
        """
        Generic check for Instructor or Room availability.
        """
        violations = 0
        for course in courses:
            entity_id = str(course.get(entity_key))
            time_slot = course.get('time_slot')

            if not is_assigned(entity_id) or not is_assigned(time_slot):
                continue

            info = entity_map.get(entity_id)
            if info:
                avail_str = str(info.get('available_times', ''))
                valid_slots = {s.strip() for s in avail_str.split(';') if s.strip()}
                
                if valid_slots and time_slot not in valid_slots:
                    _add_violation(course['course_id'], violation_name, ids, details)
                    violations += 1
        return violations

    @staticmethod
    def check_instructor_load(instructor_schedule: Dict, instructor_map: Dict, ids: Set, details: Dict) -> int:
        """
        Ensures instructor max daily load is not exceeded.
        """
        violations = 0
        for inst_id, time_slots in instructor_schedule.items():
            daily_load = defaultdict(int)
            
            for ts, courses in time_slots.items():
                if not courses: continue
                day, _ = parse_time_slot(ts)
                if day is not None:
                    daily_load[day] += 1
            
            inst_info = instructor_map.get(str(inst_id))
            max_load = int(inst_info.get('max_courses_per_day', 4)) if inst_info else 4

            for day, count in daily_load.items():
                if count > max_load:
                    for ts, courses in time_slots.items():
                        d, _ = parse_time_slot(ts)
                        if d == day:
                            for c in courses:
                                _add_violation(c['course_id'], "Instructor Daily Load", ids, details)
                                violations += 1
        return violations

    @staticmethod
    def check_intra_semester(schedule_by_ts: Dict, course_sem_map: Dict, ids: Set, details: Dict) -> int:
        """
        Ensures courses from same semester aren't scheduled simultaneously.
        """
        violations = 0
        for _, courses in schedule_by_ts.items():
            if len(courses) < 2: 
                continue
            
            for i in range(len(courses)):
                for j in range(i + 1, len(courses)):
                    c1 = courses[i]
                    c2 = courses[j]
                    
                    base1 = str(c1['course_id']).split('-')[0]
                    base2 = str(c2['course_id']).split('-')[0]

                    if base1 == base2: 
                        continue

                    sem1 = course_sem_map.get(base1)
                    sem2 = course_sem_map.get(base2)

                    if sem1 and sem2 and sem1 == sem2:
                        _add_violation(c1['course_id'], "Intra-Semester Conflict", ids, details)
                        _add_violation(c2['course_id'], "Intra-Semester Conflict", ids, details)
                        violations += 1
        return violations