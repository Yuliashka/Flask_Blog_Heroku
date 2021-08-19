# FREE BOOTSTRAP TEMPLATES:
# https://bootstrapmade.com/
# https://getbootstrap.com/docs/4.0/examples/
# https://www.creative-tim.com/bootstrap-themes/free
# FREE IMAGES: https://unsplash.com/s/photos/jungle
# RELATIONSHIPS BETWEEN SQLITE TABLES DOCS: https://docs.sqlalchemy.org/en/13/orm/basic_relationships.html
# FLASK GRAVATAR IMAGES: https://pythonhosted.org/Flask-Gravatar/
# IMAGES IMPLEMENTATION: http://en.gravatar.com/site/implement/images
# ENVIRONMENT FILE CREATION: https://able.bio/rhett/how-to-set-and-get-environment-variables-in-python--274rgt5
# CREATING GITIGNORE FILE: https://www.toptal.com/developers/gitignore
# (go to this link, write Flask, copy all info and add to .gitignore file, commit).

from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
# In relational databases such as SQLite, MySQL or Postgresql we're able to define
# a relationship between tables using a ForeignKey and a relationship() method:
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import LoginForm, RegisterForm, CreatePostForm, CommentForm
# Gravatar images are used across the internet to provide an avatar image for
# blog commenters. Gravatar allows you to change the image that you use across the blog
# websites that use Gravatar here: http://en.gravatar.com/:
from flask_gravatar import Gravatar
import os
# we are using this python module to create a new SMTP object (for email sending):
import smtplib
# TO PROTECT OUR ROUTES FROM ACCESS OF NOT LOGGED IN USERS (FROM USERS WITH ID DIFFERENT FROM ID=1):
from functools import wraps


# VARIABLES:
# MY GOOGLE ACCOUNT:
EMAIL = os.getenv("MY_EMAIL")
PASSWORD = os.getenv("MY_PASSWORD")


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)
# INTEGRATION GRAVATAR TO FLASK:
# Initialize with flask application and default parameters:
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# WORKING WITH FLASK_LOGIN:
# The login manager contains the code that lets your application and Flask-Login work together,
# such as how to load a user from an ID, where to send users when they need to log in,
# and the like.
login_manager = LoginManager()
# CONFIG OUR APP TO BE ABLE TO USE FLASK_LOGIN:
# Once the actual application object has been created, you can configure it for login with:
login_manager.init_app(app)


# CREATING USER LOADER FUNCTION:
# You will need to provide a user_loader callback. This callback is used to reload
# the user object from the user ID stored in the session.
# It should take the unicode ID of a user, and return the corresponding user object.
# For example:
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# RELATIONSHIPS BETWEEN DB TABLES:
# We need to create a relationship between the User table and the BlogPost table
# to link them together. So we can see which BlogPosts a User has written.
# Or see which User is the author of a particular BlogPost.
# We need to create a bidirectional One-to-Many relationship between the two tables.

# CREATING THE TABLE FOR KEEPING USERS IN DATABASE (PARENT TABLE):
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    # ADDING PARENT RELATIONSHIPS BETWEEN USER AND BLOGPOST TABLES:
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # ADDING PARENT RELATIONSHIP FOR BETWEEN USER AND COMMENT TABLES:
    # "comment_author" refers to the comment_author property in the Comment class.
    comments = relationship("Comment", back_populates="comment_author")


# CREATING THE TABLE FOR KEEPING POSTS IN DATABASE (CHILD TABLE):
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # ADDING A CHILD RELATIONSHIP BETWEEN BLOGPOST AND USER TABLES:
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in
    # the User class.
    author = relationship("User", back_populates="posts")
    # ADDING A PARENT RELATIONSHIP BETWEEN BLOGPOST AND COMMENT TABLES:
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


# CREATING A TABLE FOR KEEPING USERS COMMENTS IN DB:
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    # ADDING A CHILD RELATIONSHIP BETWEEN COMMENT AND USER TABLES:
    # Establish a One to Many relationship Between the User Table (Parent) and the
    # Comment table (Child). Where One User is linked to Many Comment objects.
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # ADDING A CHILD RELATIONSHIP BETWEEN BLOGPOST AND COMMENT TABLES:
    # Establish a One to Many relationship between each BlogPost object (Parent) and
    # Comment object (Child). Where each BlogPost can have many associated Comment objects.
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


# CREATING ALL TABLES IN DATABASE:
db.create_all()


# CREATING LOGIN_REQUIRED DECORATOR:
# Just because a user can't see the buttons, they can still manually access the
# /edit-post or /new-post or /delete routes. Protect these routes by creating a Python
# decorator called @admin_only
# If the current_user's id is 1 then they can access those routes, otherwise,
# they should get a 403 error (not authorised).
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 or user is not authenticated (not logged in)
        # then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    # Everytime you call render_template(), you pass the current_user over to the template.
    # current_user.is_authenticated will be True if they are logged in/authenticated after registering.
    # You can check for this is header.htm
    return render_template("index.html", all_posts=posts, current_user=current_user)


# RENDERING REGISTER.HTML PAGE
# passing there an object of RegisterForm that is created in forms.py
@app.route('/register', methods=["GET", "POST"])
def register():
    # CREATING A WTF FORM OBJECT:
    form = RegisterForm()
    # IF USER CLICK THE BUTTON AT REGISTER.HTML PAGE:
    if form.validate_on_submit():

        # We check if such user already registered in our db:
        # Taking email value from the input at register.html page:
        # Finding our user with such email in our db:
        if User.query.filter_by(email=form.email.data).first():
            print(User.query.filter_by(email=form.email.data).first())
            # User already exists
            # USING FLASK FLASH MESSAGES:
            # if user exists in db we show him a message and redirect him to login page:
            # we add a code of flash message at login page to show to the user the text of our message
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        # ADDING HASH AND SALT PASSWORD:
        # Here we are using generate_password_hash() function of Werkzeug.
        # In the beginning we added:
        # from werkzeug.security import generate_password_hash, check_password_hash
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        # ADDING A NEW USER TO DATABASE:
        # getting information from inputs at register.html page:
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        # This line will authenticate the user with Flask-Login
        # When the user is registered he will be logged in automatically and will be authenticated:
        login_user(new_user)
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    # CREATING OBJECT FOR LOGIN WTFORM:
    form = LoginForm()
    # If we press the button "LET me in":
    if form.validate_on_submit():
        # We get the information from email input from login.html page:
        email = form.email.data
        password = form.password.data

        # Finding our user with such email in our Database:
        user = User.query.filter_by(email=email).first()
        # USING FLASK FLASH MESSAGES:
        # if user does not exist in db we show him a message and redirect him to login page:
        # we add a code of flash message at login page to show to the user the text of our message
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        # if there is such user exists in our database and
        # his hashed and salted password is the same as the password in database:
        # USING werkzeug.security check_password_hash() function:
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    # To logout our user we are using logout_user() function from Flask_Login
    # The user will be logged out, and any cookies for his session will be cleaned up.
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    # CREATING AN OBJECT FOR COMMENTS FORM:
    form = CommentForm()
    # Checking which post wanted to see the user:
    requested_post = BlogPost.query.get(post_id)

    # If the user push the button "Submit comment" at post.html page:
    if form.validate_on_submit():
        # We check if this user is authenticated to write comments (this user must be
        # registered and logged in)
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        # ADDING USERS COMMENT TO DATABASE:
        # getting information from input at post.html page (text):
        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        # Adding to our db a new comment:
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post, form=form, current_user=current_user)


@app.route("/about")
def about():
    # in order to remove login and register button from header.html page when our user
    # is already logged in we are using (logged_in=current_user.is_authenticated) from Flask_Login
    # we pass it to our about.page
    return render_template("about.html", current_user=current_user)


# @app.route("/contact")
# def contact():
#     return render_template("contact.html", current_user=current_user)
# TO ALLOW TO USER SEND A MESSAGE TO MY EMAIL:
@app.route("/contact", methods=["GET", "POST"])
def contact():
    message_is_sent = False
    if request.method == "POST":
        # checking if the user already exists in our db:
        if not current_user.is_authenticated:
            flash("You need to login or register to send a message.")
            return redirect(url_for('login'))
        else:
            # GETTING USERS MESSAGE:
            # getting information from input at contact.html page (text):
            name = request.form.get("name")
            email = request.form.get("email")
            tel = request.form.get("tel")
            message = request.form.get("message")

            # SENDING MESSAGE TO EMAIL:
            # CREATING AN OBJECT:
            # we connect to gmail.com server:
            # we create an object from SMTP class.
            with smtplib.SMTP("smtp.gmail.com") as connection:
                # SECURING THE CONNECTION:
                # the next way we call starttls() = transport layer Security. A way of securing a connection to
                # our email server. To prevent reading of our emails during sending to server.
                connection.starttls()

                # LOGGING IN:
                connection.login(user=EMAIL, password=PASSWORD)

                # SENDING EMAILS:
                # emails without title are often considered as spam. its better create a title - subject.
                connection.sendmail(
                    from_addr=EMAIL,
                    to_addrs="laramera@outlook.it",
                    msg=f"Subject:BlogPost Message\n\nUser name: {name}\n\n"
                        f"User email: {email}\n\n User message: {message}"
                )

            message_is_sent = True
            return render_template("contact.html", message_is_sent=message_is_sent)

    return render_template("contact.html", message_is_sent=message_is_sent)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=form, current_user=current_user)




@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=current_user,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

