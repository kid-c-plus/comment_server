# --------------------------------------------------------------------
#   __init__.py - initialization & helper methods for comment server
# --------------------------------------------------------------------

from .models import User

# basic imports
import json
import requests
import atexit
import logging
import os
import sys
import glob
import re
import time
import pathvalidate
from threading import Lock

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager

flaskapp = Flask(__name__)
CORS(flaskapp)

# load config data from config.py
flaskapp.config.from_object("config")

loginmanager = LoginManager()
loginmanager.init_app(flaskapp)
loginmanager.login_view = "login"

from apscheduler.schedulers.background import BackgroundScheduler

# -------------
#   Constants 
# -------------

# current path to "comment_server"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

# file with information on shows & comment preferences
SCHEDULEFILE = "%s/json/schedule.json" % BASE_DIR

# directory in which to create json comment objects
COMMENTSDIR = "%s/json/comments" % BASE_DIR

# global variables

tasksched = BackgroundScheduler()

schedobj = None

commentfilelock = Lock()

streamstatus = {
    'show_running'  : False,
    'show_name'     : "",
    'check_time'    : 0
}

# startup tasks
def startup():

    # configure logging
    logging.basicConfig(filename=flaskapp.config['LOGFILE'],
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')

    # load basic schedule
    logging.info("started server")

    global schedobj
    schedobj = open_schedule()

    # load schedule from provided JSON object
    refresh_schedule()

    # schedule hourly pulls & daily clear
    tasksched.add_job(func=refresh_schedule, trigger="cron", **flaskapp.config['REFRESH_SCHEDULE_CRON'])

    # executes at 2 AM
    tasksched.add_job(func=clear_comments, trigger="cron", **flaskapp.config['CLEAR_COMMENTS_CRON'])

    tasksched.start()
    
# shutdown tasks
def shutdown():
    # stop scheduled tasks
    tasksched.shutdown()
    
# run when __name__=="__main__"
def main():
    # run startup tasks
    startup()
   
    # stop scheduled pulls on program exit
    atexit.register(shutdown)

# LoginManager load user function
@loginmanager.user_loader
def load_user(user_id):
    return User(user_id)

# helper methods

# method to create new schedule obj of empty dicts
def create_empty_sched():
    return [{}, {}, {}, {}, {}, {}, {}]

# opens schedule from json file, or creates it if it doesn't exist
# obj is [{time: {name, comments enabled}}]
def open_schedule():
    try:
        if os.path.exists(SCHEDULEFILE):
            with open(SCHEDULEFILE) as schedfile:
                return json.load(schedfile)
        else:
            return create_empty_sched()

    # if json is invalid
    except ValueError:
        return create_empty_sched()

    # something else?
    except Exception as err:
        raise err

# search schedule for show, return their comment setting, or default comment value if show not found
def get_show_comment_setting(showname):
    for day in schedobj:
        for hour in day.keys():
            if day[hour]['show'] == showname:
                return day[hour]['comments']
    return flaskapp.config['DEFAULT_COMMENT_SETTING']

# set comment enabled setting for a given showname
def set_show_comment_setting(showname, comment):
    schedobjchanged = False
    for day in schedobj:
        for hour in day.keys():
            if day[hour]['show'] == showname:
                if day[hour]['comments'] != comment:
                    schedobjchanged = True
                day[hour]['comments'] = comment
    if schedobjchanged:
        with open(SCHEDULEFILE, mode="w") as schedfile:
            json.dump(schedobj, schedfile)

# properly sanitized icecast stream status (None on error)
def get_stream_status():
    try:
        statusresp = requests.get(flaskapp.config['ICECAST_STATUS_URL'])
        if statusresp.status_code == 200:
            # fixing the icecast single dash bug
            statustext = re.sub("([^\\\\])([\"\']): *- *,([\"\'])", "\\1\\2:\"-\",\\3", statusresp.text)
            return json.loads(statustext)
        else:
            logging.error("Error accessing Icecast: HTTP Error %d" % statusresp.status_code)
            return None
    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error getting status from Icecast: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))
        return None


# check if a show is currently on air on the configured main mountpoint
# refreshes check every 5 seconds
def check_show_running():
    global streamstatus

    if time.time() - streamstatus['check_time'] >= 5.0:
        update_stream_status()

    return streamstatus['show_running']

def get_current_showname():
    global streamstatus

    if time.time() - streamstatus['check_time'] >= 5.0:
        update_stream_status()

    return streamstatus['show_name']

# get current comment filename
def get_comment_file():
    return "%s/%s.json" % (COMMENTSDIR, pathvalidate.sanitize_filename(get_current_showname()))

def update_stream_status():
    currentstatus = get_stream_status()

    if 'icestats' in currentstatus and 'source' in currentstatus['icestats']:
        # when multiple mountpoints are present, they're collected into a JSON array
        # iterate through them to find the main one
        if type(currentstatus['icestats']['source']) == type([]):
            streamstatus['show_running'] = False
            streamstatus['show_name'] = ""
            for show in currentstatus['icestats']['source']:
                if show['listenurl'].split("/")[-1] == flaskapp.config['MAIN_MOUNTPOINT'] and 'stream_start' in show:
                    streamstatus['show_running'] = True
                    streamstatus['show_name'] = show['server_name']

        # if only one mountpoint is present, it's not collected into an array, which is annoying
        else:
            show = currentstatus['icestats']['source']
            streamstatus['show_running'] = (show['listenurl'].split("/")[-1] == flaskapp.config['MAIN_MOUNTPOINT'] and 'stream_start' in show)
            streamstatus['show_name'] = show['server_name'] if 'server_name' in show else ""
    else:
        streamstatus['show_running'] = False
        streamstatus['show_name'] = ""

    streamstatus['check_time'] = time.time()

# returns a list of all unique shows on the schedule, in alphabetical order
def get_all_shows():
    shows = []
    if schedobj:
        for day in schedobj:
            for hour in day.keys():
                if not day[hour]['show'] in shows:
                    shows.append(day[hour]['show'])
    shows.sort(key=lambda x: x.lower())
    return shows


# scheduled methods

# pull authoritative schedule from provided URL or path
def refresh_schedule():
    try:
        path = flaskapp.config['SOURCE_SCHEDULE_LOCATION']

        inputschedobj = None
        # if path begins with http:// or https://, download and load it using requests
        if re.match("http[s]?://", path):
            # pull html site
            inputschedresp = requests.get(path)
            if inputschedresp.status_code == 200:
                inputschedobj = json.loads(inputschedresp.text)
        else:
            if os.path.exists(path):
                with open(path) as inputschedfile:
                    inputschedobj = json.load(inputschedfile)

        if not schedobj:
            raise FileNotFoundError("Schedule file at %s not found." % path)
        elif len(schedobj) != 7:
            raise ValueError("Schedule file does not contain seven days worth of shows")

        # iterate through days & hours in both schedule objects and reconcile internal one with input
        for day in range(7):
            schedday = schedobj[day]
            inputschedday = inputschedobj[day]
            for hournum in range(24):
                hour = str(hournum)
                if hour in inputschedday:
                    if hour not in schedday or inputschedday[hour]['show'] != schedday[hour]['show']:
                        schedday[hour] = {
                            'show'      : inputschedday[hour]['show'],
                            'comments'  : get_show_comment_setting(inputschedday[hour]['show'])
                        }
                elif hour in schedday:
                    schedday.pop(hour)
                
        # save output schedule
        with open(SCHEDULEFILE, mode="w") as schedfile:
            json.dump(schedobj, schedfile)

        logging.info("Updated schedule")

    except Exception as err:
        _, _, exc_tb = sys.exc_info()
        logging.error("Error updating schedule: %s: %s at line %d" % (err.__class__.__name__, str(err), exc_tb.tb_lineno))

# delete all comment files daily
def clear_comments():
    commentfiles = glob.glob("%s/*" % COMMENTSDIR)
    for commentfile in commentfiles:
        os.remove(commentfile)
    if flaskapp.debug:
        print("removed comments from %s" % COMMENTSDIR)

main()
from app import views
