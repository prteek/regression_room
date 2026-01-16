
import os
import glob
import requests
import pandas as pd
import duckdb
import time
# ==== YOU SET THESE ====
DOCS_DIR = r"C:\Users\Jeremy L\Desktop\jolpica-f1-main\docs\endpoints"
SEASON = "2025"          # or "2024"
DB_PATH = "f1.duckdb"
CSV_DIR = "f1_csv"
LIMIT = 1000             # pagination page size
# =======================

BASE = "https://api.jolpi.ca/ergast/f1"
os.makedirs(CSV_DIR, exist_ok=True)

session = requests.Session()


def fetch_page(endpoint: str, limit: int, offset: int) -> dict:
    url = f"{BASE}/{endpoint}/"

    while True:
        r = session.get(url, params={"limit": limit, "offset": offset}, timeout=60)

        if r.status_code == 429:
            # rate limited – wait and retry
            print("Rate limited. Sleeping 2 seconds...")
            time.sleep(2)
            continue

        r.raise_for_status()
        return r.json()


def fetch_all(endpoint: str, limit: int = 1000) -> list[dict]:
    pages = []
    offset = 0

    first = fetch_page(endpoint, limit, offset)
    pages.append(first)

    mr = first.get("MRData", {})
    total = int(mr.get("total", 0))

    offset += limit
    while offset < total:
        pages.append(fetch_page(endpoint, limit, offset))
        offset += limit

        # be nice to the API
        time.sleep(0.25)

    return pages


# -------------------------
# Flatteners (one per endpoint)
# -------------------------

def flat_circuits(page_json):
    out = []
    for c in page_json["MRData"]["CircuitTable"]["Circuits"]:
        loc = c.get("Location", {})
        out.append({
            "circuitId": c.get("circuitId"),
            "circuitName": c.get("circuitName"),
            "url": c.get("url"),
            "lat": loc.get("lat"),
            "long": loc.get("long"),
            "locality": loc.get("locality"),
            "country": loc.get("country"),
        })
    return out

def flat_constructors(page_json):
    out = []
    for c in page_json["MRData"]["ConstructorTable"]["Constructors"]:
        out.append({
            "constructorId": c.get("constructorId"),
            "name": c.get("name"),
            "nationality": c.get("nationality"),
            "url": c.get("url"),
        })
    return out

def flat_drivers(page_json):
    out = []
    for d in page_json["MRData"]["DriverTable"]["Drivers"]:
        out.append({
            "driverId": d.get("driverId"),
            "permanentNumber": d.get("permanentNumber"),
            "code": d.get("code"),
            "givenName": d.get("givenName"),
            "familyName": d.get("familyName"),
            "dateOfBirth": d.get("dateOfBirth"),
            "nationality": d.get("nationality"),
            "url": d.get("url"),
        })
    return out

def flat_seasons(page_json):
    out = []
    for s in page_json["MRData"]["SeasonTable"]["Seasons"]:
        out.append({
            "season": s.get("season"),
            "url": s.get("url"),
        })
    return out

def flat_status(page_json):
    out = []
    for s in page_json["MRData"]["StatusTable"]["Status"]:
        out.append({
            "statusId": s.get("statusId"),
            "status": s.get("status"),
        })
    return out

def flat_races(page_json):
    out = []
    for r in page_json["MRData"]["RaceTable"]["Races"]:
        c = r.get("Circuit", {})
        loc = c.get("Location", {})
        out.append({
            "season": r.get("season"),
            "round": r.get("round"),
            "raceName": r.get("raceName"),
            "date": r.get("date"),
            "time": r.get("time"),
            "url": r.get("url"),
            "circuitId": c.get("circuitId"),
            "circuitName": c.get("circuitName"),
            "locality": loc.get("locality"),
            "country": loc.get("country"),
        })
    return out

def flat_qualifying(page_json):
    out = []
    for race in page_json["MRData"]["RaceTable"]["Races"]:
        for q in race.get("QualifyingResults", []):
            out.append({
                "season": race.get("season"),
                "round": race.get("round"),
                "raceName": race.get("raceName"),
                "driverId": q["Driver"].get("driverId"),
                "constructorId": q["Constructor"].get("constructorId"),
                "number": q.get("number"),
                "position": q.get("position"),
                "Q1": q.get("Q1"),
                "Q2": q.get("Q2"),
                "Q3": q.get("Q3"),
            })
    return out

def flat_results(page_json):
    out = []
    for race in page_json["MRData"]["RaceTable"]["Races"]:
        for res in race.get("Results", []):
            out.append({
                "season": race.get("season"),
                "round": race.get("round"),
                "raceName": race.get("raceName"),
                "driverId": res["Driver"].get("driverId"),
                "constructorId": res["Constructor"].get("constructorId"),
                "grid": res.get("grid"),
                "position": res.get("position"),
                "positionText": res.get("positionText"),
                "points": res.get("points"),
                "status": res.get("status"),
                "laps": res.get("laps"),
                "time": (res.get("Time") or {}).get("time"),
                "milliseconds": (res.get("Time") or {}).get("millis"),
                "fastestLapRank": (res.get("FastestLap") or {}).get("rank"),
                "fastestLapTime": ((res.get("FastestLap") or {}).get("Time") or {}).get("time"),
                "fastestLapSpeed": ((res.get("FastestLap") or {}).get("AverageSpeed") or {}).get("speed"),
            })
    return out

def flat_sprint(page_json):
    out = []
    for race in page_json["MRData"]["RaceTable"]["Races"]:
        for res in race.get("SprintResults", []):
            out.append({
                "season": race.get("season"),
                "round": race.get("round"),
                "raceName": race.get("raceName"),
                "driverId": res["Driver"].get("driverId"),
                "constructorId": res["Constructor"].get("constructorId"),
                "grid": res.get("grid"),
                "position": res.get("position"),
                "positionText": res.get("positionText"),
                "points": res.get("points"),
                "status": res.get("status"),
                "laps": res.get("laps"),
                "time": (res.get("Time") or {}).get("time"),
                "milliseconds": (res.get("Time") or {}).get("millis"),
            })
    return out

def flat_laps(page_json):
    out = []
    for race in page_json["MRData"]["RaceTable"]["Races"]:
        for lap in race.get("Laps", []):
            lap_num = lap.get("number")
            for t in lap.get("Timings", []):
                out.append({
                    "season": race.get("season"),
                    "round": race.get("round"),
                    "raceName": race.get("raceName"),
                    "lap": lap_num,
                    "driverId": t.get("driverId"),
                    "position": t.get("position"),
                    "time": t.get("time"),
                })
    return out

def flat_pitstops(page_json):
    out = []
    for race in page_json["MRData"]["RaceTable"]["Races"]:
        for p in race.get("PitStops", []):
            out.append({
                "season": race.get("season"),
                "round": race.get("round"),
                "raceName": race.get("raceName"),
                "driverId": p.get("driverId"),
                "stop": p.get("stop"),
                "lap": p.get("lap"),
                "time": p.get("time"),
                "duration": p.get("duration"),
                "milliseconds": p.get("milliseconds"),
            })
    return out

def flat_driver_standings(page_json):
    out = []
    st = page_json["MRData"]["StandingsTable"]
    for sl in st.get("StandingsLists", []):
        season = sl.get("season")
        round_ = sl.get("round")
        for d in sl.get("DriverStandings", []):
            out.append({
                "season": season,
                "round": round_,
                "position": d.get("position"),
                "positionText": d.get("positionText"),
                "points": d.get("points"),
                "wins": d.get("wins"),
                "driverId": (d.get("Driver") or {}).get("driverId"),
                "constructors": ",".join([c.get("constructorId") for c in d.get("Constructors", []) if c.get("constructorId")]),
            })
    return out

def flat_constructor_standings(page_json):
    out = []
    st = page_json["MRData"]["StandingsTable"]
    for sl in st.get("StandingsLists", []):
        season = sl.get("season")
        round_ = sl.get("round")
        for c in sl.get("ConstructorStandings", []):
            out.append({
                "season": season,
                "round": round_,
                "position": c.get("position"),
                "positionText": c.get("positionText"),
                "points": c.get("points"),
                "wins": c.get("wins"),
                "constructorId": (c.get("Constructor") or {}).get("constructorId"),
            })
    return out

FLATTENERS = {
    "circuits": flat_circuits,
    "constructors": flat_constructors,
    "drivers": flat_drivers,
    "seasons": flat_seasons,
    "status": flat_status,
    "races": flat_races,
    "qualifying": flat_qualifying,
    "results": flat_results,
    "sprint": flat_sprint,
    "laps": flat_laps,
    "pitstops": flat_pitstops,
    "driverStandings": flat_driver_standings,
    "constructorStandings": flat_constructor_standings,
}

# Map doc filename -> API endpoint path (season-scoped)
DOC_TO_API = {
    "circuits": f"{SEASON}/circuits",
    "constructors": f"{SEASON}/constructors",
    "drivers": f"{SEASON}/drivers",
    "races": f"{SEASON}",
    "qualifying": f"{SEASON}/qualifying",
    "results": f"{SEASON}/results",
    "sprint": f"{SEASON}/sprint",

    # these cannot be fetched at season level
    "laps": None,       
    "pitstops": None,   

    "driverStandings": f"{SEASON}/driverstandings",
    "constructorStandings": f"{SEASON}/constructorstandings",

    "seasons": "seasons",
    "status": "status",
}


def discover_docs(docs_dir: str):
    md_files = glob.glob(os.path.join(docs_dir, "*.md"))
    names = [os.path.splitext(os.path.basename(p))[0] for p in md_files]
    return [n for n in names if n in DOC_TO_API and n in FLATTENERS]

def get_rounds_for_season(season: str) -> list[str]:
    # /{season}/ returns RaceTable.Races with round numbers
    pages = fetch_all(f"{season}", limit=1000)
    rounds = []
    for pj in pages:
        for r in pj["MRData"]["RaceTable"]["Races"]:
            rounds.append(r["round"])
    # de-dupe + sort as ints
    rounds = sorted(set(rounds), key=lambda x: int(x))
    return rounds


def main():
    endpoints = list(DOC_TO_API.keys())

    con = duckdb.connect(DB_PATH)

    for name in endpoints:
        api_endpoint = DOC_TO_API[name]
        flattener = FLATTENERS[name]
        
        if name in ("laps", "pitstops"):
            rounds = get_rounds_for_season(SEASON)
            pages = []
            for rd in rounds:
                pages.extend(fetch_all(f"{SEASON}/{rd}/{name}", limit=LIMIT))
        else:
            pages = fetch_all(api_endpoint, limit=LIMIT)

        rows = []
        for pj in pages:
            rows.extend(flattener(pj))

        df = pd.DataFrame(rows)
        table = name.lower()

        # write to duckdb
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.register("df_view", df)
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM df_view")
        con.unregister("df_view")

        # export csv
        csv_path = os.path.join(CSV_DIR, f"{table}_{SEASON}.csv" if (api_endpoint is not None and api_endpoint.startswith(SEASON)) else f"{table}.csv")
        df.to_csv(csv_path, index=False)
        print(f"  -> {len(df):,} rows | {csv_path}")

    con.close()
    print(f"\nDone. DuckDB: {DB_PATH} | CSVs in: {CSV_DIR}")


if __name__ == "__main__":
    main()
