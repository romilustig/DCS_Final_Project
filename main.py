from __future__ import annotations

import time
import os
import math
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import serial as ser
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# -----------------------
# Globals & thresholds
# -----------------------
light_epsilon = 0.3
object_light_epsilon = 0.3

s = None  # serial handle
ACK = '0'

# -----------------------
# Core I/O and helpers (UNCHANGED FUNCTIONALITY)
# -----------------------

def send_angle(angle):
    send_data(str(angle).rjust(3, '0'))


def init_uart():
    global s, inChar
    s = ser.Serial('COM5', baudrate=9600, bytesize=ser.EIGHTBITS,
                   parity=ser.PARITY_NONE, stopbits=ser.STOPBITS_ONE,
                   timeout=1)
    s.reset_input_buffer()
    s.reset_output_buffer()
    inChar = '0'


def send_data(data_str):
    global s
    for char in data_str:
        _ = len(data_str)
        send_command(char)
    time.sleep(0.05)
    s.write(bytes('$', 'ascii'))


def send_command(char):
    global s
    s.write(bytes(char, 'ascii'))
    time.sleep(0.05)


def command_encoder(data_str):
    translated_string = ""
    lines = data_str.split('\n')
    for line in lines:
        line = line.strip()
        if line:
            parts = line.split(' ', 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            hex_value = command_dict.get(command)
            if hex_value is not None:
                opcode = hex(hex_value)[2:].zfill(2)
                hex_args = ''
                if args:
                    hex_args_list = [hex(int(arg))[2:].zfill(2).upper() for arg in args.split(',')]
                    hex_args = ''.join(hex_args_list)
                translated_string += opcode + hex_args + '\n'
    return translated_string


def receive_ack():
    global s, ACK
    time.sleep(0.25)
    ACK = s.read_until(expected=b'\0').decode('ascii')


def receive_data():
    chr_ = b''
    while chr_[-1:] != b'\n':
        chr_ += s.read(1)
    return chr_.decode('ascii')


def receive_data2():
    chr_ = b''
    while chr_[-1:] != b'\n':
        chr_ += s.read(1)
    print(chr_)
    return chr_


def receive_char():
    data = b''
    time.sleep(0.25)
    while len(data.decode('ascii')) == 0:
        data = s.read_until(terminator=b'\n')
    return data.decode('ascii')


def receive_calib():
    data = b''
    time.sleep(0.25)
    while len(data.decode('ascii')) == 0:
        data = s.read_until(terminator=b'\n')
    return data


def save_calibration_values(calibration_values):
    with open('calibration_values.txt', 'w') as file:
        for value in calibration_values:
            file.write(str(value) + '\n')


def expand_calibration_array(calibration_array, new_length):
    expanded_array = np.zeros(new_length)
    for i in range(new_length):
        index = i // 5
        fraction = i % 5
        if i < 45:
            value = calibration_array[index] + (calibration_array[index + 1] - calibration_array[index]) * fraction / 5
        else:
            value = calibration_array[9]
        expanded_array[i] = value
    return expanded_array.tolist()


def measure_two_ldr_samples():
    LDR1_val = int(receive_data()) / 292
    time.sleep(0.25)
    if LDR1_val > 1023 / 292:
        return [-1, 0, 0]
    LDR2_val = int(receive_data()) / 292
    fitting_index = find_fitting_index(LDR1_val, LDR2_val)
    return [fitting_index, LDR1_val, LDR2_val]


def find_fitting_index(ldr1_value, ldr2_value):
    with open('calibration_values.txt', 'r') as file:
        calibration_arr = [float(line.strip()) for line in file]
    average_ldr_value = (ldr1_value + ldr2_value) / 2
    left = 0
    right = len(calibration_arr) - 1
    fitting_value = None
    while left <= right:
        mid = (left + right) // 2
        if calibration_arr[mid] == average_ldr_value:
            fitting_value = calibration_arr[mid]
            break
        elif calibration_arr[mid] > average_ldr_value:
            fitting_value = calibration_arr[mid]
            left = mid + 1
        else:
            fitting_value = calibration_arr[mid]
            right = mid - 1
    if fitting_value is None:
        if average_ldr_value < calibration_arr[-1]:
            fitting_value = calibration_arr[-1]
        elif average_ldr_value > calibration_arr[0]:
            fitting_value = calibration_arr[0]
    return 49 - calibration_arr.index(fitting_value)

# -----------------------
# Plot windows (Tkinter)
# -----------------------

def draw_scanner_map(distances, angles):
    win = tk.Toplevel()
    win.title("Scanner Map")
    win.geometry("820x860")

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)

    min_distance = min(distances) if distances else 0
    max_distance = max(distances) if distances else 50
    norm = plt.Normalize(vmin=min_distance, vmax=max_distance)
    cmap = cm.get_cmap('coolwarm')

    for distance, angle in zip(distances, angles):
        rad_angle = math.radians(angle)
        color = cmap(1 - norm(distance))
        ax.scatter(rad_angle, distance, color=color, s=10)

    radii = ax.get_yticks()
    for radius in radii[1:]:
        ax.text(0, radius, str(radius), ha='center', va='bottom', fontsize=8)

    padding = max_distance * 0.1
    ax.set_ylim(0, max_distance + padding)
    ax.set_yticklabels([])
    ax.set_xticklabels([])

    ax.spines["polar"].set_visible(True)
    ax.spines["polar"].set_color("black")
    ax.spines["polar"].set_linewidth(0.5)
    ax.spines["polar"].set_position(("data", 0))

    for spine in ax.spines.values():
        if getattr(spine, 'spine_type', '') != "polar":
            spine.set_visible(False)

    ax.set_ylim(0, max_distance + padding * 0.3)
    ax.set_xticks(ax.get_xticks()[::2])
    ax.set_xticklabels([str(int(math.degrees(tick))) + "°" for tick in ax.get_xticks()])

    if angles:
        start_angle = angles[0] - 5
        end_angle = angles[-1] - 5
        if start_angle != 0:
            ax.plot([math.radians(start_angle), math.radians(start_angle)], [0, max_distance], 'k-', linewidth=3)
            ax.text(math.radians(start_angle), max_distance + padding * 0.15, f"{start_angle}°", ha='center', va='center', fontsize=15)
        if end_angle != 180:
            ax.plot([math.radians(end_angle), math.radians(end_angle)], [0, max_distance], 'k-', linewidth=3)
            ax.text(math.radians(end_angle), max_distance + padding * 0.15, f"{end_angle}°", ha='center', va='center', fontsize=15)

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)
    win.grab_set()
    win.wait_window()


def draw_scanner_map_lights(distances, lights, angles):
    win = tk.Toplevel()
    win.title("Scanner Map")
    win.geometry("820x860")

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)

    max_distance = max(distances) if distances else 50
    if max_distance == 0:
        max_distance = 50

    i = j = 0
    for distance, light, angle in zip(distances, lights, angles):
        rad_angle = math.radians(angle)
        if light > 0 and distance < 50:
            color = "yellow"
            ax.scatter(rad_angle, distance, color=color, s=50, edgecolors='black', label="Light Source" if i == 0 else "")
            i += 1
        else:
            color = "black"
            ax.scatter(rad_angle, distance, color=color, s=10, label="Object" if j == 0 else "")
            j += 1

    ax.legend()

    padding = max_distance * 0.1
    ax.set_ylim(0, max_distance + padding)
    ax.set_yticklabels([])
    ax.set_xticklabels([])

    radii = ax.get_yticks()
    for radius in radii[1:]:
        ax.text(0, radius, str(radius), ha='center', va='bottom', fontsize=8)

    ax.spines["polar"].set_visible(True)
    ax.spines["polar"].set_color("black")
    ax.spines["polar"].set_linewidth(0.5)
    ax.spines["polar"].set_position(("data", 0))

    for spine in ax.spines.values():
        if getattr(spine, 'spine_type', '') != "polar":
            spine.set_visible(False)

    ax.set_ylim(0, max_distance + padding * 0.3)
    ax.set_xticks(ax.get_xticks()[::2])
    ax.set_xticklabels([str(int(math.degrees(tick))) + "°" for tick in ax.get_xticks()])

    if angles:
        start_angle = angles[0] - 5
        end_angle = angles[-1] - 5
        if start_angle != 0:
            ax.plot([math.radians(start_angle), math.radians(start_angle)], [0, max_distance], 'k-', linewidth=3)
            ax.text(math.radians(start_angle), max_distance + padding * 0.15, f"{start_angle}°", ha='center', va='center', fontsize=15)
        if end_angle != 180:
            ax.plot([math.radians(end_angle), math.radians(end_angle)], [0, max_distance], 'k-', linewidth=3)
            ax.text(math.radians(end_angle), max_distance + padding * 0.15, f"{end_angle}°", ha='center', va='center', fontsize=15)

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)
    win.grab_set()
    win.wait_window()

# -----------------------
# Feature Windows (Tkinter)
# -----------------------

def _make_toplevel(title: str) -> tuple[tk.Toplevel, ttk.Frame]:
    win = tk.Toplevel()
    win.title(title)
    win.geometry("700x500")
    container = ttk.Frame(win, padding=10)
    container.pack(fill="both", expand=True)
    return win, container


def _make_output(parent) -> tk.Text:
    out = tk.Text(parent, height=8, wrap="word")
    out.tag_configure("red_text", foreground="red")
    out.tag_configure("green_text", foreground="green")
    out.tag_configure("blue_text", foreground="blue")
    out.configure(state="normal")
    out.grid(row=99, column=0, columnspan=4, sticky="nsew", pady=(8,0))
    parent.rowconfigure(99, weight=1)
    parent.columnconfigure(0, weight=1)
    return out


# -----------------------
# Main Functions
# -----------------------


def objects_detector():
    send_command('1')
    win, root = _make_toplevel("Objects Detector System")

    ttk.Label(root, text="Max Distance (cm):").grid(row=0, column=0, sticky="w")
    max_dist_var = tk.IntVar(value=400)  # default
    slider = tk.Scale(root, from_=1, to=400, orient="horizontal", variable=max_dist_var)
    slider.grid(row=0, column=1, sticky="we", padx=6)

    out = _make_output(root)

    btn_scan = ttk.Button(root, text="Start Scan", style="Action.TButton")
    btn_back = ttk.Button(root, text="Back", style="Action.TButton")
    btn_scan.grid(row=1, column=0, pady=6, sticky="w")
    btn_back.grid(row=1, column=1, pady=6, sticky="w")

    def scan():
        btn_scan.config(state="disabled")
        btn_back.config(state="disabled")
        distance_arr = []
        # max_distance = dist_var.get()
        send_command('G')
        angle1 = int(receive_data())
        angle2 = int(receive_data())
        counter = 0
        while True:
            win.update()
            distance = int(receive_data())
            if distance == 500:
                break
            current_max = max_dist_var.get()
            if counter > 4:
                if distance < int(current_max):
                    distance_arr.append(distance)
                    out.insert("end", f"Distance: {distance:>3} [cm]\n")
                else:
                    out.insert("end", f"Distance: {distance:>3} [cm]")
                    out.insert("end", " - MASKED\n", "red_text")
                    distance_arr.append(0)
            counter += 1
        degree_arr = [round(float(5) + i * (float(180) - float(0)) / (len(distance_arr) - 1), 1)
                      for i in range(len(distance_arr))]
        out.insert("end", f"Distance array: {distance_arr}\n")
        out.insert("end", f"Degree array: {degree_arr}\n")
        draw_scanner_map(distance_arr, degree_arr)
        btn_scan.config(state="normal")
        btn_back.config(state="normal")

    # def go_back():
    #     send_command('0')
    #     win.destroy()

    btn_scan.config(command=scan)
    btn_back.config(command=lambda: (send_command('0'), win.destroy()))

    win.grab_set(); win.wait_window()


def telemeter():
    send_command('2')
    win, root = _make_toplevel("Telemeter")

    ttk.Label(root, text="Choose Angle between - 0° to 180°:").grid(row=0, column=0, sticky="w")
    angle_var = tk.StringVar()
    ttk.Entry(root, textvariable=angle_var, width=12).grid(row=0, column=1, sticky="w")

    out = _make_output(root)

    btn_start = ttk.Button(root, text="Start", style="Action.TButton")
    btn_stop = ttk.Button(root, text="Stop", style="Action.TButton", state="disabled")
    btn_back = ttk.Button(root, text="Back", style="Action.TButton")
    btn_start.grid(row=1, column=0, pady=6, sticky="w")
    btn_stop.grid(row=1, column=1, pady=6, sticky="w")
    btn_back.grid(row=1, column=2, pady=6, sticky="w")

    dynamic_flag = {"val": 0}

    def poll():
        if dynamic_flag["val"]:
            distance = int(receive_data())
            angle = int(receive_data())
            out.insert("end", f"Distance: {distance:>3} [cm] | Angle: {angle:>3} [°]\n")
            out.see("end")
            win.after(100, poll)

    def start():
        btn_start.config(state="disabled")
        btn_back.config(state="disabled")
        btn_stop.config(state="normal")
        out.insert("end", "Performing Ultrasonic Scan\n")
        send_command('H')
        try:
            angle = int(angle_var.get())
        except ValueError:
            messagebox.showerror("Invalid angle", "Enter a valid angle")
            btn_start.config(state="normal"); btn_back.config(state="normal"); btn_stop.config(state="disabled")
            return
        dynamic_flag["val"] = 1
        send_angle(angle)
        poll()

    def stop():
        btn_stop.config(state="disabled")
        btn_start.config(state="normal")
        btn_back.config(state="normal")
        send_command('I')
        dynamic_flag["val"] = 0

    # def back():
    #     send_command('0')
    #     win.destroy()

    btn_start.config(command=start)
    btn_stop.config(command=stop)
    btn_back.config(command=lambda: (send_command('0'), win.destroy()))

    win.grab_set(); win.wait_window()


def lights_detector():
    send_command('3')
    win, root = _make_toplevel("Light Sources Detector System")

    btn_scan = ttk.Button(root, text="Start Scan", style="Action.TButton")
    btn_back = ttk.Button(root, text="Back", style="Action.TButton")
    btn_scan.grid(row=0, column=0, pady=6, sticky="w")
    btn_back.grid(row=0, column=2, pady=6, sticky="w")

    pbar = ttk.Progressbar(root, orient='horizontal', maximum=10, length=400)
    pbar.grid(row=1, column=0, columnspan=3, pady=6, sticky="ew")

    out_lbl = ttk.Label(root, text=" ")
    out_lbl.grid(row=2, column=0, columnspan=3, sticky="w")

    out = _make_output(root)

    def scan():
        btn_back.config(state="disabled")
        btn_scan.config(state="disabled")
        distance_arr = []
        masking_distance = 49
        send_command('K')
        angle1 = int(receive_data())
        angle2 = int(receive_data())
        counter = 0
        flag = 0
        while True:
            win.update()
            arr = measure_two_ldr_samples()
            if counter > 8:
                light_distance = arr[0] + 1
                ldr_val1 = arr[1]
                ldr_val2 = arr[2]
                if light_distance == 0:
                    break
                LDR1_val_trunc = f"{ldr_val1:.2f}"
                LDR2_val_trunc = f"{ldr_val2:.2f}"
                out.insert("end", f"Left LDR value: {LDR1_val_trunc} [V] | Right LDR value: {LDR2_val_trunc} [V]")
                out.insert("end", f" | Estimate Distance: {light_distance} [cm]")
                if abs(ldr_val1 - ldr_val2) < light_epsilon and ldr_val1 < 3 and ldr_val2 < 3:
                    if light_distance > int(masking_distance):
                        out.insert("end", " (MASKED) \n", "red_text")
                        distance_arr.append(0)
                        flag = 0
                    else:
                        out.insert("end", " - LIGHT DETECTED \n", "green_text")
                        if flag == 1:
                            distance_arr.append(light_distance)
                        else:
                            distance_arr.append(0)
                        flag = 1
                else:
                    flag = 0
                    out.insert("end", " (NOISE) \n", "red_text")
                    distance_arr.append(0)
            counter += 1
        degree_arr = [round(float(5) + i * (float(180) - float(0)) / (len(distance_arr) - 1), 1)
                      for i in range(len(distance_arr))]
        out.insert("end", f"Distance array: {distance_arr}\n")
        out.insert("end", f"Degree array: {degree_arr}\n")
        draw_scanner_map_lights(distance_arr, distance_arr, degree_arr)
        btn_back.config(state="normal")
        btn_scan.config(state="normal")

    btn_scan.config(command=scan)
    btn_back.config(command=lambda: (send_command('0'), win.destroy()))

    win.grab_set(); win.wait_window()


def light_objects_detector():
    send_command('4')
    win, root = _make_toplevel("Light Sources and Objects Detector System")

    ttk.Label(root, text="Max Distance (cm):").grid(row=0, column=0, sticky="w")
    max_dist_var = tk.IntVar(value=400)  # default
    slider = tk.Scale(root, from_=1, to=400, orient="horizontal", variable=max_dist_var)
    slider.grid(row=0, column=1, sticky="we", padx=6)

    ttk.Label(root, text="Max range for lights is 0.5 meter").grid(row=1, column=0, columnspan=2, sticky="w")

    btn_go = ttk.Button(root, text="Start Scan", style="Action.TButton")
    btn_back = ttk.Button(root, text="Back", style="Action.TButton")
    btn_go.grid(row=2, column=0, pady=6, sticky="w")
    btn_back.grid(row=2, column=1, pady=6, sticky="w")

    out = _make_output(root)

    def scan():
        btn_go.config(state="disabled")
        btn_back.config(state="disabled")
        distance_arr = []
        light_arr = []
        # masking_distance_objects = dist_var.get()
        masking_distance_lights = 50
        send_command('X')
        angle1 = int(receive_data())
        angle2 = int(receive_data())
        counter = 0
        flag = 0
        while True:
            win.update()
            distance = int(receive_data())
            if distance == 9999:
                break
            arr = measure_two_ldr_samples()
            current_max = max_dist_var.get()
            if counter > 4:
                light_distance = arr[0] + 1
                ldr_val1 = arr[1]
                ldr_val2 = arr[2]
                if distance > int(current_max):
                    out.insert("end", f"Measured Distance: {distance} [cm]")
                    out.insert("end", " (MASKED) ", "red_text")
                    distance_arr.append(0)
                else:
                    out.insert("end", f"Measured Distance: {distance} [cm]")
                    distance_arr.append(distance)
                out.insert("end", f" | Estimate Light Distance: {light_distance} [cm]")
                if abs(ldr_val1 - ldr_val2) < object_light_epsilon and ldr_val1 < 3 and ldr_val2 < 3:
                    out.insert("end", " - LIGHT DETECTED", "green_text")
                    if light_distance > int(masking_distance_lights):
                        light_arr.append(0)
                        flag = 0
                        out.insert("end", " (MASKED) \n", "red_text")
                    else:
                        if flag == 1:
                            light_arr.append(light_distance)
                        else:
                            light_arr.append(0)
                        out.insert("end", "\n")
                        flag = 1
                else:
                    out.insert("end", " (NOISE) \n", "red_text")
                    flag = 0
                    light_arr.append(0)
            counter += 1
        degree_arr = [round(float(5) + i * (float(180) - float(0)) / (len(distance_arr) - 1), 1)
                      for i in range(len(distance_arr))]
        out.insert("end", f"Distance array: {distance_arr}\n")
        out.insert("end", f"Lights array: {light_arr}\n")
        out.insert("end", f"Degree array: {degree_arr}\n")
        draw_scanner_map_lights(distance_arr, light_arr, degree_arr)
        btn_go.config(state="normal")
        btn_back.config(state="normal")

    btn_go.config(command=scan)
    btn_back.config(command=lambda: (send_command('0'), win.destroy()))

    win.grab_set(); win.wait_window()


def script_mode():
    send_command('5')
    global ACK
    win, root = _make_toplevel("Upload File")

    working_directory = "C:\\Users\\David Lustig\\Downloads"

    ttk.Label(root, text="Choose a TXT file to upload:").grid(row=0, column=0, sticky="w")
    path_var = tk.StringVar()
    ttk.Entry(root, textvariable=path_var, width=60).grid(row=1, column=0, sticky="ew")

    def browse():
        fp = filedialog.askopenfilename(initialdir=working_directory, filetypes=[("text Files", "*.txt")])
        if fp:
            path_var.set(fp)

    ttk.Button(root, text="Browse", command=browse).grid(row=1, column=1, padx=6)

    btn_u1 = ttk.Button(root, text="Upload Script1", style="Action.TButton")
    btn_p1 = ttk.Button(root, text="Play Script1", style="Action.TButton")
    btn_u2 = ttk.Button(root, text="Upload Script2", style="Action.TButton")
    btn_p2 = ttk.Button(root, text="Play Script2", style="Action.TButton")
    btn_u3 = ttk.Button(root, text="Upload Script3", style="Action.TButton")
    btn_p3 = ttk.Button(root, text="Play Script3", style="Action.TButton")
    btn_back = ttk.Button(root, text="Back", style="Action.TButton")
    row = 2
    for b in (btn_u1, btn_p1, btn_u2, btn_p2, btn_u3, btn_p3, btn_back):
        b.grid(row=row, column=0, sticky="w", pady=3)
        row += 1

    status_lbl = ttk.Label(root, text="", font=("Segoe UI", 10, "bold"))
    status_lbl.grid(row=row, column=0, sticky="w", pady=(8,2))

    out = _make_output(root)

    def set_controls(state: str):
        for b in (btn_u1, btn_p1, btn_u2, btn_p2, btn_u3, btn_p3, btn_back):
            b.config(state=state)

    def do_upload(slot: str):
        nonlocal path_var
        set_controls("disabled")
        send_command(slot)
        file_address = path_var.get()
        script = open(file_address)
        string = command_encoder(script.read())
        print(os.path.basename(script.name))
        command = str(len(string).to_bytes(1, 'big'))[2]
        send_command(command)
        send_data(string)
        receive_ack()
        set_controls("normal")

    def do_play(slot: str, label: str):
        nonlocal status_lbl
        set_controls("disabled")
        send_command(slot)
        status_lbl.config(text=f"{label}, Please wait.")
        while True:
            win.update()
            opcode = receive_char()
            opcode_dict = {
                '1': "Increment char on LCD from 0 to 'x'",
                '2': "Decrement char on LCD from 'x' to 0",
                '3': "Right rotating char 'x' on LCD Screen",
                '4': "Setting delay value",
                '5': "Clearing LCD screen",
                '6': "Moving sensor to specific angle and measure distance",
                '7': "Scanning environment from angle1 to angle2",
                '8': "MSP goes back to sleep mode"
            }
            out.insert("end", f"Playing Opcode {opcode}: ", "blue_text")
            print(f"({opcode_dict[opcode]})")
            if opcode == '6':
                distance = int(receive_data())
                angle = int(receive_data())
                print(f"Measured Distance: {distance} [cm], Measured Angle: {angle} [°]")
            elif opcode == '7':
                distance_arr = []
                angle1 = int(receive_data())
                angle2 = int(receive_data())
                while True:
                    win.update()
                    distance = int(receive_data())
                    if distance == 999:
                        break
                    print(f"Measured Distance: {distance} [cm]")
                    distance_arr.append(distance)
                degree_arr = [
                    round(float(angle1) + i * (float(angle2) - float(angle1)) / (len(distance_arr) - 1), 1)
                    for i in range(len(distance_arr))]
                print(f"Distance array: {distance_arr}")
                print(f"Degree array: {degree_arr}")
                draw_scanner_map(distance_arr, degree_arr)
            elif opcode == '8':
                break
        set_controls("normal")

    btn_u1.config(command=lambda: do_upload('A'))
    btn_u2.config(command=lambda: do_upload('B'))
    btn_u3.config(command=lambda: do_upload('C'))

    btn_p1.config(command=lambda: do_play('D', 'Playing Script1'))
    btn_p2.config(command=lambda: do_play('E', 'Playing Script2'))
    btn_p3.config(command=lambda: do_play('F', 'Playing Script3'))

    # def go_back():
    #     send_command('0')
    #     win.destroy()

    btn_back.config(command=lambda: (send_command('0'), win.destroy()))

    def update_status():
        global ACK
        if ACK == '1':
            status_lbl.config(text="Script1 Transferred")
        elif ACK == '2':
            status_lbl.config(text="Script2 Transferred")
        elif ACK == '3':
            status_lbl.config(text="Script3 Transferred")
        else:
            status_lbl.config(text="")
        win.after(250, update_status)

    update_status()
    # win.grab_set(); win.wait_window()


def light_calibrate():
    send_command('3')
    win, root = _make_toplevel("Light Detector Calibrate")

    btn_cal = ttk.Button(root, text="Calibrate Using PB0", style="Action.TButton")
    btn_back = ttk.Button(root, text="Back", style="Action.TButton")
    btn_cal.grid(row=0, column=1, pady=6, sticky="w")
    btn_back.grid(row=0, column=2, pady=6, sticky="w")

    pbar = ttk.Progressbar(root, orient='horizontal', maximum=10, length=400)
    pbar.grid(row=1, column=0, columnspan=3, pady=6, sticky="ew")

    out_lbl = ttk.Label(root, text=" ")
    out_lbl.grid(row=2, column=0, columnspan=3, sticky="w")

    out = _make_output(root)

    def calibrate():
        LDR_calibrate_arr = []
        btn_back.config(state="disabled")
        btn_cal.config(state="disabled")
        btn_cal.config(text="Press PB0 to calibrate")
        pbar['value'] = 0
        out_lbl.config(text="")
        send_command('J')
        for i in range(10):
            win.update()
            out.insert("end", f"Press PB0 to take a sample: {i + 1}\n")
            LDR1_val = int(receive_data()) / 292
            LDR2_val = int(receive_data()) / 292
            LDR1_val_trunc = f"{LDR1_val:.2f}"
            LDR2_val_trunc = f"{LDR2_val:.2f}"
            LDRavg_val_trunc = f"{((LDR1_val + LDR2_val) / 2):.2f}"
            out.insert("end", f"Left LDR value: {LDR1_val_trunc} [V]| Right LDR value: {LDR2_val_trunc} [V]\n")
            out.insert("end", f"Average value: {LDRavg_val_trunc} [V]\n")
            LDR_calibrate_arr.append((LDR1_val + LDR2_val) / 2)
            pbar['value'] = i + 1
            out_lbl.config(text=f"sample {i + 1} received")
            time.sleep(0.05)
        btn_back.config(state="normal")
        btn_cal.config(text="Done Calibrating!")
        pbar['value'] = 0
        expanded = expand_calibration_array(LDR_calibrate_arr, 50)
        save_calibration_values(expanded)


    btn_cal.config(command=calibrate)
    btn_back.config(command=lambda: (send_command('0'), win.destroy()))

    win.grab_set(); win.wait_window()


def init_calibrate():
    send_command('6')
    msp_calib_arr = []
    ldr_val = receive_data2()
    for i in ldr_val:
        msp_calib_arr.append((4 * i) / 292.0)
    flash_expanded = expand_calibration_array(msp_calib_arr, 50)
    save_calibration_values(flash_expanded)

# -----------------------
# Main Window (Tkinter)
# -----------------------

def main():
    global s

    root = tk.Tk()
    style = ttk.Style(root)
    style.configure("Nav.TButton", font=("Segoe UI Emoji", 16, "bold"), padding=(20, 14))
    style.configure("Action.TButton", font=("Segoe UI", 13), padding=(16, 12))
    root.title("Light Source and Object Proximity Detector System")
    root.geometry("980x640")

    # Top bar
    top = ttk.Frame(root, padding=(10,8))
    top.pack(side="top", fill="x")
    ttk.Label(top, text="Light Source & Object Proximity Detector", font=("Segoe UI", 16, "bold")).pack(side="left")
    status_var = tk.StringVar(value="Ready")
    ttk.Label(top, textvariable=status_var, foreground="#64748B").pack(side="right")

    # Body: left nav + right pane
    body = ttk.Frame(root)
    body.pack(fill="both", expand=True)

    nav = ttk.Frame(body, padding=8)
    nav.pack(side="left", fill="y")

    content = ttk.Frame(body, padding=12)
    content.pack(side="right", fill="both", expand=True)

    # Right content (home info)
    home_title = ttk.Label(content, text="Welcome!", font=("Segoe UI", 14, "bold"))
    home_desc = ttk.Label(content, text="Use the navigation to open a feature. The UI is fully rewritten in Tkinter.")
    home_title.pack(anchor="w")
    home_desc.pack(anchor="w", pady=(0,10))

    # Navigation buttons
    ttk.Button(nav, text="📡  Object Detector", width=28, style="Nav.TButton",
               command=objects_detector).pack(anchor="w", pady=8)
    ttk.Button(nav, text="📏  Telemeter", width=28, style="Nav.TButton",
               command=telemeter).pack(anchor="w", pady=8)
    ttk.Button(nav, text="💡  Light Sources", width=28, style="Nav.TButton",
               command=lights_detector).pack(anchor="w", pady=8)
    ttk.Button(nav, text="🧭  Lights + Objects", width=28, style="Nav.TButton",
               command=light_objects_detector).pack(anchor="w", pady=8)
    ttk.Button(nav, text="📝  Script Mode", width=28, style="Nav.TButton",
               command=script_mode).pack(anchor="w", pady=8)
    ttk.Button(nav, text="⚙️💡  Light Calibrate", width=28, style="Nav.TButton",
               command=light_calibrate).pack(anchor="w", pady=8)



    def on_exit():
        try:
            send_command('Q')
        except Exception:
            pass
        root.destroy()

    ttk.Button(nav, text="Exit", width=28, style="Nav.TButton",
               command=on_exit).pack(anchor="w", pady=(12, 0))
    # Perform the same startup handshake (unchanged behavior)
    try:
        init_uart()
        init_calibrate()
        status_var.set("Connected and calibrated from MSP")
    except Exception as e:
        status_var.set(f"Startup issue: {e}")
        messagebox.showerror("Startup", f"Could not complete startup handshake.\n\n{e}")

    root.mainloop()


if __name__ == '__main__':
    command_dict = {
        "inc_lcd": 0x01,
        "dec_lcd": 0x02,
        "rra_lcd": 0x03,
        "set_delay": 0x04,
        "clear_lcd": 0x05,
        "servo_deg": 0x06,
        "servo_scan": 0x07,
        "sleep": 0x08
    }
    main()