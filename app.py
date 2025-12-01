#!/usr/bin/env python3
import os
import threading
from time import sleep, time
import sqlite3

from flask import Flask, request, jsonify, render_template

from intellicart import Intellicart, utils
from intellicart.music import Music

try:
    from videolib import videolib
except Exception as e:
    print("Error importing videolib:", e)
    raise

# Try to close any previous camera instance
try:
    videolib.camera_close()
    sleep(0.2)
except Exception:
    pass

# ===== SQLite setup =====
DB_PATH = os.path.join(os.path.dirname(__file__), "telemetry.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS telemetry (
  ts REAL,
  speed REAL,
  raw_speed REAL,
  distance REAL,
  line_l INTEGER,
  line_m INTEGER,
  line_r INTEGER,
  motion TEXT,
  line_state TEXT,
  obstacle INTEGER,
  cpu_temp REAL,
  line_track INTEGER,
  avoid_obstacles INTEGER,
  color_follow INTEGER,
  color_detect INTEGER,
  face_detect INTEGER
)
""")
conn.commit()


def log_telemetry_row(row):
    """Insert one telemetry sample into SQLite."""
    try:
        c = conn.cursor()
        c.execute("""
            INSERT INTO telemetry (
              ts, speed, raw_speed, distance,
              line_l, line_m, line_r,
              motion, line_state, obstacle, cpu_temp,
              line_track, avoid_obstacles, color_follow, color_detect, face_detect
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            row["ts"], row["speed"], row["raw_speed"], row["distance"],
            row["line_l"], row["line_m"], row["line_r"],
            row["motion"], row["line_state"], row["obstacle"], row["cpu_temp"],
            row["line_track"], row["avoid_obstacles"],
            row["color_follow"], row["color_detect"], row["face_detect"]
        ))
        conn.commit()
    except Exception as e:
        print("DB insert error:", e)


# ===== Robot init =====
utils.reset_mcu()
sleep(0.2)

px = Intellicart()
speed = 0                 # commanded speed
smooth_speed = 0.0        # smoothed speed for gauge
last_line_state = "stop"

# Reset camera
px.set_cam_pan_angle(0)
px.set_cam_tilt_angle(0)

LINE_TRACK_SPEED = 10
LINE_TRACK_ANGLE_OFFSET = 20

AVOID_OBSTACLES_SPEED = 40
SAFE_DISTANCE = 40        # cm (user configurable)
DANGER_DISTANCE = 20      # cm (user configurable)

COLOR_LIST = ["red", "green", "blue", "yellow", "orange", "purple"]

FOLLOW_BASE_SPEED = 30
FOLLOW_CENTER_X = 320
FOLLOW_MAX_ERR = 320
FOLLOW_NEAR_WIDTH = 220

speed_limit = 100

# Horn sound
User = os.popen('echo ${SUDO_USER:-$LOGNAME}').readline().strip()
UserHome = os.popen('getent passwd %s | cut -d: -f 6' % User).readline().strip()
music = Music()

if os.geteuid() != 0:
    print('\033[33mNote: horn sound playback usually needs sudo.\033[m')


def horn():
    _status, _result = utils.run_command('sudo killall pulseaudio')
    sound_path = os.path.join(UserHome, "picar-x", "sounds", "car-double-horn.wav")
    music.sound_play_threading(sound_path)


def get_line_status(vals):
    state = px.get_line_status(vals)
    if state == [0, 0, 0]:
        return "stop"
    if state[1] == 1:
        return "forward"
    if state[0] == 1:
        return "right"
    if state[2] == 1:
        return "left"
    return "stop"


def line_track_step():
    """Single step of line tracking."""
    global last_line_state
    vals = px.get_grayscale_data()
    st = get_line_status(vals)

    if st != "stop":
        last_line_state = st
        if st == "forward":
            px.set_dir_servo_angle(0)
            px.forward(LINE_TRACK_SPEED)
        elif st == "left":
            px.set_dir_servo_angle(LINE_TRACK_ANGLE_OFFSET)
            px.forward(LINE_TRACK_SPEED)
        elif st == "right":
            px.set_dir_servo_angle(-LINE_TRACK_ANGLE_OFFSET)
            px.forward(LINE_TRACK_SPEED)
    else:
        if last_line_state == "left":
            px.set_dir_servo_angle(-30)
            px.backward(10)
        elif last_line_state == "right":
            px.set_dir_servo_angle(30)
            px.backward(10)
        sleep(0.1)
        px.stop()


def read_cpu_temp():
    """Read CPU temperature in Celsius (Pi)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        return 0.0


# Shared state
joystick_move = {"x": 0.0, "y": 0.0}
joystick_cam = {"x": 0.0, "y": 0.0}

modes = {
    "line_track": False,
    "avoid_obstacles": False,
    "face_detect": False,
    "color_detect": False,
    "color_follow": False,
}

telemetry = {
    "speed": 0,               # smoothed speed 0–100
    "raw_speed": 0,           # unsmoothed |speed|
    "distance": 0,
    "line": [0, 0, 0],
    "motion": "stop",
    "line_state": "stop",
    "obstacle_detected": False,
    "cpu_temp": 0.0,
}

state_lock = threading.Lock()
last_log_time = 0.0  # last time we wrote a DB row

# Camera / streaming
ip = utils.get_ip()
print(f"Pi IP: {ip}")
print("Starting camera stream on http://%s:9000/mjpg" % ip)

videolib.camera_start(vflip=False, hflip=False)
videolib.display(local=False, web=True)

app = Flask(__name__, static_url_path="/static")


@app.route("/")
def index():
    """Single page: controller + telemetry."""
    return render_template("index.html",
                           stream_url=f"http://{ip}:9000/mjpg",
                           ip=ip)


@app.route("/api/move", methods=["POST"])
def api_move():
    d = request.get_json(force=True)
    with state_lock:
        joystick_move["x"] = max(-100, min(100, float(d.get("x", 0))))
        joystick_move["y"] = max(-100, min(100, float(d.get("y", 0))))
    return "", 204


@app.route("/api/camera", methods=["POST"])
def api_camera():
    d = request.get_json(force=True)
    with state_lock:
        joystick_cam["x"] = max(-100, min(100, float(d.get("x", 0))))
        joystick_cam["y"] = max(-100, min(100, float(d.get("y", 0))))
    return "", 204


@app.route("/api/modes", methods=["POST"])
def api_modes():
    d = request.get_json(force=True)
    with state_lock:
        for k in modes:
            if k in d:
                modes[k] = bool(d[k])
    return "", 204


@app.route("/api/horn", methods=["POST"])
def api_horn():
    threading.Thread(target=horn, daemon=True).start()
    return "", 204


@app.route("/api/stop", methods=["POST"])
def api_stop():
    global speed, smooth_speed
    with state_lock:
        joystick_move["x"] = 0
        joystick_move["y"] = 0
        for k in modes:
            modes[k] = False
    px.stop()
    speed = 0
    smooth_speed = 0.0
    return "", 204


@app.route("/api/settings", methods=["POST"])
def api_settings():
    global speed_limit, SAFE_DISTANCE, DANGER_DISTANCE
    d = request.get_json(force=True)
    with state_lock:
        if "speed_limit" in d:
            speed_limit = max(0, min(100, int(d["speed_limit"])))
        if "safe_distance" in d:
            new_safe = max(20, min(80, int(d["safe_distance"])))
            SAFE_DISTANCE = new_safe
            if DANGER_DISTANCE >= SAFE_DISTANCE:
                DANGER_DISTANCE = max(5, SAFE_DISTANCE - 5)
        if "danger_distance" in d:
            new_danger = max(5, min(40, int(d["danger_distance"])))
            if new_danger >= SAFE_DISTANCE:
                SAFE_DISTANCE = min(80, new_danger + 5)
            DANGER_DISTANCE = new_danger
    return "", 204


@app.route("/api/status", methods=["GET"])
def api_status():
    with state_lock:
        return jsonify({
            "speed": telemetry["speed"],
            "raw_speed": telemetry["raw_speed"],
            "distance": telemetry["distance"],
            "line": telemetry["line"],
            "modes": modes,
            "speed_limit": speed_limit,
            "motion": telemetry["motion"],
            "line_state": telemetry["line_state"],
            "obstacle_detected": telemetry["obstacle_detected"],
            "safe_distance": SAFE_DISTANCE,
            "danger_distance": DANGER_DISTANCE,
            "cpu_temp": telemetry["cpu_temp"],
        })


@app.route("/api/history", methods=["GET"])
def api_history():
    """
    Return recent telemetry history from SQLite for charts.
    ?seconds=600 → last 10 minutes (default).
    """
    secs = request.args.get("seconds", default=600, type=int)
    if secs <= 0:
        secs = 600
    if secs > 86400:
        secs = 86400  # max 24h

    cutoff = time() - secs

    try:
        c = conn.cursor()
        c.execute("""
            SELECT ts,speed,raw_speed,distance,line_l,line_m,line_r,
                   motion,line_state,obstacle,cpu_temp,
                   line_track,avoid_obstacles,color_follow,color_detect,face_detect
            FROM telemetry
            WHERE ts >= ?
            ORDER BY ts ASC
        """, (cutoff,))
        rows = c.fetchall()
    except Exception as e:
        print("DB history error:", e)
        rows = []

    history = []
    for r in rows:
        history.append({
            "ts": r[0],
            "speed": r[1],
            "raw_speed": r[2],
            "distance": r[3],
            "line": [r[4], r[5], r[6]],
            "motion": r[7],
            "line_state": r[8],
            "obstacle": bool(r[9]),
            "cpu_temp": r[10],
            "modes": {
                "line_track": bool(r[11]),
                "avoid_obstacles": bool(r[12]),
                "color_follow": bool(r[13]),
                "color_detect": bool(r[14]),
                "face_detect": bool(r[15]),
            }
        })
    return jsonify({"history": history})


def control_loop():
    global speed, smooth_speed, SAFE_DISTANCE, DANGER_DISTANCE, last_log_time
    last_face = False
    last_color = False    # for color detect
    color_index = 0
    alpha = 0.85          # smoothing factor

    while True:
        sleep(0.05)
        now = time()

        with state_lock:
            mvx = joystick_move["x"]
            mvy = joystick_move["y"]
            camx = joystick_cam["x"]
            camy = joystick_cam["y"]
            line_on = modes["line_track"]
            avoid_on = modes["avoid_obstacles"]
            face_on = modes["face_detect"]
            color_on = modes["color_detect"]
            follow_on = modes["color_follow"]
            sp_lim = speed_limit
            safe_dist = SAFE_DISTANCE
            danger_dist = DANGER_DISTANCE

        # Sensors
        try:
            line_vals = px.get_grayscale_data()
        except Exception:
            line_vals = [0, 0, 0]

        try:
            dist = px.get_distance()
        except Exception:
            dist = 0

        try:
            line_state = get_line_status(line_vals)
        except Exception:
            line_state = "stop"

        obstacle = (dist > 0 and dist < safe_dist)
        motion = "stop"

        try:
            if line_on:
                speed = LINE_TRACK_SPEED
                line_track_step()
                if line_state in ("forward", "left", "right"):
                    motion = line_state
                else:
                    motion = "stop"

            elif avoid_on:
                speed = AVOID_OBSTACLES_SPEED
                if dist >= safe_dist:
                    px.set_dir_servo_angle(0)
                    px.forward(speed)
                    motion = "forward"
                elif dist >= danger_dist:
                    px.set_dir_servo_angle(30)
                    px.forward(speed)
                    motion = "right"
                else:
                    px.set_dir_servo_angle(-30)
                    px.backward(speed)
                    motion = "backward"

            elif follow_on and color_on:
                params = getattr(videolib, "detect_obj_parameter", {})
                n = params.get("color_n", 0)
                if n and n > 0:
                    cx = params.get("color_x", FOLLOW_CENTER_X)
                    cw = params.get("color_w", 0)
                    obj_center = cx + cw / 2.0
                    err = obj_center - FOLLOW_CENTER_X

                    steer = utils.mapping(err, -FOLLOW_MAX_ERR, FOLLOW_MAX_ERR, -30, 30)
                    steer = max(-30, min(30, steer))
                    px.set_dir_servo_angle(steer)

                    if cw < FOLLOW_NEAR_WIDTH:
                        sp = min(FOLLOW_BASE_SPEED, sp_lim)
                        if sp <= 0:
                            px.stop()
                            speed = 0
                            motion = "stop"
                        else:
                            speed = sp
                            px.forward(sp)
                            motion = "forward"
                    else:
                        px.stop()
                        speed = 0
                        motion = "stop"
                else:
                    px.stop()
                    speed = 0
                    motion = "stop"

            else:
                # Manual / joystick
                steer = utils.mapping(mvx, -100, 100, -30, 30)
                px.set_dir_servo_angle(steer)
                if abs(mvy) < 5:
                    px.stop()
                    speed = 0
                    if mvx < -20:
                        motion = "left"
                    elif mvx > 20:
                        motion = "right"
                    else:
                        motion = "stop"
                else:
                    sp = int(utils.mapping(abs(mvy), 0, 100, 0, sp_lim))
                    if sp <= 0:
                        px.stop()
                        speed = 0
                        motion = "stop"
                    else:
                        speed = sp
                        if mvy > 0:
                            px.forward(sp)
                            motion = "forward"
                        else:
                            px.backward(sp)
                            motion = "backward"
                        if mvx < -20:
                            motion = "left"
                        elif mvx > 20:
                            motion = "right"

            # Camera control
            pan = utils.mapping(camx, -100, 100, -90, 90)
            tilt = utils.mapping(camy, -100, 100, -35, 65)
            px.set_cam_pan_angle(pan)
            px.set_cam_tilt_angle(tilt)

            # Face detection
            if face_on != last_face:
                videolib.face_detect_switch(face_on)
                last_face = face_on

            # Color detection cycling
            if color_on:
                if not last_color:
                    print("Color detection ON: cycling")
                    last_color = True
                videolib.color_detect(COLOR_LIST[color_index])
                color_index = (color_index + 1) % len(COLOR_LIST)
            else:
                if last_color:
                    videolib.color_detect("close")
                    last_color = False

        except Exception as e:
            print("Control loop error:", e)

        # Telemetry update + logging
        try:
            cpu_temp = read_cpu_temp()
            row = None
            log_now = False

            with state_lock:
                telemetry["distance"] = int(dist)
                telemetry["line"] = line_vals
                telemetry["line_state"] = line_state
                telemetry["motion"] = motion
                telemetry["obstacle_detected"] = bool(obstacle)

                # raw + smoothed speed
                telemetry["raw_speed"] = int(abs(speed))
                target_display = max(0.0, min(float(abs(speed)), 100.0))
                smooth_speed = alpha * smooth_speed + (1.0 - alpha) * target_display
                telemetry["speed"] = int(smooth_speed + 0.5)

                telemetry["cpu_temp"] = cpu_temp

                # Prepare row for DB logging
                line_l = int(line_vals[0]) if len(line_vals) > 0 else 0
                line_m = int(line_vals[1]) if len(line_vals) > 1 else 0
                line_r = int(line_vals[2]) if len(line_vals) > 2 else 0

                row = {
                    "ts": now,
                    "speed": telemetry["speed"],
                    "raw_speed": telemetry["raw_speed"],
                    "distance": telemetry["distance"],
                    "line_l": line_l,
                    "line_m": line_m,
                    "line_r": line_r,
                    "motion": telemetry["motion"],
                    "line_state": telemetry["line_state"],
                    "obstacle": 1 if telemetry["obstacle_detected"] else 0,
                    "cpu_temp": telemetry["cpu_temp"],
                    "line_track": 1 if modes["line_track"] else 0,
                    "avoid_obstacles": 1 if modes["avoid_obstacles"] else 0,
                    "color_follow": 1 if modes["color_follow"] else 0,
                    "color_detect": 1 if modes["color_detect"] else 0,
                    "face_detect": 1 if modes["face_detect"] else 0,
                }

                if now - last_log_time >= 1.0:
                    last_log_time = now
                    log_now = True

            if log_now and row is not None:
                log_telemetry_row(row)

        except Exception as e:
            print("Telemetry error:", e)


def main():
    threading.Thread(target=control_loop, daemon=True).start()
    print("Web UI at http://0.0.0.0:5000")
    print(f"For local network use: http://{ip}:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    try:
        main()
    finally:
        px.stop()
        
        try:
            videolib.camera_close()
        except Exception:
            pass
            
        try:
            conn.close()
        except Exception:
            pass
