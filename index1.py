import tkinter as tk
from PIL import Image, ImageTk, ImageFilter
import subprocess

def show_frame(frame):
    frame.tkraise()

def print_button_info(button_name, *args):
    print(f"Button: {button_name}")
    if args:
        print(f"Values: {', '.join(map(str, args))}")

def open_play_window():
    print_button_info("Play Window")
    show_frame(level_frame)

def open_levels_page():
    print_button_info("Levels Page")
    show_frame(level_frame)

def open_terminals(level, scene, town):
    print_button_info("Open Terminals", level, scene, town)
    import open_terminals
    scene_map = {"Scene 1": "1", "Scene 2": "2", "Scene 3": "3"}
    town_map = {"Town 02": 0, "Town 03": 1, "Town 04": 2, "Town 05": 3, "Town 06": 4}
    open_terminals.open_terminals(level, scene_map.get(scene, "Scene 1"), town_map.get(town, 0))

def open_scenes_page(level):
    print_button_info("Scenes Page", level)
    show_frame(scenes_frame)
    for widget in scenes_frame.winfo_children():
        widget.destroy()

    if level == "Easy":
        scenes = ["Scene 1", "Scene 2"]
    else:
        scenes = ["Scene 1", "Scene 2", "Scene 3"]

    for i, scene in enumerate(scenes):
        tk.Button(scenes_frame, text=scene, command=lambda s=scene: open_town_page(level, s), width=20, height=3, font=("Helvetica", 16), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=i, column=0, padx=10, pady=10)

    tk.Button(scenes_frame, text="Back", command=lambda: show_frame(level_frame), width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=len(scenes), column=0, pady=20)

def open_town_page(level, scene):
    print_button_info("Town Page", level, scene)
    show_frame(town_frame)
    for widget in town_frame.winfo_children():
        widget.destroy()

    towns = ["Town 02", "Town 03", "Town 04", "Town 05", "Town 06"]
    for i, town in enumerate(towns):
        tk.Button(town_frame, text=town, command=lambda t=town: open_terminals(level, scene, t), width=20, height=3, font=("Helvetica", 16), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=i, column=0, padx=10, pady=10)

    tk.Button(town_frame, text="Back", command=lambda: open_scenes_page(level), width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=len(towns), column=0, pady=20)

def run_practice_command():
    print_button_info("Practice Command")
    subprocess.run("python3 scenario_runner.py --route srunner/data/final_routes.xml srunner/data/practice_all_towns_traffic_scenarios.json 0 --agent srunner/autoagents/human_agent.py --output", shell=True)

def open_settings():
    print_button_info("Settings")
    show_frame(settings_frame)

def close_app():
    print_button_info("Exit")
    root.destroy()

root = tk.Tk()
root.title("Main Window")
root.attributes('-fullscreen', True)

bg_image = Image.open("/home/cvit-car-simulator/Downloads/images.jpeg")
bg_image = bg_image.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.LANCZOS)
blurred_bg_image = bg_image.filter(ImageFilter.GaussianBlur(radius=5))

bg_photo = ImageTk.PhotoImage(blurred_bg_image)
bg_label = tk.Label(root, image=bg_photo)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

button_color = "#4d4d4d"
bg_color = "#000000"

# Create frames for each page
landing_frame = tk.Frame(root, bg=bg_color)
landing_frame.pack(fill='both', expand=True)

level_frame = tk.Frame(root, bg=bg_color)
scenes_frame = tk.Frame(root, bg=bg_color)
town_frame = tk.Frame(root, bg=bg_color)
settings_frame = tk.Frame(root, bg=bg_color)

for frame in (landing_frame, level_frame, scenes_frame, town_frame, settings_frame):
    frame.grid(row=0, column=0, sticky='nsew')

# Landing Page
tk.Button(landing_frame, text="Practice", command=run_practice_command, width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=0, column=0, pady=10)
tk.Button(landing_frame, text="Play", command=open_play_window, width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=1, column=0, pady=10)
tk.Button(landing_frame, text="Settings", command=open_settings, width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=2, column=0, pady=10)
tk.Button(landing_frame, text="Exit", command=close_app, width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=3, column=0, pady=10)

# Levels Page
for i, level in enumerate(["Easy", "Intermediate", "Hard"]):
    tk.Button(level_frame, text=level, command=lambda l=level: open_scenes_page(l), width=20, height=3, font=("Helvetica", 16), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=i, column=0, padx=10, pady=10)

tk.Button(level_frame, text="Back", command=lambda: show_frame(landing_frame), width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=len(["Easy", "Intermediate", "Hard"]), column=0, pady=20)

# Scenes Page
tk.Button(scenes_frame, text="Back", command=lambda: show_frame(level_frame), width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=0, column=0, pady=20)

# Towns Page
town_frame_inner = tk.Frame(town_frame, bg=bg_color)
town_frame_inner.place(relx=0.5, rely=0.5, anchor='center')

tk.Button(town_frame_inner, text="Back", command=lambda: show_frame(scenes_frame), width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=0, column=0, pady=20)

# Add buttons for towns to the inner town frame
for i, town in enumerate(["Town 02", "Town 03", "Town 04", "Town 05", "Town 06"]):
    tk.Button(town_frame_inner, text=town, command=lambda t=town: open_terminals("Easy", "Scene 1", t), width=20, height=3, font=("Helvetica", 16), bg=button_color, fg="white", borderwidth=0, relief="flat").grid(row=i+1, column=0, padx=10, pady=10)

# Settings Frame
settings_frame_town = tk.Frame(root, bg=bg_color)
settings_frame_town.place(relx=1.0, y=0, anchor='ne')

tk.Button(settings_frame_town, text="Settings", command=open_settings, width=15, height=2, font=("Helvetica", 10), bg=button_color, fg="white", borderwidth=0, relief="flat").pack(pady=20)

show_frame(landing_frame)
root.mainloop()
