import os
import sqlalchemy
import re
from flask import Flask, jsonify, render_template, request

from cs50 import SQL
from helpers import lookup

import urllib.parse
import psycopg2
urllib.parse.uses_netloc.append("postgres")
url = urllib.parse.urlparse(os.environ["DATABASE_URL"])
conn = psycopg2.connect(
 database=url.path[1:],
 user=url.username,
 password=url.password,
 host=url.hostname,
 port=url.port
)

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL(os.environ["DATABASE_URL"])

# added during Heroku tutorial
class SQL(object):
    def __init__(self, url):
        try:
            self.engine = sqlalchemy.create_engine(url)
        except Exception as e:
            raise RuntimeError(e)
    def execute(self, text, *multiparams, **params):
        try:
            statement = sqlalchemy.text(text).bindparams(*multiparams, **params)
            result = self.engine.execute(str(statement.compile(compile_kwargs={"literal_binds": True})))
            # SELECT
            if result.returns_rows:
                rows = result.fetchall()
                return [dict(row) for row in rows]
            # INSERT
            elif result.lastrowid is not None:
                return result.lastrowid
            # DELETE, UPDATE
            else:
                return result.rowcount
        except sqlalchemy.exc.IntegrityError:
            return None
        except Exception as e:
            raise RuntimeError(e)
# # end


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Render map"""
    if not os.environ.get("API_KEY"):
        raise RuntimeError("API_KEY not set")
    return render_template("index.html", key=os.environ.get("API_KEY"))


@app.route("/articles")
def articles():
    """Look up articles for geo"""
    geo = request.args.get("geo")
    if not geo:
        raise RuntimeError("missing geo")
    all_articles = lookup(geo)
    article_list = []
    for i in range(0, 5):
        article_list.append(all_articles[i])
    return jsonify(article_list)


@app.route("/search")
def search():
    """Search for places that match query"""
    q = request.args.get("q") + "%%"
    results = db.execute("SELECT * FROM places WHERE postal_code LIKE :q OR place_name LIKE :q OR admin_code1 LIKE :q", q=q)
    return jsonify(results)


@app.route("/update")
def update():
    """Find up to 10 places within view"""

    # Ensure parameters are present
    if not request.args.get("sw"):
        raise RuntimeError("missing sw")
    if not request.args.get("ne"):
        raise RuntimeError("missing ne")

    # Ensure parameters are in lat,lng format
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("sw")):
        raise RuntimeError("invalid sw")
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("ne")):
        raise RuntimeError("invalid ne")

    # Explode southwest corner into two variables
    sw_lat, sw_lng = map(float, request.args.get("sw").split(","))

    # Explode northeast corner into two variables
    ne_lat, ne_lng = map(float, request.args.get("ne").split(","))

    # Find 10 cities within view, pseudorandomly chosen if more within view
    if sw_lng <= ne_lng:

        # Doesn't cross the antimeridian
        rows = db.execute("SELECT * FROM places WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude AND longitude <= :ne_lng) GROUP BY country_code, place_name, admin_code1, postal_code, admin_name1, admin_name2, admin_code2, admin_name3, admin_code3, latitude, longitude, accuracy ORDER BY RANDOM() LIMIT 10", sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    else:

        # Crosses the antimeridian
        rows = db.execute("SELECT * FROM places WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude OR longitude <= :ne_lng) GROUP BY country_code, place_name, admin_code1, postal_code, admin_name1, admin_name2, admin_code2, admin_name3, admin_code3, latitude, longitude, accuracy ORDER BY RANDOM() LIMIT 10", sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    # Output places as JSON
    return jsonify(rows)


if __name__ == '__main__':
 app.debug = True
 port = int(os.environ.get('PORT', 5000))
 app.run(host='0.0.0.0', port=port)
