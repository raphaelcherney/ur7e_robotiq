# UR7e + Robotiq 2F-85 (ROS 2 Lyrical)

ROS 2 packages for our UR7e arm with a Robotiq 2F-85 gripper, including a MoveIt demo.
The layout follows Universal Robots' official
[`my_robot_cell` tutorial](https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/doc/ur_tutorials/my_robot_cell/doc/index.html),
so the UR documentation applies directly.

| Package | What it contains |
| --- | --- |
| `ur7e_robotiq_description` | URDF of arm + coupling + gripper (no control) and a model viewer |
| `ur7e_robotiq_control` | Starts the robot with ros2_control: real arm, or mock (simulated) hardware |
| `ur7e_robotiq_moveit_config` | MoveIt config (planning groups, poses, controllers) and launch files |

Everything else (UR driver, UR description, MoveIt) is installed from apt. The Robotiq gripper
driver isn't released for Lyrical, so it is built from source (listed in `ur7e_robotiq.repos`).

## One-time setup

The repository is private: ask to be added as a collaborator, and add an
[SSH key to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
on the machine you're using.

```bash
mkdir -p ~/ws/ur/src && cd ~/ws/ur/src
git clone git@github.com:raphaelcherney/ur7e_robotiq.git
vcs import . < ur7e_robotiq/ur7e_robotiq.repos     # Robotiq driver + serial library
cd ~/ws/ur
source /opt/ros/lyrical/setup.bash
rosdep install --from-paths src --ignore-src -y   # installs any missing apt packages
colcon build --symlink-install
```

**In every new terminal** (or `Package '...' not found` errors appear):

```bash
source ~/ws/ur/install/setup.bash
```

To do this automatically, add it to your `~/.bashrc` after the `/opt/ros/lyrical/setup.bash` line.
Also keep ROS traffic on this PC: the robot (PolyScope X) runs its own ROS 2 node that otherwise
shows up in your ROS graph and publishes on `/joint_states` too.

```bash
echo "source ~/ws/ur/install/setup.bash" >> ~/.bashrc
echo "export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST" >> ~/.bashrc
```

## MoveIt demo (no robot needed)

```bash
ros2 launch ur7e_robotiq_moveit_config demo.launch.py
```

In RViz's **MotionPlanning** panel:

- **Planning Group `ur_manipulator`**: drag the interactive marker (it sits at the gripper TCP,
  between the fingers), or pick a goal like `home` / `up` / `test_configuration`, then **Plan & Execute**.
- **Planning Group `gripper`**: pick goal state `open` or `close`, then **Plan & Execute**.

## Real robot

Our arms run **PolyScope X**. Connect the PC to the robot with an Ethernet cable. The robot is at
`192.168.56.101` and the PC must be `192.168.56.1` (netmask `255.255.255.0`).

Each arm is identified by its serial number (on the label on the arm base), which selects its
calibration file in `ur7e_robotiq_control/config/calibration/`:

| Serial | Calibration |
| --- | --- |
| 20265702158 | `ur7e_20265702158.yaml` |
| 20265702166 | not extracted yet |

By default ROS sends the robot's control program itself ("headless mode"): nothing to run on
the pendant.

1. On the pendant, put the robot in **Remote** control mode (once; it stays that way):
   tap the button in the **top-right corner** to open *Safety Overview* / *Mode Selection*,
   choose **Automatic** under **Select Operational mode** (password: factory default
   `operator`, unless your lab has changed it), then **Remote** under **Select Control mode**.
2. Power on the robot and release the brakes.
3. Terminal 1 (driver):
   ```bash
   ros2 launch ur7e_robotiq_control start_robot.launch.py robot_serial:=<SERIAL>
   ```
   The driver sends the program and the gripper activates (its fingers open and close). This
   stops the program once; the driver resends it automatically. Wait for `Gripper ready.`
4. Terminal 2 (MoveIt):
   ```bash
   ros2 launch ur7e_robotiq_moveit_config moveit.launch.py
   ```
   In RViz, keep the velocity scaling low (default 0.1) until you're confident in your motion.
   In Automatic mode the pendant speed slider is usually at 100%, so it won't slow you down.

If the program stops later (e.g. after a protective stop or e-stop), restart it from ROS:

```bash
ros2 service call /io_and_status_controller/resend_robot_program std_srvs/srv/Trigger
```

Add `use_gripper:=false` to step 3 to run the arm without controlling the gripper.
Only run one robot (real or simulated) per PC at a time.

> **Safety:** in Remote mode, nothing on the pendant marks the moment ROS takes control: the arm
> can move as soon as anyone sends a command. Keep the e-stop within reach. Automatic mode also
> changes which safety limits apply: follow your lab's rules for it. In Remote mode the pendant
> can't start programs; switch back to **Local** (same menu) to use pendant programs.

### Alternative: pendant program (Local mode)

To keep an explicit "hand control to ROS" step on the pendant, leave the robot in **Local** mode
and add `headless_mode:=false`:

1. Terminal 1:
   ```bash
   ros2 launch ur7e_robotiq_control start_robot.launch.py robot_serial:=<SERIAL> headless_mode:=false
   ```
2. On the pendant, open the `ros_control` program (it contains a single **External Control**
   node) and press play. If the External Control node is **yellow** (always the case after the
   robot reboots) or PolyScope says *"Program is not finished"*, first select the node, press
   **Update program** (the driver must be running), then play.
   The driver log shows `Robot connected to reverse interface. Ready to receive control commands.`
   The first time after starting the driver, the gripper then activates and **the program
   stops**: press play once more. After that it stays running.
3. MoveIt as above. After a protective stop, press play on the pendant.

### One-time robot setup (per arm)

On the teach pendant (PolyScope X 10.13):

1. **Services:** ☰ → Settings → Security → Services (unlock with the admin password): enable
   *Primary Client Interface* and *Real-Time Data Exchange (RTDE)*.
2. **External Control URCapX** (needed for the pendant-program alternative; headless mode
   doesn't use it): install
   [`external-control-1.2.1.urcapx`](https://github.com/UniversalRobots/Universal_Robots_ExternalControl_URCapX/releases)
   from a USB stick via ☰ → System Manager → URCaps → **+URCap**. After the reboot, open the
   **External Control** application and set the host IP to `192.168.56.1`. Create and save a
   program `ros_control` containing only an **External Control** node.
3. **Tool Comm Forwarder URCapX** (lets ROS talk to the gripper through the wrist connector):
   install [`tool-comm-forwarder-1.0.0.urcapx`](https://github.com/UniversalRobots/Universal_Robots_ToolComm_Forwarder_URCapX/releases)
   the same way, then press **Start** for it in the Application screen. Make sure port 54321
   isn't blocked under ☰ → Settings → Security → General → Inbound Connections.
4. **No Robotiq URCapX:** uninstall the Robotiq Grippers URCapX if it's installed (it takes over
   the wrist serial port), and set Application → Communication → Tool I/O → **Controlled By** to
   **User**. Then **restart the controller**: the change only takes effect after a restart.
   Check with `ros2 run ur7e_robotiq_control check_gripper_comm.py` (see Troubleshooting).
5. **Calibration** (once per arm): with the robot on, run
   ```bash
   ros2 launch ur_calibration calibration_correction.launch.py robot_ip:=192.168.56.101 \
     target_filename:=$HOME/ur7e_<SERIAL>.yaml
   ```
   and add the file to `ur7e_robotiq_control/config/calibration/`. (The apt `ur_calibration`
   for Lyrical fails to connect to PolyScope X; build it from the
   [UR driver source](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver) if needed.)

### Status (Nov 2026)

Tested on UR7e **20265702158** (PolyScope X 10.13) with the 2F-85: driver connection with its
calibration, gripper activation and open/close (direct and through MoveIt), arm trajectories,
and MoveIt planning and execution from RViz.

Known issues / not yet done:

- The first gripper activation after starting the driver stops the robot program (resent
  automatically in headless mode; with the pendant program you press play twice once). Cause: `robotiq_driver` blocks ros2_control's loop for ~2 s while
  the gripper does its activation stroke, so the arm driver sends nothing and the robot's
  External Control script exits (`Socket timed out waiting for command on reverse_socket`).
- Starting right after a robot boot (boot → driver → Update program → play) was tested and works.
- Headless mode (the default, robot in Remote) was tested: program sent, gripper activated,
  program automatically resent, gripper commands and arm trajectories OK.
- UR7e **20265702166** still needs the one-time robot setup below and its calibration file.
- The `ros_control` program on 20265702158 also has a Script node
  (`set_tool_voltage(24)`, `set_tool_communication(True, 115200, 0, 1, 1.5, 3.5)`) before the
  External Control node. It's probably not needed (the driver sets these itself), but that
  hasn't been checked.

## Troubleshooting (real robot)

How the gripper connection works: the gripper's RS-485 cable goes through the UR wrist
connector. The **Tool Comm Forwarder URCapX** on the robot exposes it on TCP port 54321, the UR
driver turns that into a virtual serial port `/tmp/ttyUR` on the PC (with `socat`), and
`robotiq_driver` talks Modbus RTU over it. The robot only powers the tool (24 V) and enables
RS-485 once the `ros_control` program has been played, so the gripper is activated then, by
`ur7e_robotiq_control/scripts/gripper_bringup.py`.

**Check the gripper connection directly** (read-only, the gripper doesn't move; stop the driver
first, and have `ros_control` played at least once since the robot booted):

```bash
ros2 run ur7e_robotiq_control check_gripper_comm.py
```

| Symptom | Cause / fix |
| --- | --- |
| `Package 'ur7e_robotiq_...' not found` | The workspace isn't sourced in this terminal: `source ~/ws/ur/install/setup.bash`. |
| `No such file or directory: /opt/ros/lyrical/share/robotiq_description/urdf/2f_85.ros2_control.xacro` | This terminal was sourced before the Robotiq packages were built into the workspace, so it finds the older apt `robotiq_description`. Run `source ~/ws/ur/install/setup.bash` again (or open a new terminal). After building **new** packages, always re-source. |
| Driver log: `socat ... Broken pipe`, `Failed to communicate with the Robotiq gripper`; `check_gripper_comm.py` says *the robot closed the connection immediately* | The forwarder can't open the wrist serial port. Uninstall the **Robotiq Grippers URCapX**, set Tool I/O **Controlled By** to **User**, then **restart the controller** (a restart is required). Also check the forwarder is **Started** in the Application screen. |
| `check_gripper_comm.py`: *cannot connect* | Forwarder not installed/started, or port 54321 blocked under Inbound Connections. |
| `check_gripper_comm.py`: *no valid reply* | Tool not powered yet: play `ros_control` once. Then check the gripper cable. |
| *"Program is not finished. Complete the yellow program-nodes..."* when pressing play | The External Control node has no program yet (normal after a robot reboot). With the driver running, select the node, press **Update program**, then play. |
| The program stops a second after you first press play; robot log says *Socket timed out waiting for command on reverse_socket* | Expected once per driver start: the gripper's activation briefly blocks the driver. Headless mode resends the program automatically; with the pendant program, press play again. |
| Gripper commands "stall" and the fingers don't move after a robot reboot | The gripper isn't really activated. `gripper_bringup` re-activates it automatically; to do it by hand: `ros2 service call /robotiq_activation_controller/reactivate_gripper std_srvs/srv/Trigger`. |
| `Could not activate the gripper` in the driver log | Fix the cause above, then restart the driver (`robotiq_driver` can't retry after a failed connection). |
| `/joint_states` has extra joints named `UR<serial>_...` | That's the robot's own ROS 2 node. Set `export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` (see setup). |
| Driver warns *dashboard server is not available* | Normal on PolyScope X. |
| Arm doesn't move, `joint_trajectory_controller` inactive | The robot program isn't running (the driver pauses arm controllers when it stops). Press play, or in headless mode call `/io_and_status_controller/resend_robot_program`. |
| Headless: *Could not resend the robot program* / nothing happens at startup | The robot isn't in Remote control mode, or isn't powered on with brakes released. |
| `ur_calibration` keeps reconnecting (*Reconnect called on a socket that is not in LostConnection state*) | Bug in the apt package for Lyrical. Build `ur_calibration` from the UR driver source. |

## Other useful commands

```bash
# Just look at the model, with joint sliders
ros2 launch ur7e_robotiq_description view_robot.launch.py

# Robot without MoveIt (simulated), e.g. to test your own controller code
ros2 launch ur7e_robotiq_control start_robot.launch.py use_mock_hardware:=true

# Re-activate the real gripper (e.g. after a fault or power cycle)
ros2 service call /robotiq_activation_controller/reactivate_gripper std_srvs/srv/Trigger

# Command the gripper directly (0.0 = open, 0.79 = closed)
# (works in simulation and on the real robot)
ros2 action send_goal /robotiq_gripper_controller/gripper_cmd \
  control_msgs/action/ParallelGripperCommand \
  "{command: {name: [robotiq_85_left_knuckle_joint], position: [0.79]}}"
```

## Where things are

- Gripper TCP offset: `ur7e_robotiq_description/urdf/ur7e_robotiq_macro.xacro` (`gripper_tcp_joint`)
- Named poses, planning groups, collision matrix: `ur7e_robotiq_moveit_config/config/ur7e_robotiq.srdf`
- Gripper controller settings: `ur7e_robotiq_control/config/robotiq_controllers.yaml`
- Per-robot calibrations: `ur7e_robotiq_control/config/calibration/`
- Real-gripper startup logic: `ur7e_robotiq_control/scripts/gripper_bringup.py` and
  `ur7e_robotiq_control/config/controller_manager_real_gripper.yaml`
- Arm controllers: ur_robot_driver's own `config/ur_controllers.yaml` (used unchanged)
