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

To do this automatically, add it to your `~/.bashrc` after the `/opt/ros/lyrical/setup.bash` line:

```bash
echo "source ~/ws/ur/install/setup.bash" >> ~/.bashrc
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

1. Terminal 1 (driver):
   ```bash
   ros2 launch ur7e_robotiq_control start_robot.launch.py robot_serial:=<SERIAL>
   ```
2. On the pendant, run the `ros_control` program (it contains a single **External Control** node).
   The driver log shows `Robot connected to reverse interface. Ready to receive control commands.`
3. Terminal 2 (MoveIt):
   ```bash
   ros2 launch ur7e_robotiq_moveit_config moveit.launch.py
   ```

Add `use_gripper:=false` to step 1 to run the arm without controlling the gripper.
Only run one robot (real or simulated) per network/`ROS_DOMAIN_ID` at a time.

### One-time robot setup (per arm)

On the teach pendant (PolyScope X 10.13):

1. **Services:** ☰ → Settings → Security → Services (unlock with the admin password): enable
   *Primary Client Interface* and *Real-Time Data Exchange (RTDE)*.
2. **External Control URCapX** (lets ROS move the arm): install
   [`external-control-1.2.1.urcapx`](https://github.com/UniversalRobots/Universal_Robots_ExternalControl_URCapX/releases)
   from a USB stick via ☰ → System Manager → URCaps → **+URCap**. After the reboot, open the
   **External Control** application and set the host IP to `192.168.56.1`. Create and save a
   program `ros_control` containing only an **External Control** node.
3. **Tool Comm Forwarder URCapX** (lets ROS talk to the gripper through the wrist connector):
   install [`tool-comm-forwarder-1.0.0.urcapx`](https://github.com/UniversalRobots/Universal_Robots_ToolComm_Forwarder_URCapX/releases)
   the same way, then enable forwarding in its application screen. Make sure port 54321 isn't
   blocked under ☰ → Settings → Security → General → Inbound Connections.
   Don't install the Robotiq URCapX: it conflicts with ROS controlling the gripper.
4. **Calibration** (once per arm): with the robot on, run
   ```bash
   ros2 launch ur_calibration calibration_correction.launch.py robot_ip:=192.168.56.101 \
     target_filename:=$HOME/ur7e_<SERIAL>.yaml
   ```
   and add the file to `ur7e_robotiq_control/config/calibration/`. (The apt `ur_calibration`
   for Lyrical fails to connect to PolyScope X; build it from the
   [UR driver source](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver) if needed.)

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
- Arm controllers: ur_robot_driver's own `config/ur_controllers.yaml` (used unchanged)
