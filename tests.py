#! /Users/rick/Documents/Other/badradio/comment_server/venv/bin/python3
import os, shutil, sys, subprocess

import unittest
import json
import requests
import time
import re

import app

URL = "http://localhost:5000"
login = {'username' : "<<INSERT USERNAME HERE>>", 'password' : "<<INSERT PASSWORD HERE>>", 'rememberme' : "y"}

class TestCase(unittest.TestCase):
    def setUp(self):
        shutil.copyfile(app.SCHEDULEFILE, "%s.bak" % app.SCHEDULEFILE)

    # __init__.py tests

    def test_no_schedule(self):
        if os.path.exists(app.SCHEDULEFILE):
            os.remove(app.SCHEDULEFILE)
        sched = app.open_schedule()
        assert sched == app.create_empty_sched()

    def test_invalid_schedule(self):
        with open(app.SCHEDULEFILE, mode="w") as file:
            file.write("invalid json!!")
        sched = app.open_schedule()
        assert sched == app.create_empty_sched()

    def test_refresh_schedule(self):
        if os.path.exists(app.SCHEDULEFILE):
            os.remove(app.SCHEDULEFILE)
        app.refresh_schedule()
        assert os.path.exists(app.SCHEDULEFILE)

    def test_nonsense_show(self):
        assert not app.get_show_comment_setting("nonexistent show")

    def test_stream_status(self):
        assert app.get_stream_status()

    def test_show_running(self):
        assert app.check_show_running()

    # commenting tests

    def test_clear_comments(self):
        with open("%s/dummy_show.json" % app.COMMENTSDIR, mode="w") as file:
            file.write(json.dumps({1 : {'name' : "rick", 'comment' : "comment"}}))
        app.clear_comments()
        assert not os.path.exists("%s/dummy_show.json" % app.COMMENTSDIR)

    # def test_long_comment(self):
    #     comment = "a" * 1001
    #     requests.post("http://localhost:5000/new", data={'name' : "rick", 'comment' : comment})
    #     print(requests.get("http://localhost:5000/comments").text)
    #     assert requests.get("http://localhost:5000/comments").text == json.dumps({1 : {'name' : "rick", 'comment' : "%s..." % comment[:250]}})

    # def test_long_name(self):
    #     name = "a" * 31
    #     requests.post("http://localhost:5000/new", data={'name' : name, 'comment' : "comment"})
    #     print(requests.get("http://localhost:5000/comments").text)
    #     assert requests.get("http://localhost:5000/comments").text == json.dumps({1 : {'name' : "%s..." % name[:20], 'comment' : "comment"}})

    def test_many_comments(self):
        for i in range(50):
            requests.post("http://localhost:5000/new", data={'name' : "rick", 'comment' : "comment %d" % i})
        assert requests.post("http://localhost:5000/new", data={'name' : "rick", 'comment' : "comment 101"}).text == "comment section full"

    def test_invalid_comment(self):
        ic = "invalid comment"
        assert requests.post("http://localhost:5000/new", data=None).text == ic and requests.post("http://localhost:5000/new", data={'big' : "old", 'butt' : "ass"}).text == ic and requests.post("http://localhost:5000/new", data={'name' : "rick", 'comment' : "comment", 'butt' : "ass"}).text == "comment successfully added"

    # admin console tests
    def test_invalid_login(self):
        login['username'] = "invalid name"
        login['password'] = "invalid password"
        assert requests.post(URL + "/login", data=login).url == "http://localhost:5000/login"
  
    def tearDown(self):
        app.clear_comments()
        shutil.copyfile("%s.bak" % app.SCHEDULEFILE, app.SCHEDULEFILE)
        os.remove("%s.bak" % app.SCHEDULEFILE)
        

if __name__ == "__main__":
    child = subprocess.Popen([sys.executable, "./debug.py", "&"])
    time.sleep(10)
    app.flaskapp.debug = True
    app.clear_comments()
    unittest.main()
    child.kill()
    child.wait()
