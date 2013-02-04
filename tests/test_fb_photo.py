#!/usr/bin/python

from gi.repository import GObject

import logging
import time
import sys

sys.path.append("..")

from facebook.fb_photo import FbPhoto
from facebook.fb_account import FbAccount


def test_create_photo(loop):
    def photo_created_cb(photo, photo_id, loop):
        logging.debug("Photo created: %s" % (photo_id))
        loop.quit()

    photo = FbPhoto()
    photo.connect('photo-created', photo_created_cb, loop)
    photo.create(photo_path)

def test_add_comment(loop):
    def photo_created_cb(photo, photo_id, loop):
        logging.debug("Photo created: %s" % (photo_id))

        def comment_added_cb(photo, comment_id, loop):
            logging.debug("Comment created: %s" % (comment_id))
            loop.quit()
            return False

        photo = FbPhoto(photo_id)
        photo.connect("comment-added", comment_added_cb, loop)
        photo.add_comment("this is a test")
        return False

    photo = FbPhoto()
    photo.connect('photo-created', photo_created_cb, loop)
    photo.create(photo_path)

def test_get_comments(loop):
    def photo_created_cb(photo, photo_id, loop):
        logging.debug("Photo created: %s" % (photo_id))

        def comment_added_cb(photo, comment_id, loop):
            logging.debug("Comment created: %s" % (comment_id))

            def comments_downloaded_cb(photo, comments, loop):
                logging.debug("%s comments for photo %s",
                              len(comments), photo.fb_object_id)

                for c in comments:
                    logging.debug("Comment from %s with message: %s",
                                  c["from"], c["message"])

                loop.quit()

            photo.connect('comments-downloaded',
                          comments_downloaded_cb,
                          loop)
            photo.refresh_comments()
            return False

        photo = FbPhoto(photo_id)
        photo.connect("comment-added", comment_added_cb, loop)
        photo.add_comment("this is a test")
        return False

    photo = FbPhoto()
    photo.connect('photo-created', photo_created_cb, loop)
    photo.create(photo_path)

def test_transfer_state_changed(loop):
    states = []
    states_started = []
    states_completed = []
    def transfer_state_changed_cb(photo, state, loop):
        states.append(state)

        if 'started' in state:
            states_started.append(state)
        elif 'completed' in  state:
            states_completed.append(state)

        if len(states_started) == 1 and len(states_completed) == 1:
            loop.quit()

            logging.debug("transfer-state-changed events received:")
            for s in states:
                logging.debug("- ", s)

    photo = FbPhoto()
    photo.connect('transfer-state-changed',
                  transfer_state_changed_cb, loop)
    photo.create(photo_path)


def timeout_cb(test_name, loop, failed):
    failed.append(True)
    loop.quit()
    return False

if __name__ == '__main__':
    tname = ''
    len_args = len(sys.argv)
    if len_args < 2:
        logging.debug("Tests need an access_token!")
        exit(1)
    elif len_args == 3:
        tname = sys.argv[2]

    photo_path = "test.png"
    access_token = sys.argv[1]
    FbAccount.set_access_token(access_token)

    if tname != '':
        tests = [eval(tname)]
    else:
        tests = [eval(t) for t in dir() if t.startswith('test_')]

    for t in tests:
        print "\n* Starting %s (%s)" % (t.__name__, time.time())
        loop = GObject.MainLoop()
        failed = []
        tid = GObject.timeout_add(30000, timeout_cb, t.__name__, loop, failed)
        t(loop)
        loop.run()
        GObject.source_remove(tid)
        if len(failed) == 0:
            result = "\033[92mpassed\033[0m"
        else:
            result = "\033[91mfailed\033[0m"
        print "* Finished %s, result = %s  (%s)\n" % (t.__name__, result, time.time())

