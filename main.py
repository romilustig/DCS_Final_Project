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
    s = ser.Serial('COM3', baudrate=9600, bytesize=ser.EIGHTBITS,
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
    s.write(bytes(char, 'ascii', errors='ignore'))
    time.sleep(0.05)


def file_command_encoder(data_str):
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
    #time.sleep(0.25)
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
    #print(chr_)
    return chr_


def receive_char():
    data = b''
    time.sleep(0.25)
    while len(data.decode('ascii')) == 0:
        data = s.read_until(expected=b'\n')
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
    with open('calibration_values_2.txt', 'r') as file:
        calibration_arr = [float(line.strip()) for line in file]
    average_ldr_value = (ldr1_value + ldr2_value) / 2

    # Find closest value
    min_diff = float("inf")
    fitting_index = 0
    for i, val in enumerate(calibration_arr):
        diff = abs(val - average_ldr_value)
        if diff < min_diff:
            min_diff = diff
            fitting_index = i

    # Return the index (0..49)
    return fitting_index

import mplcursors

def draw_scanner_map(distances, angles):
    win = tk.Toplevel()
    win.title("Scanner Map")
    win.geometry("950x500")

    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(111, polar=True)

    # Horizontal layout: 0° at right, 180° at left
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)
    ax.set_thetamin(0)
    ax.set_thetamax(180)

    max_distance = max(distances) if distances else 50
    if max_distance == 0:
        max_distance = 50

    # scatter all points in one artist (black objects)
    rad_angles = [math.radians(a) for a in angles]
    ax.scatter(rad_angles, distances, color="black", s=40, alpha=0.8, edgecolors="k")

    # style
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.6)
    ax.set_facecolor("#f5f5f5")

    padding = max_distance * 0.1
    ax.set_ylim(0, max_distance + padding)

    for radius in ax.get_yticks()[1:]:
        ax.text(math.radians(90), radius, f"{int(radius)} cm",
                ha="center", va="bottom", fontsize=8)

    ax.set_xticks([math.radians(a) for a in range(0, 181, 30)])
    ax.set_xticklabels([f"{a}°" for a in range(0, 181, 30)], fontsize=9)

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)
    win.grab_set()
    win.wait_window()


def draw_scanner_map_lights(distances, lights, angles):
    win = tk.Toplevel()
    win.title("Scanner Map - Lights")
    win.geometry("950x500")

    fig = plt.figure(figsize=(10, 5))
    ax = fig.add_subplot(111, polar=True)

    # Horizontal layout: 0° at right, 180° at left
    ax.set_theta_zero_location("E")
    ax.set_theta_direction(1)
    ax.set_thetamin(0)
    ax.set_thetamax(180)

    max_distance = max(distances) if distances else 50
    if max_distance == 0:
        max_distance = 50

    rad_angles = [math.radians(a) for a in angles]
    colors = ["yellow" if (l > 0 and d < 50) else "black"
              for d, l in zip(distances, lights)]
    sizes = [80 if (l > 0 and d < 50) else 30
             for d, l in zip(distances, lights)]

    ax.scatter(rad_angles, distances, c=colors, s=sizes,
               edgecolors="black", alpha=0.85)

    # legend with one entry each
    ax.scatter([], [], c="yellow", s=80, edgecolors="black", label="Light Source")
    ax.scatter([], [], c="black", s=30, label="Object")
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))

    # style
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.6)
    ax.set_facecolor("#f5f5f5")

    padding = max_distance * 0.1
    ax.set_ylim(0, max_distance + padding)

    for radius in ax.get_yticks()[1:]:
        ax.text(math.radians(90), radius, f"{int(radius)} cm",
                ha="center", va="bottom", fontsize=8)

    ax.set_xticks([math.radians(a) for a in range(0, 181, 30)])
    ax.set_xticklabels([f"{a}°" for a in range(0, 181, 30)], fontsize=9)

    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)
    win.grab_set()
    win.wait_window()

# -----------------------
# Plot windows (Tkinter)
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
        send_command('U')
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
            out.insert("end", f"Distance: {distance:>3} [cm]\n")
            out.see("end")
            win.after(100, poll)

    def start():
        btn_start.config(state="disabled")
        btn_back.config(state="disabled")
        btn_stop.config(state="normal")
        out.insert("end", "Performing Ultrasonic Scan\n")
        send_command('V')
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
        send_command('W')
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
        masking_distance = 50
        send_command('Y')
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
        send_command('Z')
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


def file_mode():
    send_command('5')
    global ACK
    win, root = _make_toplevel("Upload File")

    working_directory = r"C:\Users\Omer Pintel\Downloads\DCS-Final-Project-main\DCS-Final-Project-main\CCS\Scripts"

    ttk.Label(root, text="Choose a TXT file to upload:").grid(row=0, column=0, sticky="w")
    path_var = tk.StringVar()
    ttk.Entry(root, textvariable=path_var, width=60).grid(row=1, column=0, columnspan=2, sticky="ew")

    def browse():
        fp = filedialog.askopenfilename(initialdir=working_directory, filetypes=[("Text Files", "*.txt")])
        if fp:
            path_var.set(fp)

    ttk.Button(root, text="Browse", command=browse).grid(row=1, column=2, padx=6)

    # === Button grid ===
    button_refs = []
    for x in range(1, 11):  # slots 1–10
        btn_file   = ttk.Button(root, text=f"Upload File_{x}",   style="Action.TButton")
        btn_script = ttk.Button(root, text=f"Upload Script_{x}", style="Action.TButton")
        btn_play   = ttk.Button(root, text=f"Play {x}",          style="Action.TButton", state="disabled")

        btn_file.grid(  row=x+2, column=0, padx=4, pady=3, sticky="ew")
        btn_script.grid(row=x+2, column=1, padx=4, pady=3, sticky="ew")
        btn_play.grid(  row=x+2, column=2, padx=4, pady=3, sticky="ew")
        button_refs.append((btn_file, btn_script, btn_play))

    root.grid_columnconfigure(0, weight=2)
    root.grid_columnconfigure(1, weight=1)
    # PB1 simulated
    btn_pb1 = ttk.Button(root, text="PB1", style="Action.TButton",command=lambda: (send_command('a')))
    btn_pb1.grid( row=13, column=1, pady=(10,5), sticky="ew")
    # Back button (full width at bottom of left section)
    btn_back = ttk.Button(root, text="Back", style="Action.TButton",
                          command=lambda: (send_command('0'), win.destroy()))
    btn_back.grid(row=13, column=0, pady=(10, 5), sticky="ew")

    # Make columns 0..2 uniform; give column 3 (output) extra weight
    for c in range(3):
        root.grid_columnconfigure(c, weight=1, uniform="col")
    root.grid_columnconfigure(3, weight=2)  # output pane grows more

    # === OUTPUT PANE ON THE RIGHT (scrollable) ===
    out_frame = ttk.Frame(root)
    # Span most rows so it aligns next to the buttons
    out_frame.grid(row=0, column=3, rowspan=16, sticky="nsew", padx=(10, 0), pady=4)

    out_scroll = ttk.Scrollbar(out_frame, orient="vertical")
    out = tk.Text(out_frame, wrap="word", yscrollcommand=out_scroll.set, width=48, height=28)
    out_scroll.config(command=out.yview)

    # Optional tags you already use
    out.tag_configure("blue_text",  foreground="#1f6feb")
    out.tag_configure("black_text", foreground="#000000")

    # Layout inside frame
    out.grid(row=0, column=0, sticky="nsew")
    out_scroll.grid(row=0, column=1, sticky="ns")
    out_frame.grid_rowconfigure(0, weight=1)
    out_frame.grid_columnconfigure(0, weight=1)

    # === Status label (put above or below output—your choice). Here below buttons:
    status_lbl = ttk.Label(root, text="", font=("Segoe UI", 10, "bold"))
    status_lbl.grid(row=14, column=0, columnspan=3, sticky="w", pady=(8, 2))

    # (Optional) autosize window now that output exists
    win.update_idletasks()
    win.geometry(f"{win.winfo_reqwidth()}x{win.winfo_reqheight()}")

    # === Enable/Disable helpers
    def set_controls(state: str):
        for trio in button_refs:
            for b in trio:
                b.config(state=state)
        btn_back.config(state=state)  # <- you had a small bug setting command here

    # === Your handlers (unchanged, but consider calling out.see('end') after inserts)
    def do_upload(index: int, slot: str, file_flag: bool):
        nonlocal path_var
        button_refs[index][0].config(state="disabled")
        button_refs[index][1].config(state="disabled")
        send_command(slot)
        file_address = path_var.get()
        file_name = os.path.basename(file_address)
        file_name = file_name.split('.')
        file_name = file_name[0]
        with open(file_address) as file:
            if file_flag:
                string = file_command_encoder(file.read())
            else:
                string = file.read()
            # send file date
            #command = str(len(string).to_bytes(1, 'big'))[2]
            command = chr(len(string))
            send_command(command)
            send_data(string)
            # send file name
            command = chr(len(file_name))
            send_command(command)
            send_data(file_name)
            receive_ack()
        button_refs[index][0].config(state="disabled")
        button_refs[index][1].config(state="disabled")
        button_refs[index][2].config(state="normal")
        # set_controls("normal")

    def do_play(slot: str, label: str):
        nonlocal status_lbl
        #set_controls("disabled")
        send_command(slot)
        status_lbl.config(text=f"{label}, Please wait.")
        while True:
            win.update()
            opcode = receive_char()
            opcode_dict = {
                '1': "inc_lcd",
                '2': "dec_lcd",
                '3': "rra_lcd",
                '4': "set_delay",
                '5': "clear_lcd",
                '6': "servo_deg",
                '7': "servo_scan",
                '8': "msp sleep"
            }
            out.insert("end", f"Playing Opcode {opcode}: ", "blue_text")
            out.insert("end", f"({opcode_dict[opcode]})\n", "black_text")
            out.see("end")  # auto-scroll

            if opcode == '6':
                distance = int(receive_data())
                angle = int(receive_data())
                out.insert("end", f"Distance: {distance} [cm], Angle: {angle} [deg]\n")
                out.see("end")

            elif opcode == '7':
                distance_arr = []
                angle1 = int(receive_data())
                angle2 = int(receive_data())
                while True:
                    win.update()
                    distance = int(receive_data())
                    if distance == 500:
                        break
                    distance_arr.append(distance)
                degree_arr = [
                    round(float(angle1) + i * (float(angle2) - float(angle1)) / (len(distance_arr) - 1), 1)
                    for i in range(len(distance_arr))
                ]
                out.insert("end", f"Distance array: {distance_arr}\n")
                out.insert("end", f"Degree array: {degree_arr}\n")
                out.see("end")
                #draw_scanner_map(distance_arr, degree_arr)

            elif opcode == '8':
                break

        #set_controls("normal")

    attach_dict = {
        0:"AB", 1:"CD", 2:"EF", 3:"GH", 4:"IJ",
        5:"KL", 6:"MN", 7:"OP", 8:"QR", 9:"ST",
    }
    for i, button in enumerate(button_refs):
        button[0].config(command=lambda v=i: do_upload(v, slot=attach_dict[v][0], file_flag=True))
        button[1].config(command=lambda v=i: do_upload(v, slot=attach_dict[v][0], file_flag=False))
        button[2].config(command=lambda v=i: do_play(attach_dict[v][1], f"Playing {v+1}"))

    def update_status():
        global ACK
        status_map = {
            '1': "File/Script 1 Transferred",
            '2': "File/Script 2 Transferred",
            '3': "File/Script 3 Transferred",
            '4': "File/Script 4 Transferred",
            '5': "File/Script 5 Transferred",
            '6': "File/Script 6 Transferred",
            '7': "File/Script 7 Transferred",
            '8': "File/Script 8 Transferred",
            '9': "File/Script 9 Transferred",
            '0': "File/Script 10 Transferred",
        }
        status_lbl.config(text=status_map.get(ACK, ""))
        win.after(250, update_status)

    update_status()
    win.grab_set(); win.wait_window()



def light_calibrate():
    # send_command('3')
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

    # def calibrate():
    #     LDR_calibrate_arr = []
    #     btn_back.config(state="disabled")
    #     btn_cal.config(state="disabled")
    #     btn_cal.config(text="Press PB0 to calibrate")
    #     out_lbl.config(text="")
    #     send_command('X')
    #     btn_back.config(state="normal")
    #     btn_cal.config(text="Press PB0 10 Times")


    # btn_cal.config(command=calibrate)
    btn_cal.config(command=lambda: (send_command('X'), win.destroy()))
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
    root.title("DCS Final Project - Omer Pintel & Romi Lustig")
    root.geometry("980x640")

    # Top bar
    top = ttk.Frame(root, padding=(10,8))
    top.pack(side="top", fill="x")
    ttk.Label(top, text="Light Source & Object Proximity Detector System", font=("Segoe UI", 16, "bold")).pack(side="left")
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
    home_desc = ttk.Label(content,
        text=(
        "This interface was designed by Omer Pintel and Romi Lustig as part of\nour DCS Final Project.\n\n"
        "Through this system you can:\n"
        " • Detect and visualize nearby objects using ultrasonic scanning\n"
        " • Measure distances at specific angles with the telemeter\n"
        " • Identify and track light sources in your environment\n"
        " • Combine object and light detection\n"
        " • Upload, store, and play custom scripts on the MSP430\n"
        " • Calibrate the light sensors for precise measurements\n\n"
        "Use the navigation panel on the left to get started."),font=("Segoe UI", 12))
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
    ttk.Button(nav, text="📝  File/Script Mode", width=28, style="Nav.TButton",
               command=file_mode).pack(anchor="w", pady=8)
    ttk.Button(nav, text="⚙️💡  Light Calibrate", width=28, style="Nav.TButton",
               command=light_calibrate).pack(anchor="w", pady=8)



    def on_exit():
        try:
            send_command('q')
        except Exception:
            pass
        root.destroy()

    ttk.Button(nav, text="Exit", width=28, style="Nav.TButton",
               command=on_exit).pack(anchor="w", pady=(12, 0))
    # Perform the same startup handshake (unchanged behavior)
    try:
        init_uart()
        init_calibrate()
        status_var.set("Connected to MSP")
    except Exception as e:
        status_var.set(f"Startup issue: {e}")
        messagebox.showerror("Startup", f"Startup Failed.\n\n{e}")

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