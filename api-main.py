from flask import Flask, render_template, request, redirect, url_for, jsonify
from pymongo import MongoClient
import random
import smtplib
from email.message import EmailMessage
from datetime import date
from credentials import cred
import json


#database setup

app = Flask(__name__)
client = MongoClient("localhost", 27017)

db = client["elec-vote"]
citizens = db["citizens"]
onlineVotingCred = db["onlineVotingCred"]
elecPlaces = db["elecPlaces"]

#list where you can specifically add the places of election
ECIplaces = ["mumbai",  "sikar", "lucknow", "palli"]


#online voting cred of users registration and accordingly message generation

def onlineVotingCredReg(to, password, name):
    if (db.onlineVotingCred.find_one({"username": to})):
        found = db.onlineVotingCred.find_one({"username": to})
        username = found["username"]
        password = found["password"]
        message = "Hey " + name + ",\n\nYou already generated your password for online voting. Credentials for the same are as follows :\nYour login id : " + to + "\nYour login password : " + password + "\n\n\n\nThank you!!"
        return message
    else:
        db.onlineVotingCred.insert_one({"username" : to, "password" : password, "vote" : 0})
        message = "Hey " + name + ",\n\nYour login id : " + to + "\nYour login password : " + password + "\n\n\n\nThank you!!"
        return message

#email generation according to the user credentials generation requirement

def emailGen(to, password, name="ECI Admin"):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(cred.emailId, cred.emailPass)
    msg = EmailMessage()
    if (name=="ECI Admin"):
        message = "Hey " + name + ",\n\nYour login otp is " + password + "\n\n\n\nThank you!!"
    else:
        message = onlineVotingCredReg(to, password, name)
    msg.set_content(message)
    msg['Subject'] = 'Online Voting Credentials'
    msg['From'] = "test.proje.niks@gmail.com"
    msg['To'] = to
    s.send_message(msg)
    s.quit()

#password generation for particular user

def password():
    key = "!@#$&*1234567890qwertyuiopasd12345QWERTYUIOPASDFGHJKLZXCVBNM67890fghjklzxcvbnm1234567890!@#$&*"
    key = list(key)
    random.shuffle(key)
    password = key[0:8]
    password = "".join(password)
    return password

#age calculation of the user

def age(dbDate):
    dbDate = dbDate.split("-")
    dbDate = [int(x) for x in dbDate]
    today = str(date.today()).split("-")
    today = [int(x) for x in today]
    age = date(today[0], today[1], today[2]) - date(dbDate[0], dbDate[1], dbDate[2])
    age = age.days // 365
    return age


#adding place to database related to ECI Admin

@app.route("/addElecPlace", methods=["GET", "POST"])
def addElecPlace():
    if request.method == 'POST':
        place = request.json['place']
        if (db.elecPlaces.find_one({"placeName" : place})):
            return "Place already exist"
        else:
            db.elecPlaces.insert_one({"placeName" : place})
            return "Place Added Successfully"


@app.route("/showElecPlace", methods=["POST", "GET"])
def showElecPlace():
    if request.method == "GET":
        places = list(db.elecPlaces.find({}, {"_id" : 0}));
        #print(j[0]['placeName']) this is how to access the data
        trans = jsonify(places)
        return trans


#route for user login page rendering

@app.route("/userLogin")
def userLogin():
    return render_template("userLogin.html")

#route for processing of data submiotted by user

@app.route("/userLoginProcess", methods=["GET", "POST"])
def userLoginProcess():
    username = request.form["username"]
    password = request.form["password"]
    if (db.onlineVotingCred.find_one({"username" : username, "password" : password})):
        return render_template("userSuccessLogin.html")
    else:
        error = "The login credentials entered by you are not valid"
        return render_template("userLogin.html", error=error)


#default route for the password generation for user


@app.route("/")
def main():
    return render_template("main.html")

#rendering of the main file when user leaves all the input feilds blank

@app.route("/blank")
def blank():
    error = "You cannot leave input fields empty"
    return render_template("main.html", error=error)

#login portal for ECI Admin

@app.route("/ECI")
def ECI():
    return render_template("ECILogin.html")

#login credentials processing for ECI Admin

@app.route("/ECILogin" , methods=["POST", "GET"])
def ECILogin():
    username = (request.form["username"]).lower()
    passwordInput = request.form["password"]
    if ( username == cred.username and passwordInput == cred.password):
        global otp
        otp = password()
        emailGen(cred.ECIEmail,otp)
        return render_template("ECIOtp.html")
    else:
        error = "Username and password provided by you is not correct"
        return render_template("ECILogin.html", error=error)

#otp verification route for ECI Admin login

@app.route("/otpVerify", methods=["POST", "GET"])
def otpVerify():
    otpInput = request.form["otp"]
    if (otp == otpInput):
        return render_template("ECIHomePage.html")
    else:
        return redirect(url_for("ECI"))

#processing route for generating password for user

@app.route("/generate", methods=["GET", "POST"])
def generate():
    name = (request.form["name"]).lower()
    uid = request.form["uid"]
    dob = request.form["dob"]
    place = (request.form["place"]).lower()
    print(name, uid , dob, place )
    print(type(name), type(uid), type(dob), type(place))
    error = "Thank you for using Online Voting, your login have been mailed to your registered email id!"
    if (len(name) == 0 or len(str(uid)) == 0 or len(dob) == 0 or len(place) == 0):
        error = "You cannot leave input fields blank"
        return redirect(url_for('blank'))
    else:
        uid = int(request.form["uid"])
        if( db.citizens.find_one({"name": name, "vid": uid, "dob" : dob, "pob" : place}) ):
            #accessing the particular persons data
            reqData = db.citizens.find_one({"name": name,"vid": uid, "dob" : dob, "pob" : place})
            # checking persons age
            dbDate = reqData["dob"]
            dbName = (reqData["name"]).title()
            ageNow = age(dbDate)
            if (ageNow >= 18 ):
                electPlace = reqData["pob"]
                if electPlace in ECIplaces:
                    #sending email procedure
                    to = reqData["email"]
                    print(to)
                    passwordGen = password()
                    emailGen(to, passwordGen, dbName)
                    return render_template("main.html", error=error)
                else:
                    error = "Elections are not happening at your place!"
                    return render_template("main.html", error=error)
            else:
                error = "You are not eligible to vote, you should be atleast of 18 years in order to vote."
                return render_template("main.html", error=error)

        else:
            error = "The details given by you do not match our database"
            return render_template("main.html", error=error)
    # return render_template("success.html")


app.run(debug=True)


