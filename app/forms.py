from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField, PasswordField, RadioField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    rememberme = BooleanField('rememberme', default=False)

class AdminForm(FlaskForm):
    show = SelectField("show", validators=[DataRequired()])
    comments = RadioField("comments", choices=[("enabled",) * 2, ("disabled",) * 2], validators=[DataRequired()])


def edit_comment_form_builder(comments):
    class EditCommentForm(EditCommentFormBase):
        pass

    if comments:
        for commentid in comments.keys():
            setattr(EditCommentForm, "comment_%s" % commentid, BooleanField(label="%s:%s" % (comments[commentid]['name'], comments[commentid]['comment'])))

    return EditCommentForm()

class EditCommentFormBase(FlaskForm):
    pass
