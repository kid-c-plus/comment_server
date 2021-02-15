# Icecast Comment Server

REST API designed to supplement an Icecast web radio station with chat functionality. 

# Installation

Once you've downloaded this repository, navigate to the directory you've saved it to and install Python dependencies using pip:

    pip3 install -r requirements.txt

Next, read through the top-level config.py file, and set all the required eonfiguration items specific to your Icecast server.

Finally, run the comment server as a WSGI script using an established web server. I recommend Apache, as detailed [here](https://www.howtoforge.com/tutorial/python-apache-mod_wsgi_ubuntu/), but you can also run it with a pure Python server such as gunicorn using this command to run on port 5000:

    gunicorn --bind 0.0.0.0:5000 run:flaskapp

# Usage

You can integrate the comment server into an existing Icecast radio website using the following endpoints:

/comments - GET a JSON dictionary of all the comments submitted to the current show, in the form:

    {<<UNIQUE COMMENT ID>> : {
        "name"      : <<NAME SUBMITTED WITH COMMENT>>,
        "comment"   : <<COMMENT TEXT>>
    }, ...}

If no show is currently airing, or the current show has disabled the chat, None (or null in JavaScript) will be returned as JSON.

/new - POST a web form containing a "name" and "comment" field to add a comment to the current show.

/admin - this is an admin console, protected by a login page, that DJs can use to enable or disable comments for their shows & delete comments for the currently running show.

Note that once authenticated, any DJ can change comment settings for any show and delete comments. This is for simplicity of use, and presumes that anyone with credentials can be trusted with the apparatus. You can still create a unique account for each user in the accounts JSON file (detailed in configs.py), which will make revoking access easier, or you can allow all users access to one account.
