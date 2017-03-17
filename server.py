import os
from jinja2 import StrictUndefined
from flask import Flask, render_template, redirect, request, flash, session, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from model import User, Trail, Visit, City, Connection, connect_to_db, db
from friends import friends_or_pending, get_friend_requests, get_friends
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", "abcdef")
app.jinja_env.undefined = StrictUndefined

from raven.contrib.flask import Sentry
sentry = Sentry(app, dsn='https://c42cb440f5ce49039d750403b70d910d:d1c5986bcfe645e1963902d198ff021f@sentry.io/101473')


# ---------- load initial data to database from csv -----
def load_cities():
    """
    load cities available
    """
    for row in open("data/cities.csv"):
        row = row.rstrip()
        name = row.split(",")[1]
        city = City(name=name)
        try:
            tmp_res = db.session.query(City).filter(City.name == name).one()
        except NoResultFound:
            db.session.add(city)
            db.session.commit()

def load_trails():
    """
    load trails and images of trails
    """

    for row in open("data/sftrails.csv"):
        row = row.rstrip()
        name, city, address, distance, trail_type, latitude, longitude, image_url = row.split(",")[1:]

        trail = Trail(name=name,
                        city_id=db.session.query(City).filter(City.name == city).one().city_id,
                        address = address,
                        distance=float(distance),
                        trail_type=trail_type,
                        latitude=float(latitude),
                        longitude=float(longitude),
                        image_url=image_url)
        try:
            trail = db.session.query(Trail).filter(Trail.name == name).one()
        except NoResultFound:
            db.session.add(trail)
            db.session.commit()



# ---------- HOMEPAGE --------------

@app.route('/')
def index():
    """
    homepage.
    """

    return render_template("homepage.html")


# ---------- ACCOUNT (login, signup, logout) -------

@app.route("/login", methods=["GET"])
def show_login_form():
    """
    show login form
    """

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def process_login():
    """
    user log in and redirect to user's page
    """

    email = request.form.get("email")
    password = request.form.get("password")

    current_user = User.query.filter(User.email==email).first()

    #user exists, check password
    if current_user:
        if password == current_user.password:
            #login successfully

            received_friend_requests, sent_friend_requests = get_friend_requests(current_user.user_id)
            num_received_requests = len(received_friend_requests)
            num_sent_requests = len(sent_friend_requests)
            num_total_requests = num_received_requests + num_sent_requests

            session["current_user"] = {
                "first_name": current_user.first_name,
                "user_id": current_user.user_id,
                "num_received_requests": num_received_requests,
                "num_sent_requests": num_sent_requests,
                "num_total_requests": num_total_requests
                }

            flash("You have successfully logged in!", "success")
            return redirect("/users/%s" % current_user.user_id)

        else:
            #wrong password
            flash("You entered wrong password. Please try again.", "danger")
            return redirect("/login")

    #user doesn't exist, need to register
    else:
        flash("No user associated with this email. Please sign up.", "danger")
        return redirect("/signup")


@app.route("/signup", methods=["GET"])
def show_signup_form():
    """
    show registration form
    """
    return render_template("signup.html")


@app.route("/signup", methods=["POST"])
def process_signup():
    """
    check if email exists, if not, create new user and log in after registration
    """
    email = request.form.get("email")
    password = request.form.get("password")
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    city = request.form.get("city")

    city_id = db.session.query(City).filter(City.name == city).one().city_id

   #user exists
    if db.session.query(User).filter(User.email == email).first():
        flash("An account exists with your email. Please login.", "danger")
        return redirect("/login")

    #create a new user and add to db
    new_user = User(email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    city_id=city_id)

    db.session.add(new_user)
    db.session.commit()

    if new_user.user_id % 5 != 0:
        new_user.profile_pic_url = "static/img/profile" + str(new_user.user_id % 5) + ".jpg"
        db.session.commit()

    #login with these info
    session["current_user"] = {
            "first_name": new_user.first_name,
            "user_id": new_user.user_id,
            "num_received_requests": 0,
            "num_sent_requests": 0,
            "num_total_requests": 0
            }

    flash("You have succesfully signed up for an account, and you are now logged in.", "success")

    return redirect("/users/%s" % new_user.user_id)


@app.route("/logout")
def logout():
    """
    user log out
    """
    del session["current_user"]

    flash("You have logged out.", "success")

    return redirect("/")


# ----------- USERS (user's profile page) ---------
@app.route("/users")
def get_user():
    """
    redirect to current user or login form
    """

    user = session.get("current_user")

    if user:
        return redirect("/user/%s" % user)

    return redirect("/login")


@app.route("/users/<int:user_id>")
def user_profile(user_id):
    """
    display user profile, including map and recent 5 footprints
    """

    user = db.session.query(User).filter(User.user_id == user_id).one()

    #get all footprints
    footprint = db.session.query(Visit).filter(Visit.user_id == user_id).\
                                            order_by(Visit.visit_id.desc())

    total_footprints = len(footprint.all())
    recent_footprints = footprint.limit(5).all()

    total_friends = len(get_friends(user_id).all())

    current_user_id = session["current_user"]["user_id"]
    # Check connection status between user_a and user_b
    friends, pending_request = friends_or_pending(current_user_id, user_id)

    return render_template("user_profile.html",
                           user=user,
                           total_footprints=total_footprints,
                           recent_footprints=recent_footprints,
                           total_friends=total_friends,
                           friends=friends,
                           pending_request=pending_request)






# --------- FRIEND (show, add, accept, ignore, cancel, search) ------------

@app.route("/friends")
def show_friends_and_requests():
    """
    show friends and  requests
    """

    received_friend_requests, sent_friend_requests = get_friend_requests(session["current_user"]["user_id"])

    friends = get_friends(session["current_user"]["user_id"]).all()

    return render_template("friends.html",
                           received_friend_requests=received_friend_requests,
                           sent_friend_requests=sent_friend_requests,
                           friends=friends)


@app.route("/add-friend", methods=["POST"])
def add_friend():
    """
    send a friend request
    """

    user_a_id = session["current_user"]["user_id"]
    user_b_id = request.form.get("user_b_id")

    friend_request = Connection(user_a_id=user_a_id, user_b_id=user_b_id, status="Pending")

    session["current_user"]["num_sent_requests"] += 1
    session["current_user"]["num_total_requests"] += 1

    db.session.add(friend_request)
    db.session.commit()
    return "Request Sent"


@app.route("/accept-request", methods=["POST"])
def accept_request():
    """
    accept friend request
    """
    user_a_id = request.form.get("user_a_id")
    user_b_id = request.form.get("user_b_id")

    accept = db.session.query(Connection).filter(Connection.user_a_id == user_a_id, 
                                                    Connection.user_b_id == user_b_id,
                                                    Connection.status == "Pending").first()
    accept.status = "Friends"

    db.session.commit()
    session["current_user"]["num_received_requests"] -= 1
    session["current_user"]["num_total_requests"] -= 1

    flash("You just accepted a friend request.", "success")

    return redirect("/friends")


@app.route("/ignore-request", methods=["POST"])
def ignore_request():
    """
    ignore friend request
    """
    user_a_id = request.form.get("user_a_id")
    user_b_id = request.form.get("user_b_id")

    db.session.query(Connection).filter(Connection.user_a_id == user_a_id, 
                                        Connection.user_b_id == user_b_id,
                                        Connection.status == "Pending").delete()
    db.session.commit()
    session["current_user"]["num_received_requests"] -= 1
    session["current_user"]["num_total_requests"] -= 1

    flash("You just ignored a friend request.", "danger")

    return redirect("/friends")


@app.route("/cancel-sent-request", methods=["POST"])
def cancel_sent_request():
    """
    cancel sent friend request
    """
    user_a_id = request.form.get("user_a_id")
    user_b_id = request.form.get("user_b_id")

    db.session.query(Connection).filter(Connection.user_a_id == user_a_id, 
                                        Connection.user_b_id == user_b_id,
                                        Connection.status == "Pending").delete()
    db.session.commit()    
    session["current_user"]["num_sent_requests"] -= 1
    session["current_user"]["num_total_requests"] -= 1

    flash("You just cancelled a friend request.", "danger")

    return redirect("/friends")

@app.route("/friends/search", methods=["GET"])
def search_users():
    """Search for a user by email and return results."""

    received_friend_requests, sent_friend_requests = get_friend_requests(session["current_user"]["user_id"])

    friends = get_friends(session["current_user"]["user_id"]).all()

    user_input = request.args.get("q")

    # query all users whose email contain user_input
    search_results = db.session.query(User).filter(User.email.like('%' + user_input + '%')).all()

    return render_template("friends_search_results.html",
                           received_friend_requests=received_friend_requests,
                           sent_friend_requests=sent_friend_requests,
                           friends=friends,
                           search_results=search_results)


# ----------- TRAILS (list, search, profile) -----------------

@app.route("/trails")
def trail_list():
    """
    list all trails
    """

    trails = db.session.query(Trail).order_by(Trail.name).all()

    return render_template("trail_list.html",
                           trails=trails)


@app.route("/trails/search", methods=["GET"])
def search_trails():
    """
    search trails by name
    """

    user_input = request.args.get("q")

    #Query all trails whose names contain user_input
    search_results = db.session.query(Trail).filter(Trail.name.match('*' + user_input + '*')).all()

    return render_template("trails_search_results.html", search_results=search_results)

@app.route("/trails/<int:trail_id>")
def trail_profile(trail_id):
    """
    show trail info
    """

    trail = db.session.query(Trail).filter(Trail.trail_id == trail_id).one()

    #friends who visited
    friends = get_friends(session["current_user"]["user_id"])
    user_visited = db.session.query(User).join(Visit,
                                                Visit.user_id == User.user_id).filter(Visit.trail_id == trail_id)

    has_friends_visited = False
    for friend in friends:
        if friend in user_visited:
            has_friends_visited = True
            break

    return render_template("trail_profile.html",
                           trail=trail,
                           friends=friends,
                           user_visited=user_visited,
                           has_friends_visited=has_friends_visited)


# ---------- FOOTPRINTS ----------------

@app.route("/leave-footprint", methods=["POST"])
def add_visit():
    """
    add trail visit to user's trail history
    """

    trail_id = request.form.get("trail_id")

#delete time later
    date = time.strftime("%m/%d/%Y %H:%M:%S", time.localtime())
    visit = Visit(user_id=session["current_user"]["user_id"], trail_id=trail_id, visit_date=date)
    db.session.add(visit)
    db.session.commit()

    flash("You just left a footprint on this trail.", "success")
    return redirect("/users/%s" % session["current_user"]["user_id"])


@app.route("/users/<int:user_id>/footprints")
def show_all_footprints(user_id):
    """
    show user's all footprints (check-ins)
    """

    footprints = db.session.query(Visit).filter(Visit.user_id == user_id).order_by(desc(Visit.visit_id)).all()

    return render_template("footprints.html",
                           footprints=footprints)


@app.route("/users/<int:user_id>/visits.json")
def user_footprints(user_id):
    """
    return all visits as JSON
    """

    all_footprints = db.session.query(Visit).filter(Visit.user_id == user_id).all()

    visits = {}

    for footprint in all_footprints:
        if footprint.trail.image_url:
            image_url = footprint.trail.image_url
        else:
            image_url = "/static/img/not_available.jpg"

        visits[footprint.visit_id] = {
            "trail": footprint.trail.name,
            "trail_id": footprint.trail.trail_id,
            "address": footprint.trail.address,
            "image_url": image_url,
            "latitude": float(footprint.trail.latitude),
            "longitude": float(footprint.trail.longitude)
        }

    return jsonify(visits)


@app.route("/error")
def error():
    raise Exception("Error!")


if __name__ == "__main__":
    app.debug = True

    connect_to_db(app, os.environ.get("DATABASE_URL"))
    db.create_all()

    #import data
    load_cities()
    load_trails()

    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = "NO_DEBUG" not in os.environ

    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
