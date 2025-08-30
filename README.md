# DCS\_Final\_Project

Final Project for DCS - using CCS (C source and headers files) and Pycharm (Python file).



systemReadMe.txt

=================



This document provides an overview of the source code files, their purposes, 

and a short explanation of the functions contained in each file.



------------------------------------------------------------

1\. main.c

------------------------------------------------------------

\- \*\*Purpose\*\*: Main entry point of the MSP430 program. Implements the finite state 

&nbsp; machine (FSM) that controls different application modes such as object detection, 

&nbsp; telemeter, light detection, combined light+object detection, file/script handling, 

&nbsp; and calibration.

\- \*\*Functions\*\*:

&nbsp; - `main(void)`: Initializes system, LCD, and manages program flow based on `state` 

&nbsp;   (state0–state7). Each state activates a specific application mode.



------------------------------------------------------------

2\. api.c / api.h

------------------------------------------------------------

\- \*\*Purpose\*\*: Application Programming Interface layer. Provides higher-level 

&nbsp; functional APIs for the application logic to interact with hardware functions.

\- \*\*Functions\*\*:

&nbsp; - `object\_detector()`: Handles ultrasonic object detection logic.

&nbsp; - `telemeter()`: Measures distance at a given angle using servo + ultrasonic sensor.

&nbsp; - `light\_detector()`: Manages detection of light sources with LDRs.

&nbsp; - `light\_object\_detector()`: Combines light and object detection modes.

&nbsp; - `file\_script\_fsm()`: Executes a file/script-driven state machine.

&nbsp; - `light\_calibration()`: Runs calibration process for LDR sensors.

&nbsp; - `move\_servo(int)`: Moves servo to a given angle by generating PWM signal.

&nbsp; - `servo\_scan(int, int, int)`: Performs scanning across angles with servo motor.

&nbsp; - `meas\_and\_send\_distance()`, `meas\_and\_send\_ldr()`, `calc\_and\_send\_angle(int)`: 

&nbsp;   Measurement and communication functions to PC.

&nbsp; - Utility functions: `lcd\_puts`, `flash\_write`, `play\_script`, etc.



------------------------------------------------------------

3\. halGPIO.c / halGPIO.h

------------------------------------------------------------

\- \*\*Purpose\*\*: Hardware Abstraction Layer (HAL). Provides direct control over GPIO, 

&nbsp; timers, ADC, UART, and interrupt service routines (ISRs).

\- \*\*Functions\*\*:

&nbsp; - GPIO setup/config functions: `sysConfig()`, `GPIOconfig()`, etc.

&nbsp; - Servo PWM functions: `pwmOutServoConfig()`, `disable\_timerA1()`.

&nbsp; - Ultrasonic functions: `pwmOutTrigConfig()`, `TIMER\_A0\_config\_for\_ultrasonic()`.

&nbsp; - Flash memory write functions: `write\_flash\_char`, `init\_flash\_write`, etc.

&nbsp; - UART communication ISRs: `USCI0RX\_ISR` (RX handling), `USCI0TX\_ISR` (TX handling).

&nbsp; - Timer ISRs: `Timer\_1\_ISR`, `Timer\_2\_ISR` for capture/compare operations.

&nbsp; - ADC ISR: `adc\_inter()` for sampling LDR sensors.



------------------------------------------------------------

4\. bsp.c / bsp\_msp430x2xx.h

------------------------------------------------------------

\- \*\*Purpose\*\*: Board Support Package (BSP). Defines microcontroller hardware mappings, 

&nbsp; pin assignments, timer/ADC macros, and low-level hardware configuration.

\- \*\*Content\*\*:

&nbsp; - Pin mapping for LCD, LDR sensors, ultrasonic echo/trigger, servo PWM, buttons.

&nbsp; - Timer macros for Timer\_A0 and Timer\_A1 registers.

&nbsp; - ADC configuration macros (`ADC10CTL0`, `ADC10MEM`, etc.).

&nbsp; - UART pin macros (TXD/RXD).

&nbsp; - ServoPort, TelePort, LCD port configurations.



------------------------------------------------------------

5\. app.h

------------------------------------------------------------

\- \*\*Purpose\*\*: Application-level enumerations and state definitions.

\- \*\*Content\*\*:

&nbsp; - Defines FSM states (`state0`–`state9`).

&nbsp; - Enumerations for script handling, pushbutton states, telemeter states, 

&nbsp;   object detector states, light detector states, calibration states, 

&nbsp;   and power modes (`mode0`–`mode4`).



------------------------------------------------------------

6\. Python main.py (PC Interface)

------------------------------------------------------------

\- \*\*Purpose\*\*: Provides a GUI (Tkinter + Matplotlib) for interacting with the MSP430 system. 

&nbsp; Handles UART communication, visualization of distance/light maps, calibration, 

&nbsp; and file/script upload.

\- \*\*Functions\*\*:

&nbsp; - Communication: `init\_uart()`, `send\_command()`, `send\_data()`, `receive\_data()`.

&nbsp; - Calibration: `init\_calibrate()`, `expand\_calibration\_array()`, 

&nbsp;   `save\_calibration\_values()`.

&nbsp; - Measurement: `measure\_two\_ldr\_samples()`, `find\_fitting\_index()`.

&nbsp; - Visualization: `draw\_scanner\_map()`, `draw\_scanner\_map\_lights()`.

&nbsp; - GUIs: `objects\_detector()`, `telemeter()`, `lights\_detector()`, 

&nbsp;   `light\_objects\_detector()`, `file\_mode()`, `light\_calibrate()`.

&nbsp; - `main()`: Builds and runs the main GUI window.



------------------------------------------------------------



Summary:

\- \*\*main.c\*\*: High-level FSM controlling system operation.

\- \*\*api.c/h\*\*: Functional API layer for object, telemeter, light, script, servo.

\- \*\*halGPIO.c/h\*\*: Hardware drivers + ISRs for GPIO, timers, ADC, UART, flash.

\- \*\*bsp.c / bsp\_msp430x2xx.h\*\*: Board-level pin and peripheral mapping.

\- \*\*app.h\*\*: FSM states and enumerations.

\- \*\*main.py\*\*: PC-side GUI for visualization, calibration, and interaction.



