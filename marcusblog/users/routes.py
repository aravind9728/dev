from flask import render_template, url_for,flash,redirect,request,Blueprint
from flask import Flask
from flask_login import login_user, current_user, logout_user, login_required
from marcusblog import db, bcrypt
from marcusblog.models import User, Post
from marcusblog.users.forms import (RegistrationForm,RequestResetForm,ResetPasswordForm,LoginForm,UpdateAccountForm )
from marcusblog.users.utils import save_picture, send_reset_email
from twilio.rest import Client
import random 

users = Blueprint('users', __name__)
users.secret_key = 'otp'

@users.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit() 
        flash(f"hey! {form.username.data} Your account has been created, Please user your email ID and password to login!", 'success')
        return redirect(url_for('users.login'))
    return render_template('register.html', title='Register', form=form)


@users.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(' main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect (next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Incorrect username or password. Please enter your correct username and password or click forget password', 'danger')
    return render_template('login.html', title='Login', form=form)

@users.route("/getotp", methods =['POST'])
def getotp():
    number = request.form['number']
    val = getotpAPI(number)
    if val:
        return render_template("otp.html")

@users.route ("/validateotp", methods = ['POST'])
def validateotp():
    otp = request.form['otp']
    if 'response' in session:
        s = session['response']
        session.pop('response',None)
        if s == otp:
            return 'Your are Authorized for the session! thank you' 
        else:
            return 'Your not AUthorized'    

def generateOTP():
    return random.randrange(100000,999999)  

def getotpAPI(number):
    account_sid=''
    auth_token =''
    client = Client(account_sid,auth_token)
    otp = generateOTP()
    session['response'] = str(otp)
    body = 'Your OTP is' + str(otp)
    message = client.messages.create(from_='+13513336544',body=body,to=number)

    if message.sid:
        return True
    else:
        False



@users.route("/logout")
def logout():
    logout_user()
    flash(f"You are logged out",'info')
    return redirect(url_for('users.login'))


@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash(f'Your account has been updated', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email    
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file = image_file, form=form)


@users.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page',1,type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('user_posts.html', posts=posts, user=user)   


@users.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form=RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Email has been sent to reset your password. The link will expire after 30min.', 'info')
        return redirect(url_for('users.login'))
    return render_template('reset_request.html', title='Reset Password', form=form)    

@users.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('The token is invalid or expired', 'warning')    
    form=ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')       
        user.password = hashed_password
        db.session.commit() 
        flash(f"hey!{{form.username.data}}Your Passcode has been updated Please use your new passcode to login. Thanks!", 'success')
        return redirect(url_for('users.login'))
    return render_template('reset_token.html', title='Reset Password', form=form)
