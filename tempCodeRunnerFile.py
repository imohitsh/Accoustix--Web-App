from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
from flask_socketio import SocketIO, send, emit, join_room, leave_room
from flask_pymongo import PyMongo
from time import localtime, strftime, time
from passlib.hash import pbkdf2_sha256
from flask_mail import Message, Mail
from bson.json_util import dumps, loads
# import additional

current_user = "test"

app = Flask(__name__)

#  Contact Us:
#file = open("credentials.txt", "r")
own_email =  'abc@gmail.com'  #file.readline().strip()
own_password = 'abd' # file.readline().strip()
#file.close()

mail = Mail(app)

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = own_email
app.config["MAIL_PASSWORD"] = own_password
app.config["MAIL_USE_SSL"] = True

mail = Mail(app)


# Database integration
app.config["MONGO_URI"] = "mongodb://localhost:27017/Accoustix"
mongodb_client = PyMongo(app)
db = mongodb_client.db

app.config["SECRET_KEY"] = "melodyitnichocolatykyuhai"
# Creating an instance of SocketIO using constructor.
socketio = SocketIO(app)


# Creating a global user
@app.before_request
def before_request():
    g.user = None
    if "user_email" in session:
        user = db.users.find_one({"email": session["user_email"]})
        g.user = user


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/chat")
def chat():
    return render_template("chat.html", username=g.user['username'])


@app.route("/chat2")
def chat2():
    return render_template("chat2.html", username=g.user['username'])


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    user_exists = False
    if request.method == "POST":
        # getting user's data from registration page
        first_name = request.form["first-name"]
        last_name = request.form["last-name"]
        email = request.form["email"]
        dob = request.form["user-dob"]
        username = request.form["username"]
        password = request.form["password"]
        gender = request.form["gender"]

        existing_user = db.users.find_one({"email": email, "username": username})
        if existing_user is None:
            # encrypting user's password for protection.
            hashed_password = pbkdf2_sha256.hash(password)

            # inserting data into the db.
            db.users.insert_one(
                {
                    "email": email,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "dob": dob,
                    "gender": gender,
                    "password": hashed_password,
                }
            )
            return redirect(url_for("login"))
        else:
            user_exists = True

    return render_template("register.html", user_exists=user_exists)


@app.route("/login", methods=["POST", "GET"])
def login():
    wrong_credentials = False
    if request.method == "POST":
        users = db.users
        user_email = request.form["email"]
        user_password = request.form["password"]

        current_user = users.find_one({"email": user_email})
        print(current_user)

        if current_user and pbkdf2_sha256.verify(
            user_password, current_user["password"]):
            session["user_email"] = current_user["email"]
            # join_room(current_user["connection"])
            return redirect(url_for("chat2"))
        else:
            wrong_credentials = True
            return render_template("login.html", wrong_credentials=wrong_credentials)

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    return redirect(url_for("home"))

@app.route("/contact", methods=["POST", "GET"])
def contact():
    messageSent = 0
    if request.method == "POST":
        user_name = request.form["name"]
        user_email = request.form["email"]
        user_msg = request.form["message"]

        msg = Message(
            "Accoustix Contact Response",
            sender=own_email,
            recipients=[user_email],
        )

        msg.body = f"""
        Hi {user_name}👋,

        Thank you for contacting us.

        We've recieved your message and one of our team members will get back to you soon.

        Best Regards,
        Team Accoustix.
        """

        mail.send(msg)
        messageSent = 1

    return render_template("contact.html", messageSent=messageSent)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if request.method == "POST":
        first_name = request.form["first-name"]
        last_name = request.form["last-name"]
        username = request.form["username"]
        newpassword = request.form["newpassword"]
        oldpassword = request.form["oldpassword"]

        if g.user and pbkdf2_sha256.verify(oldpassword, g.user["password"]):
            hashed_password = pbkdf2_sha256.hash(newpassword)
            db.users.update_one(
                {"email": g.user["email"]},
                {
                    "$set": {
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "password": hashed_password,
                    }
                },
            )
        return redirect(url_for("profile"))
    return render_template("profile.html")


@app.route('/searchmembers/<data>', methods=['GET', 'POST'])
def serach_members(data):
    # user = db.users.find({
    #     '$or': [
    #             { 'first_name': { '$regex' : '/{data}/' } },
    #             { 'last_name': { '$regex' : '/{data}/' } },
    #             { 'username': { '$regex' : '/{data}/' } },
    #             { 'email': { '$regex' : '/{data}/' } }
    #     ]
    # })
    user = db.users.find({
        'username' : data
    })

    print(user.count())     
    return dumps(user)


''' --------- SocketIO Code Starts ----------'''

@socketio.on("incoming-msg")
def on_message(data):
    
    # """Broadcast messages"""
    print(data)
    msg = data["msg"]
    username = data["username"]
    room = data["room"]
    # Set timestamp
    time_stamp = strftime("%b-%d %I:%M%p", localtime())
    send({"username": username, "msg": msg, "time_stamp": time_stamp},  room=room)
    


@socketio.on("join")
def on_join(data):
    """User joins a room"""

    username = data["username"]
    room = data["room"]
    join_room(room)
    print(f'\n\nRoom joined by user {data["username"]}\n\n')

    # Broadcast that new user has joined
    send({"msg": username + " has joined the " + room + " room."}, room=room)


@socketio.on("leave")
def on_leave(data):
    """User leaves a room"""

    username = data["username"]
    room = data["room"]
    leave_room(room)
    send({"msg": username + " has left the room"}, room=room)


# @socketio.on("message")
# def message(data):
#     # print("Message: ", data, "\n\n\n\n")
#     send(
#         {
#             "msg": data["msg"],
#             "username": data["username"],
#             "timestamp": strftime("%b-%d %I:%M%p", localtime()),
#         }
#     )


# @socketio.on("join")
# def join(data):
#     join_room(data["room"])
#     send({"msg": data["username"] + "has joined the room"})


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5500)
