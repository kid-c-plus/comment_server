# server.py - server powering comment functionality for badradio.biz
# author - Rick Lewis
import app
from .forms import *
from .models import User

import flask
import flask_login

import bleach

# basic imports
import json
import logging
import os
import sys
import datetime
import re

# web endpoint handlers

# get json comments for current show, if enabled
@app.flaskapp.route("/comments")
def get_comments():
    try:
        # python treats monday as day 0, but we treat sunday as day 0...why can't we just get along
        currentday = (datetime.datetime.now().weekday() + 1) % 7
        currenthour = str(datetime.datetime.now().hour)

        if check_comments_enabled():
            commentfile = get_comment_file(currentday, currenthour)
            # return comment file
            if os.path.exists(commentfile):
                with app.commentfilelock:
                    with open(commentfile) as commentfileobj:
                        comments = commentfileobj.read()
                return comments
            # return empty array
            else:
                return json.dumps({})
        else:
            # return None, indicating comments are disabled at this point
            return json.dumps(None)
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error returning comments: %s: %s: %s at line %d" % (err.__class__.__name__, err.__class__.__name__, str(err), exc_tb.tb_lineno))
        return "error"

# add new comment to the pile
# comment should be in an HTML form, with a 'name' and 'comment' field
@app.flaskapp.route("/new", methods=["POST"])
def add_comment():
    try:
        currentday = (datetime.datetime.now().weekday() + 1) % 7
        currenthour = str(datetime.datetime.now().hour)

        if check_comments_enabled():

            if 'name' in flask.request.form and 'comment' in flask.request.form:
                safename = bleach.clean(flask.request.form['name'], tags=[])
                safecomment = bleach.clean(flask.request.form['comment'], tags=[])

                # truncate name and comment to max length
                if len(safename) > app.flaskapp.config['MAX_NAME_LENGTH']:
                    safename = "%s..." % safename[:app.flaskapp.config['MAX_NAME_LENGTH']]
                if len(safecomment) > app.flaskapp.config['MAX_COMMENT_LENGTH']:
                    safecomment = "%s..." % safecomment[:app.flaskapp.config['MAX_COMMENT_LENGTH']]

                # search for links and make them clickable
                if app.flaskapp.config['PARSE_LINKS']:
                    safecomment = re.sub("(?:(?:http(?:s)?://)|^|\\s)([^\\s/$?.#:]*\\.[^\\s\.][^\\s]*)", app.flaskapp.config['PARSED_LINK_FORMAT'], safecomment)

                commentfile = get_comment_file(currentday, currenthour)

                # add comment to file
                with app.commentfilelock:
                    if os.path.exists(commentfile):
                        commentsobj = json.load(open(commentfile))
                        if len(commentsobj.keys()) < app.flaskapp.config['MAX_COMMENTS']:
                            if len(commentsobj.keys()) > 0:
                                commentid = str(max([int(key) for key in commentsobj.keys()]) + 1)
                            else:
                                commentid = "1"
            
                            commentsobj[commentid] = {
                                'name'      : safename,
                                'comment'   : safecomment
                            }
                        else:
                            return "comment section full"
                    else:
                        commentsobj = {
                            '1'   :   {
                                'name'      : safename,
                                'comment'   : safecomment
                            }
                        }

                    with open(commentfile, mode="w") as commentfileobj:
                        json.dump(commentsobj, commentfileobj)
                return "comment successfully added"
            else:
                logging.info("Recieved invalid comment: %s" % ",".join(flask.request.form.keys()))
                return "invalid comment"
        else:
            return "comments currently disabled"
        
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error adding comment: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))
        return "error"
            
# handle GET and POST requests to admin console, including authentication
@app.flaskapp.route("/login", methods=["GET", "POST"])
def login():
    try:
        if flask.g.user is not None and flask.g.user.is_authenticated:
            return flask.redirect(flask.url_for("admin"))
        form = LoginForm()
        # check for valid POST data
        if form.validate_on_submit():
            logging.info("user %s attempting to log in" % form.username.data)
            return check_login(form.username.data, form.password.data, form.rememberme.data)
        return flask.render_template("login.html", form=form)
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error logging into admin console: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))
        return "error"

@app.flaskapp.route("/admin", methods=["GET", "POST"])
@flask_login.login_required
def admin():
    try:
        form = AdminForm()
        form.show.choices = [(show, show) for show in app.get_all_shows()]
        if form.validate_on_submit():
            commentssetting = form.comments.data == "enabled"
            app.set_show_comment_setting(form.show.data, commentssetting)
            logging.info("user %s changed comment setting for %s" % (flask.g.user.get_id(), form.show.data))
            flask.flash("Comments %s for %s." % (form.comments.data, form.show.data))
            return flask.redirect(flask.url_for("admin"))
        logging.info("user %s accessed admin page" % flask.g.user.get_id())
        return flask.render_template("admin.html", form=form)
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error in admin console: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))
        return "error"

@app.flaskapp.route("/editcomments", methods=["GET", "POST"])
@flask_login.login_required
def editcomments():
    try:
        if check_comments_enabled():
            comments = json.loads(get_comments())
            form = edit_comment_form_builder(comments)
            if form.validate_on_submit():
                commentsdeleted = False
                commentids = list(comments.keys())
                for commentid in commentids:
                    if getattr(form, "comment_%s" % commentid).data:
                        commentsdeleted = True
                        logging.info("user %s deleted comment %s from user %s" % (flask.g.user.get_id(), comments[commentid]['comment'], comments[commentid]['name']))
                        delete_comment(comments, commentid)
                if commentsdeleted:
                    flask.flash("Comments deleted.")
                return flask.redirect(flask.url_for("editcomments"))
            return flask.render_template("editcomments.html", enabled=True, form=form, comments=comments)
        else:
            return flask.render_template("editcomments.html", enabled=False)
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error editing comments in admin console: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))
        return "error"

@app.flaskapp.route("/logout")
@flask_login.login_required
def logout():
    try:
        flask_login.logout_user()
        return flask.redirect(flask.url_for("login"))
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error logging out of admin console: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))
        return "error"

# associated decorated functions    

@app.flaskapp.before_request
def before_request():
    flask.g.user = flask_login.current_user

# helper functions

# checks if comments are enabled for current show
def check_comments_enabled():
    currentday = (datetime.datetime.now().weekday() + 1) % 7
    currenthour = str(datetime.datetime.now().hour)
    # returns true if show's currently running AND either the current timeslot has comments enabled or the current show has comments enabled for their timeslot
    return (app.check_show_running() and ((currenthour in app.schedobj[currentday] and app.schedobj[currentday][currenthour]['comments']) or app.get_show_comment_setting(app.get_current_showname())))

# compares provided credentials to data in accounts file, and logs in users using flask if credentials are valid 
def check_login(username, password, rememberme=False):
    try:
        if os.path.exists(app.flaskapp.config['ACCOUNTFILE']):
            accounts = json.load(open(app.flaskapp.config['ACCOUNTFILE']))
            if len(accounts.keys()):
                if username in accounts and accounts[username] == password:
                    logging.info("logged in user %s" % username)
                    user = User(username)
                    flask_login.login_user(user, remember = rememberme)
                    return flask.redirect(flask.url_for("admin"))
                else:
                    logging.info("failed to log in user %s" % username)
                    flask.flash("Login failed.")
                    return flask.redirect(flask.url_for("login"))
            else:
                logging.info("failed to log in user %s: account file is empty" % username)
                flask.flash("Login failed.")
                return flask.redirect(flask.url_for("login"))
        else:
            logging.info("failed to log in user %s: account file not found" % username);
            flask.flash("Login error.")
            return flask.redirect(flask.url_for("login"))
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error logging into admin console: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))
        flask.flash("Login error.")
        return flask.redirect(flask.url_for("login"))

# get current comment filename
def get_comment_file(currentday, currenthour):
    return "%s/%s.json" % (app.COMMENTSDIR, app.get_current_showname())

# deletes comment with the given id
def delete_comment(commentobj, commentid):
    currentday = (datetime.datetime.now().weekday() + 1) % 7
    currenthour = str(datetime.datetime.now().hour)
    commentfile = get_comment_file(currentday, currenthour)
    if commentid in commentobj:
        commentobj.pop(commentid)
    with app.commentfilelock:
        with open(commentfile, mode="w") as commentfileobj:
            json.dump(commentobj, commentfileobj)
