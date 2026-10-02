# src/scheduling/assignment.py

class Assignment:

    def __init__(self, group_id: str, classroom: str, day: int, start_block: int):
        self.group_id = group_id
        self.classroom = classroom
        self.day = day
        self.start_block = start_block