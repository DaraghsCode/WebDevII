from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, RadioField, FileField, TextAreaField
from wtforms.validators import InputRequired, EqualTo, Length
from flask_wtf.file import FileAllowed

class UserSelectForm(FlaskForm):
    user_type=RadioField(
        "Please select what kind of user you want to register for:",
        choices=["I'm looking for work","I'm looking to hire"],
        default="I'm looking for work")
    submit=SubmitField("Submit")

class RegistrationForm(FlaskForm):
        user_id=StringField("Username: ", validators=[InputRequired()])
        password=PasswordField("Password: ", validators=[InputRequired()])
        password2=PasswordField("Confirm Password: ",
             validators=[InputRequired(), EqualTo("password",message="passwords must match")])
        submit=SubmitField("Submit")

class LoginForm(FlaskForm):
    user_id=StringField("User id: ",
                        validators=[InputRequired()])
    password=PasswordField("Password:",
                           validators=[InputRequired()])
    submit=SubmitField("Submit")

class PostForm(FlaskForm):
    message=TextAreaField(
                        validators=[InputRequired(),Length(1,150)])
    submit=SubmitField("Post message")

class CommentForm(FlaskForm):
         message=StringField("Comment: ",
                        validators=[Length(1,150)])
         submit=SubmitField("Post comment")

class SearchForm(FlaskForm):
    user_id=StringField("Search by UserId:",
                        validators=[Length(0,30)])
    submit=SubmitField("Submit")
    user_type=RadioField(
        choices=["employees","employers","both"],
        default="both")

class ProfileForm(FlaskForm):
    picture=FileField('Your Profile Picture',
                      validators=[
                                  FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    header=TextAreaField("Profile header:",
                        validators=[InputRequired(),Length(max=150)])
    body=TextAreaField("Profile Body:",
                        validators=[InputRequired(),Length(max=500)])
    submit=SubmitField("Sumbit")

class DeleteForm(FlaskForm):
    submit=SubmitField("Delete")

class DeleteAccountForm(FlaskForm):
    user_id=StringField("User id: ",
                        validators=[InputRequired()])
    password=PasswordField("Password:",
                           validators=[InputRequired()])
    password2=PasswordField("please enter your password again: ",
             validators=[InputRequired(), EqualTo("password")])
    double_check=RadioField("Are you sure you want to delete your account?",
                            choices=["Yes, delete my account",
                                     "No, I want to keep my account"],
                            default="No, I want to keep my account")
    submit=SubmitField("Submit")