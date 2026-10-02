import tkinter as tk
from tkinter import ttk, messagebox
        
from ..scheduling.scheduler import Scheduler
from ..scheduling.schedule_state import ScheduleState
from ..scheduling.time_model import TimeModel
from ..scheduling.classroom import Classroom
from ..scheduling.group import Group


class SchedulerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Academic Scheduler")

        self.scheduler = Scheduler()
        self.groups = []
        self.state = None

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)

        load_btn = ttk.Button(btn_frame, text="Load Sample Data", command=self.load_sample_data)
        load_btn.pack(side="left", padx=5)

        run_btn = ttk.Button(btn_frame, text="Run Scheduler", command=self.run_scheduler)
        run_btn.pack(side="left", padx=5)

        self.tree = ttk.Treeview(frame, columns=("Classroom", "Day", "Start Block"), show="headings")
        self.tree.heading("Classroom", text="Classroom")
        self.tree.heading("Day", text="Day")
        self.tree.heading("Start Block", text="Start Block")
        self.tree.pack(fill="both", expand=True)

    def load_sample_data(self):
        time_model = TimeModel(days=5, blocks_per_day=8)

        classrooms = [
            Classroom("Room1", 30, "Normal"),
            Classroom("Room2", 30, "Normal"),
            Classroom("Lab1", 25, "Laboratory")
        ]

        self.groups = [
            Group("MAT101-G1", "MAT101", 2, "Normal"),
            Group("PHY201-G1", "PHY201", 3, "Laboratory"),
            Group("ENG301-G1", "ENG301", 1, "Normal")
        ]

        self.state = ScheduleState(time_model, classrooms)

        messagebox.showinfo("Info", "Sample data loaded.")

    def run_scheduler(self):
        if not self.state or not self.groups:
            messagebox.showwarning("Warning", "Load data first.")
            return

        success = self.scheduler.schedule(self.state, self.groups)

        if not success:
            messagebox.showerror("Error", "No valid schedule found.")
            return

        self._display_results()

    def _display_results(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for group in self.groups:
            classroom, day, block = group.assignment
            self.tree.insert("", "end", values=(classroom, day, block))


def run_app():
    root = tk.Tk()
    app = SchedulerApp(root)
    root.mainloop()