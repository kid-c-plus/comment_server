# --------------------------------------------------------
#   config.py - set all configuration items in this file
# --------------------------------------------------------

# Flask-WTF Settings
# necessary to secure login page
WTF_CSRF_ENABLED = True

# your secret key can be anything, it will be used for CSRF token generation
SECRET_KEY = "<<ENTER SECRET KEY HERE>>" 

# --------------------------------
#   Internal Configuration Items
# --------------------------------

# the comment server will build an internal schedule object, including user comment settings,
# based on an external source defining the schedule in the form of a 7-entry JSON array of the form
# [{'hour' : {'show': "showname", ...} ...}, ...] where each array entry is a dictionary representing a day of the week, 
# starting on Sunday, and each dictionary entry includes, as key, the numerical hour of the day in 24-hour format,
# and, as value, a *sub-dictionary* including the name of the show at that hour under the field 'show'
# this subdictionary for each show can also include other data, if convenient for your station
# for example, if my radio station has Show A from 5 AM to 7 AM on Sundays, Show B from 9 PM to 10 PM Sundays,
# Show C from 2 PM to 4 PM on Mondays, Show D from 5 PM to 6 PM on Thursdays, and Show E from 11 PM Fridays to 1 AM Saturdays,
# my input schedule JSON file would look like:
# [
#   {
#       '5' : {'show': "Show A"},
#       '6' : {'show': "Show A"},
#       '21': {'show': "Show B"}
#   }, {
#       '14': {'show': "Show C"},
#       '15': {'show': "Show C"}
#   }, {
#   }, {
#   }, {
#       '17': {'show': "Show D"}
#   }, {
#       '23': {'show': "Show E"}
#   }, {
#       '0' : {'show': "Show E"}
#   }
# ]
# Note that the comment server will periodically poll the source schedule and update its internal representation accordingly,
# so you do not need to restart the comment server after making changes to the source schedule
# also, the comment server saves its internal schedule representation to <COMMENT SERVER BASE DIRECTORY>/json/schedule.json, so
# DO NOT use that location for the source schedule
# recommended location: <<COMMENT SERVER BASE DIRECTORY>>/json/source_schedule.json
# you can also provide a web location: just provide a url starting with http:// or https://

SOURCE_SCHEDULE_LOCATION = "<<PATH TO SOURCE_SCHEDULE_FILE_HERE>>"

# CRON argument dictionaries for the two periodic tasks of the server: refreshing the schedule from the provided source, 
# and clearing out old comment files. Refer to the specification here for information on what arguments to provide:
# https://apscheduler.readthedocs.io/en/v2.1.2/cronschedule.html
# and use https://crontab.guru to test your CRON
# note also that the comment server names each comment file after the currently running show, so that if you don't clear out
# old files in time, they can be loaded for the next iteration of that show. I recommend clearing out the comments every 24 hours,
# during a time in which no shows are running

# default - every fifteen minutes
REFRESH_SCHEDULE_CRON = {
    minute: "*/15"
}

# default - every day at 2 AM
CLEAR_COMMENTS_CRON = {
    minute: "0"
    hour: "2"
}

# provide accounts for DJs to log into the comment server admin page
# store accounts in a JSON dictionary, where the key is the username and the value is the password
# EX: {"account1" : "password1", "account2" : "password2"}
# This server ships without any default credentials, so login will not be possible until you populate this file!
# recommended location: <<COMMENT SERVER BASE DIRECTORY>>/json/accounts.json
ACCOUNTFILE = "<<PATH TO ACCOUNT FILE HERE>>"

# path to write all log output to (not just errors)
LOGFILE = "<<PATH TO LOG FILE HERE>>"

# URL of Icecast status-json.xsl file containing current status info
ICECAST_STATUS_URL = "http://localhost:8000/status-json.xsl"

# name of Icecast mountpoint on which shows are broadcst
# essentially, the mountpoint for which you want comments
MAIN_MOUNTPOINT = "stream"

# --------------------------------
#   Comment Content Settings
# --------------------------------

# whether comments should be enabled by default
DEFAULT_COMMENT_SETTING = False

# max number of comments per show
MAX_COMMENTS = 2000

# max length of "name" item in comment
MAX_NAME_LENGTH = 20

# max length of comment
MAX_COMMENT_LENGTH = 250

# whether to scan submitted comments for hyperlinks and convert them into clickable HTML tags
PARSE_LINKS = True

# string format for returned HTML link element
# use \1 to insert the matched link
# the default is the simplest form, which just encases each link in an <a> tag which opens in a new tab
PARSED_LINK_FORMAT = "<a href=http://\\1 target=\"_blank\">\\1</a>"
