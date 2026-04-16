from flask import Flask, render_template, request
import requests
import time
import random
from requests.adapters import Retry, HTTPAdapter

app = Flask(__name__)


# -------------------------------
# SESSION
# -------------------------------
def create_session(cookie):
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)

    session.headers.update({
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0",
        "origin": "https://online.vtu.ac.in",
        "referer": "https://online.vtu.ac.in/",
        "cookie": cookie
    })

    return session


# -------------------------------
# FETCH COURSE + ENRICH LECTURES
# -------------------------------
def fetch_course_data(cookie, course_slug):
    session = create_session(cookie)

    url = f"https://online.vtu.ac.in/api/v1/student/my-courses/{course_slug}"

    res = session.get(url)

    if res.status_code == 401:
        return None, "expired"

    if not res.ok:
        return None, "error"

    data = res.json()["data"]

    # 🔥 Enrich each lecture with extra API
    for lesson in data["lessons"]:
        for lec in lesson["lectures"]:
            lecture_id = lec["id"]

            lec_url = f"https://online.vtu.ac.in/api/v1/student/my-courses/{course_slug}/lectures/{lecture_id}"

            lec_res = session.get(lec_url)

            if lec_res.status_code == 401:
                return None, "expired"

            if lec_res.ok:
                lec_data = lec_res.json()["data"]

                # duration → minutes
                try:
                    h, m, s = map(
                        int, lec_data["duration"].split()[0].split(":"))
                    total_seconds = h * 3600 + m * 60 + s
                    lec["duration_minutes"] = round(total_seconds / 60)
                except:
                    lec["duration_minutes"] = 0

                lec["percent"] = lec_data.get("percent", 0)

            else:
                lec["duration_minutes"] = 0
                lec["percent"] = 0

    return data, None


# -------------------------------
# COMPLETE LOGIC
# -------------------------------
def get_duration(session, course, lecture_id):
    url = f"https://online.vtu.ac.in/api/v1/student/my-courses/{course}/lectures/{lecture_id}"

    res = session.get(url)

    if res.status_code == 401:
        return None, "unauthorized"

    if not res.ok:
        return None, "error"

    data = res.json()["data"]

    try:
        h, m, s = map(int, data["duration"].split()[0].split(":"))
        return h * 3600 + m * 60 + s, None
    except:
        return 0, None


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        cookie = request.form.get("cookie")
        course = request.form.get("course")

        data, err = fetch_course_data(cookie, course)

        if err == "expired":
            return "⚠ Cookie expired. Refresh and try again."

        if not data:
            return "Failed to fetch data"

        return render_template("dashboard.html", data=data, request=request)

    return render_template("index.html")


@app.route("/complete", methods=["POST"])
def complete():
    cookie = request.form.get("cookie")
    course = request.form.get("course")
    lecture_id = request.form.get("lecture_id")

    session = create_session(cookie)

    total_seconds, err = get_duration(session, course, lecture_id)

    if err == "unauthorized":
        return {"status": "expired"}

    post_url = f"https://online.vtu.ac.in/api/v1/student/my-courses/{course}/lectures/{lecture_id}/progress"

    current = 0

    while current < total_seconds:
        step = min(60, total_seconds - current)

        res = session.post(post_url, json={
            "current_time_seconds": current,
            "total_duration_seconds": total_seconds,
            "seconds_just_watched": step
        })

        if res.status_code == 401:
            return {"status": "expired"}

        current += step
        time.sleep(random.uniform(2, 4))  # safer timing

    return {"status": "done"}


if __name__ == "__main__":
    app.run(debug=True)
