from flask import Flask, render_template, request
import requests

app = Flask(__name__)


def fetch_course_data(cookie, course_slug):
    url = f"https://online.vtu.ac.in/api/v1/student/my-courses/{course_slug}"

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0",
        "origin": "https://online.vtu.ac.in",
        "referer": "https://online.vtu.ac.in/",
        "cookie": cookie
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()["data"]
    except Exception as e:
        print("Error:", e)
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        cookie = request.form.get("cookie")
        course = request.form.get("course")

        data = fetch_course_data(cookie, course)

        if not data:
            return "Failed to fetch data"

        return render_template("dashboard.html", data=data)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)