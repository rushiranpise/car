import time
import random
import psycopg2


PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "2710",
}


VEHICLE_IDS = [
    "IntelliCart-01",
    "IntelliCart-02",
    "IntelliCart-03",
    "IntelliCart-04",
    "IntelliCart-05",
    "IntelliCart-06",
]

ROWS_PER_VEHICLE = 60   # history per vehicle (1 row/sec ≈ 1 minute)


def ensure_table(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vehicle_telemetry (
      id SERIAL PRIMARY KEY,
      ts DOUBLE PRECISION,
      vehicle_id TEXT,
      speed DOUBLE PRECISION,
      raw_speed DOUBLE PRECISION,
      distance DOUBLE PRECISION,
      line_l INTEGER,
      line_m INTEGER,
      line_r INTEGER,
      motion TEXT,
      line_state TEXT,
      obstacle BOOLEAN,
      cpu_temp DOUBLE PRECISION,
      line_track BOOLEAN,
      avoid_obstacles BOOLEAN,
      color_follow BOOLEAN,
      color_detect BOOLEAN,
      face_detect BOOLEAN
    )
    """)
    conn.commit()
    cur.close()


def generate_row(now_ts, vehicle_id, idx):
    """
    Generate one realistic telemetry row.
    - now_ts: base timestamp (float, epoch seconds)
    - vehicle_id: e.g. 'IntelliCart-01'
    - idx: row index; we offset ts backwards using this
    """
    # Make time go backwards so older rows are in the past
    ts = now_ts - (ROWS_PER_VEHICLE - idx)  # roughly one second apart

    # Choose a motion state
    motion_choices = ["stop", "forward", "left", "right"]
    motion = random.choices(
        motion_choices, weights=[1, 5, 2, 2], k=1
    )[0]

    # Speed logic
    if motion == "stop":
        speed = random.uniform(0, 5)
    else:
        speed = random.uniform(10, 80)  # IntelliCart moving
    raw_speed = speed + random.uniform(-3, 3)

    # Modes setup (slightly different behavior per vehicle)
    line_track = (vehicle_id in ["IntelliCart-01", "IntelliCart-02"]) and random.random() < 0.7
    avoid_obstacles = (vehicle_id in ["IntelliCart-03", "IntelliCart-04"]) and random.random() < 0.7
    color_follow = (vehicle_id == "IntelliCart-05") and random.random() < 0.5
    color_detect = color_follow or random.random() < 0.2
    face_detect = random.random() < 0.1

    # Line sensors based on state
    if line_track:
        if motion == "forward":
            line_l, line_m, line_r = 0, 1, 0
            line_state = "forward"
        elif motion == "left":
            line_l, line_m, line_r = 1, 0, 0
            line_state = "left"
        elif motion == "right":
            line_l, line_m, line_r = 0, 0, 1
            line_state = "right"
        else:
            line_l, line_m, line_r = 0, 0, 0
            line_state = "stop"
    else:
        # No line tracking → mostly zeros
        line_l = 1 if random.random() < 0.05 else 0
        line_m = 1 if random.random() < 0.05 else 0
        line_r = 1 if random.random() < 0.05 else 0
        line_state = "stop"

    # Distance & obstacle
    # When avoid_obstacles / moving → sometimes close, sometimes far
    if avoid_obstacles or motion != "stop":
        if random.random() < 0.2:
            distance = random.uniform(5, 25)   # close obstacle
        else:
            distance = random.uniform(40, 150) # far / safe
    else:
        distance = random.uniform(60, 200)

    obstacle = distance < 35  # treat <35 cm as "obstacle"

    # CPU temp (Pi-like)
    cpu_temp = random.uniform(40, 75)

    return dict(
        ts=ts,
        vehicle_id=vehicle_id,
        speed=speed,
        raw_speed=raw_speed,
        distance=distance,
        line_l=line_l,
        line_m=line_m,
        line_r=line_r,
        motion=motion,
        line_state=line_state,
        obstacle=obstacle,
        cpu_temp=cpu_temp,
        line_track=line_track,
        avoid_obstacles=avoid_obstacles,
        color_follow=color_follow,
        color_detect=color_detect,
        face_detect=face_detect,
    )


def insert_rows(conn, rows):
    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO vehicle_telemetry (
          ts, vehicle_id, speed, raw_speed, distance,
          line_l, line_m, line_r,
          motion, line_state, obstacle, cpu_temp,
          line_track, avoid_obstacles, color_follow, color_detect, face_detect
        )
        VALUES (
          %(ts)s, %(vehicle_id)s, %(speed)s, %(raw_speed)s, %(distance)s,
          %(line_l)s, %(line_m)s, %(line_r)s,
          %(motion)s, %(line_state)s, %(obstacle)s, %(cpu_temp)s,
          %(line_track)s, %(avoid_obstacles)s, %(color_follow)s,
          %(color_detect)s, %(face_detect)s
        )
    """, rows)
    conn.commit()
    cur.close()


def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**PG_CONFIG)
    ensure_table(conn)

    now_ts = time.time()
    all_rows = []

    for vid in VEHICLE_IDS:
        print(f"Generating data for {vid}...")
        for i in range(ROWS_PER_VEHICLE):
            row = generate_row(now_ts, vid, i)
            all_rows.append(row)

    print(f"Inserting {len(all_rows)} rows into vehicle_telemetry...")
    insert_rows(conn, all_rows)
    conn.close()
    print("Done. You can now run central_dashboard.py and see 6 vehicles.")


if __name__ == "__main__":
    main()
    print("Done!")
