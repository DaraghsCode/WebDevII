#NOTES
"""
1. the password for all user accounts is '123' if you'd like to login as one of them
2. employers and employees do not have any distinct different functions
3. the toughest part of this project was the dashboard (route found near the bottom)
"""




from flask import Flask, render_template, session, request, redirect, url_for,g, flash
from flask_session import Session
from database import get_db, close_db
from forms import UserSelectForm,RegistrationForm, LoginForm, PostForm, SearchForm, ProfileForm, DeleteForm, DeleteAccountForm, CommentForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, random
from functools import wraps

app = Flask(__name__)
app.config["SECRET_KEY"] = "this-is-my-secret-key"
app.teardown_appcontext(close_db)
app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]="filesystem"
app.config['UPLOAD_FOLDER'] = 'static/profile_pictures' #route for storing profile pictures uploaded by users
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}
Session(app)

#helper function that reads the filename and checks that its type matches the 3 types we've allowed.
def correctFileType(filename):
    if '.' not in filename:
        return False
    name=filename.rsplit('.',1) #splits "name" into two parts based on the first argument. This allows us to check if the file type matches are allowed file types.
    file_extension=name[1].lower()
    if file_extension in app.config['ALLOWED_EXTENSIONS']:
        return True
    return False 

@app.before_request
def load_logged_in_user():
    g.user=session.get("user_id",None)

def login_required(view):
    @wraps(view)
    def wrapped_view(*args,**kwargs):
        if g.user is None:
            return redirect(url_for("login",next=request.url))
        return view(*args,**kwargs)
    return wrapped_view

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/choose_account_type", methods=["GET","POST"])
def chooseAccount():
    form = UserSelectForm()
    if form.validate_on_submit():
        selection=form.user_type.data
        if selection == "I'm looking for work":
            user_type="employee"
        elif selection == "I'm looking to hire":
            user_type="employer"
        return redirect( url_for("register",user_type=user_type))
    return render_template("account_selection.html",form=form)

@app.route("/register/<user_type>", methods=["GET","POST"])
def register(user_type):
    form = RegistrationForm()
    if form.validate_on_submit():
        user_id = form.user_id.data
        password = form.password.data
        user_type=user_type
        db=get_db()
        clash = db.execute("""SELECT * FROM users 
                           WHERE user_id = ?;""",(user_id,)).fetchone()
        if clash is not None:
            form.user_id.errors.append("User id already taken")
        else:
            db.execute("""INSERT INTO users (user_id, password, user_type)
                       VALUES (?,?,?);""",(user_id, generate_password_hash(password),user_type))
            db.execute("""INSERT INTO profiles (user_id,header,body) VALUES (?,?,?);""",(user_id," ", " "))
            db.commit()
            return redirect( url_for("edit_my_profile"))
    if user_type == "employee":
        title="Employee"
        return render_template("register.html", form=form,title=title)
    elif user_type == "employer":
        title="Employer"
        return render_template("register.html", form=form,title=title)
    else:
        flash("Invalid user type.")
        return redirect(url_for("chooseAccount"))

@app.route("/login", methods=["GET","POST"])
def login():
    
    form = LoginForm()
    if form.validate_on_submit():
        user_id = form.user_id.data
        password = form.password.data
        db=get_db()
        user_in_db= db.execute("""SELECT * FROM users
                            WHERE user_id = ?;""",(user_id,)).fetchone()
        if user_in_db is None:
            form.user_id.errors.append("No such user name sorry!")
        elif not check_password_hash(user_in_db["password"], password):
            form.password.errors.append("Incorrect Password!")
        else:
            session.clear()
            session["user_id"]= user_id
            session.modified=True
            next_page=request.args.get("next")
            if not next_page:
                next_page=url_for("dashboard")
                return redirect(next_page)
            return redirect(next_page)
    return render_template("login.html",form=form)

@app.route("/logout")
def logout():
    session.clear()
    session.modified=True
    return redirect( url_for("index"))

@app.route("/post",methods=["GET","POST"])
@login_required
def post():
    form= PostForm()
    if form.validate_on_submit():
        user_id=g.user
        message=form.message.data
        db=get_db()
        db.execute("""INSERT INTO posts (user_id, body)
                        VALUES (?,?)""",(user_id,message))
        db.commit()
        return redirect( url_for("dashboard"))
    return render_template("post.html",form=form)

@app.route("/search",methods=["GET","POST"])
@login_required
def search():
    form=SearchForm()
    db=get_db()
    result=db.execute("""SELECT users.*,profiles.profile_picture FROM users 
                      JOIN profiles ON users.user_id = profiles.user_id
                      WHERE NOT users.user_id=?""",(session['user_id'],)).fetchall()
    if form.validate_on_submit():
        user_id=form.user_id.data
        user_type=form.user_type.data
        if user_type == "employees":
            result=db.execute("""SELECT users.*,profile_picture FROM users
                              JOIN profiles ON users.user_id = profiles.user_id
                            WHERE users.user_id LIKE ? AND users.user_type= ?
                          """,(f"%{user_id}%","employee")).fetchall()
        elif user_type == "employers":
            result=db.execute("""SELECT users.*,profile_picture FROM users
                              JOIN profiles ON users.user_id = profiles.user_id
                            WHERE users.user_id LIKE ? AND users.user_type= ?
                          """,(f"%{user_id}%","employer")).fetchall()
        else:
            result=db.execute("""SELECT users.*,profile_picture FROM users 
                      JOIN profiles ON users.user_id = profiles.user_id
                              WHERE users.user_id LIKE ?""",(f"%{user_id}%",)).fetchall()
        if not result:
            form.user_id.errors.append("No such user name sorry!")

    return render_template("search.html",form=form,result=result)

@app.route("/profile/<user_id>")
@login_required
def view_user(user_id):
    db=get_db()
    profile=db.execute("""SELECT * FROM profiles WHERE user_id=?;""",(user_id,)).fetchone()
    friends=db.execute("""SELECT * FROM relationships 
                       WHERE member1_id=? OR member2_id=?;
                       """,(user_id,user_id)).fetchall()
    numFriends=len(friends)
    # activity=db.execute("""SELECT * FROM POSTS WHERE user_id=?""",(user_id,)).fetchall()
    activity=db.execute("""SELECT posts.*,profile_picture FROM posts
                     JOIN profiles ON posts.user_id = profiles.user_id WHERE posts.user_id=?
                     ORDER BY post_id DESC """,(user_id,)).fetchall()
    if not profile:
        return redirect( url_for("index"))
    return render_template("profile.html",profile=profile,user_id=user_id,numFriends=numFriends,activity=activity)

@app.route("/edit_my_profile",methods=["GET","POST"])
@login_required
def edit_my_profile(): 
    form=ProfileForm()
    filename="default.png"
    if form.validate_on_submit():
        if 'picture' in request.files: #if user has uploaded a file (profile picture)
            picture = request.files['picture']
            if picture and correctFileType(picture.filename): #if picture has been uploaded and passes our helper function
                filename = secure_filename(picture.filename) #sanitizes filenames before sotring them (using secure_filename module imported at top)
                picture.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user_id=g.user
        header=form.header.data
        body=form.body.data
        db=get_db()
        db.execute("""UPDATE profiles SET profile_picture=?, header=?, body=?
                     WHERE user_id=?""",(filename,header,body,user_id))
        db.commit()
        return redirect( url_for("view_user", user_id=user_id))
    
    return render_template("edit_my_profile.html",form=form)

@app.route("/add_comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    comment_forms = {post_id: CommentForm()}
    form = comment_forms[post_id]
    user_id=session["user_id"]
    db = get_db()
    numUserComments = db.execute("""
        SELECT COUNT(*) FROM comments WHERE post_id = ? AND user_id = ?
    """, (post_id, user_id)).fetchone()[0]
    if numUserComments < 3:
        if form.validate_on_submit():
            db = get_db()
            db.execute("INSERT INTO comments (post_id, user_id, body) VALUES (?, ?, ?)",
                    (post_id, user_id, form.message.data))
            db.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("You can only have 3 comments on a post.")

    return redirect(url_for("dashboard"))

@app.route("/remove_comment/<int:comment_id>",methods=["POST"])
@login_required
def remove_comment(comment_id):
    user_id=session["user_id"]
    delete_forms={comment_id:DeleteForm()}
    form=delete_forms[comment_id]
    if form.validate_on_submit():
        db=get_db()
        db.execute("""DELETE FROM COMMENTS WHERE
                user_id=? AND comment_id=?""",(user_id,comment_id))
        db.commit()
    return redirect(url_for("dashboard"))

@app.route("/remove_post/<int:post_id>",methods=["POST"])
@login_required
def remove_post(post_id):
    user_id=session["user_id"]
    delete_forms={post_id:DeleteForm()}
    form=delete_forms[post_id]
    if form.validate_on_submit():
        db=get_db()
        db.execute("""DELETE FROM posts WHERE
                user_id=? AND post_id=?""",(user_id,post_id))
        db.commit()
    return redirect(url_for("dashboard"))    

@app.route("/friendrequest/<user_id>",methods=["GET","POST"])
@login_required
def friendrequest(user_id):
    db=get_db()
    user_check= db.execute("""SELECT * FROM users 
                           WHERE user_id=?""",(user_id,)).fetchone()
    if user_id == g.user:
        flash ("you have entered your own userID, enter a different one please")
        return redirect(url_for("index"))
    relationship_check=db.execute("""SELECT * FROM relationships WHERE member1_id=? AND member2_id=?
                                  UNION SELECT * FROM relationships WHERE member2_id=? AND member1_id=? """,(g.user,user_id,g.user,user_id)).fetchone()
    if relationship_check:
        flash (f"You and {user_id} are already friends!")
        return redirect(url_for("dashboard"))
    if not user_check:
        flash ("oops! that user doesn't exist.")
        return redirect(url_for("dashboard"))
    request_check=db.execute("""SELECT * FROM REQUESTS WHERE sender_id=? AND receiver_id=?""",(g.user,user_id)).fetchone()
    if request_check:
        flash ("You have already made a friend requst for that user, let's hope they accept it.")
        return redirect(url_for("dashboard"))
    db.execute("""INSERT INTO requests (sender_id,receiver_id) VALUES
                           (?,?)""",(g.user,user_id))
    db.commit()
    flash (f"Success! Friend request sent to {user_id}.")
    return redirect(url_for("dashboard"))

@app.route("/acceptrequest/<user_id>",methods=["GET","POST"])
@login_required
def acceptrequest(user_id):
    db=get_db()
    db.execute("""INSERT INTO RELATIONSHIPS (member1_id,member2_id) VALUES (?,?)""",(g.user,user_id))
    db.execute("""DELETE FROM REQUESTS WHERE sender_id=?""",(user_id,))
    db.commit()
    flash (f"Congratulations! You and {user_id} are now friends!")
    return redirect(url_for("dashboard"))

@app.route("/declinerequest/<user_id>",methods=["GET","POST"])
@login_required
def declinerequest(user_id):
    db=get_db()
    db.execute("""DELETE FROM REQUESTS WHERE sender_id=?""",(user_id,))
    db.commit()
    flash (f"Friend request from {user_id} has been declined.")
    return redirect(url_for("dashboard"))

@app.route("/friends",methods=["GET","POST"])
@login_required
def friends():
    db=get_db()
    friends=db.execute("""SELECT relationships.member2_id,profiles.profile_picture FROM RELATIONSHIPS
                       JOIN profiles on relationships.member2_id=profiles.user_id
                       WHERE member1_id =? 
                       UNION 
                       SELECT relationships.member1_id,profiles.profile_picture FROM RELATIONSHIPS
                       JOIN profiles on relationships.member1_id=profiles.user_id
                       WHERE member2_id =? """,(g.user,g.user)).fetchall()

    pending_requests=db.execute("""SELECT * FROM REQUESTS 
                                WHERE sender_id=?""",(session["user_id"],)).fetchall()
    return render_template("friends.html",friends=friends,user_id=g.user,pending_requests=pending_requests)

@app.route("/removefriend/<user_id>")
def removefriend(user_id):
    db=get_db()
    db.execute("""DELETE FROM RELATIONSHIPS 
               WHERE (member1_id = ? AND member2_id=?)
               OR (member1_id= ? AND member2_id=?)"""
               ,(g.user,user_id,user_id,g.user))
    db.commit()
    friends=db.execute("""SELECT member2_id FROM RELATIONSHIPS
                       WHERE member1_id =? 
                       UNION SELECT member1_id FROM RELATIONSHIPS
                       WHERE member2_id =? """,(g.user,g.user)).fetchall()
    return render_template("friends.html",friends=friends,user_id=user_id)

@app.route("/delete_account",methods=["GET","POST"])
@login_required
def deleteAccount():
    form=DeleteAccountForm()
    if form.validate_on_submit():
        db=get_db()
        user_id=form.user_id.data
        user= db.execute("SELECT password FROM users WHERE user_id=?", (g.user,)).fetchone()
        if user_id!=g.user:
            form.user_id.errors.append("Error, you must input your correct UserId")
            return render_template("delete_account.html",form=form)
        password=form.password.data
        if not check_password_hash(user["password"],password):
            form.password.errors.append("Error, must enter your correct password!")
            return render_template("delete_account.html",form=form)
        double_check=form.double_check.data
        if double_check == "No, I want to keep my account":
            flash("Thank you for choosing to keep your account!")
            return redirect(url_for("dashboard"))
        db.execute("""DELETE FROM users WHERE user_id=?""",(user_id,))
        db.commit()
        session.clear()
        return redirect(url_for("index"))
    return render_template("delete_account.html",form=form)

@app.route("/notifications",methods=["GET"])
@login_required
def notifications():
    db=get_db()
    requests=db.execute("""SELECT requests.sender_id,profiles.profile_picture FROM requests
                        JOIN profiles ON requests.sender_id=profiles.user_id
                        WHERE receiver_id=?""",(session['user_id'],)).fetchall()
    return render_template('notifications.html',requests=requests)

@app.route("/dashboard",methods=["GET"])
@login_required
def dashboard():
    db=get_db()
    posts=db.execute("""SELECT posts.*,profile_picture FROM posts
                     JOIN profiles ON posts.user_id = profiles.user_id
                     ORDER BY post_id DESC """).fetchall()
    user_id=session["user_id"]

    '''
    initiates a dictionary 'comments' where the Post ID is the key 
    and a list of the comments corresponding to said post will be the value.
    As we are selecting from a database each entry into our list will be a row object (essentially a dict).
    '''
    comments={}
    for post in posts:
        comments[post["post_id"]]=db.execute("""SELECT comment_id, user_id, body FROM comments
                        WHERE post_id=?""",(post["post_id"],)).fetchall()
    #comments is super handy as it allows us to do the heavy lifting here and passes the result on to the jinja.
    
    #comment forms is a dictionary that maps "Comment form" to each post in the feed
    comment_forms = {post["post_id"]: CommentForm() for post in posts}

    #delete forms is similar to comment forms, however it only displays the option to delete on comments the user has made (using user_id to find matches)   
    delete_post_forms= {}
    delete_comment_forms={}
    for post in posts:
        if post["user_id"] == user_id:
            delete_post_forms[post["post_id"]]=DeleteForm()

        for comment in comments[post["post_id"]]:
            if comment["user_id"] == user_id:
                delete_comment_forms[comment["comment_id"]]=DeleteForm()

    form=PostForm() #allows users to make a post while viewing the feed

    users=db.execute("""SELECT users.*, profiles.profile_picture FROM USERS
                     JOIN profiles on users.user_id= profiles.user_id
                    WHERE users.user_id!=?""",(session['user_id'],)).fetchall()
    if len(users)<4:
        users_of_today=random.sample(users,len(users))
    else:
        users_of_today=random.sample(users,4)


   
    def view_user():
        profile=db.execute("""SELECT * FROM profiles WHERE user_id=?;""",(session['user_id'],)).fetchone()
        return profile
    
    profile=view_user()
    return render_template("dashboard.html",posts=posts,comments=comments,comment_forms=comment_forms,delete_post_forms=delete_post_forms,delete_comment_forms=delete_comment_forms,form=form,users_of_today=users_of_today,profile=profile)