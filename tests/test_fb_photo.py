#!/usr/bin/python

from gi.repository import GObject

import argparse
import logging
import time
import sys
import unittest

sys.path.append("..")

from facebook.fb_photo import FbPhoto
from facebook.fb_account import FbAccount


class TestFbPhoto(unittest.TestCase):
    PER_TEST_TIMEOUT = 30000
    photo_path = 'test.png'

    def setUp(self):
        logging.debug("Starting (%d)", int(time.time()))
        self._loop = GObject.MainLoop()
        self._tid = GObject.timeout_add(self.PER_TEST_TIMEOUT, self._timeout_cb)
        self._completed = False

    def tearDown(self):
        GObject.source_remove(self._tid)

    def _finish_test(self):
        self._completed = True
        self._loop.quit()

    def test_create_photo(self):
        def photo_created_cb(photo, photo_id, callback):
            logging.debug("Photo created: %s" % (photo_id))
            callback()
            return False

        photo = FbPhoto()
        photo.connect('photo-created', photo_created_cb, self._finish_test)
        photo.create(self.photo_path)
        self._loop.run()
        assert(self._completed)

    def test_add_comment(self):
        def photo_created_cb(photo, photo_id, callback):
            logging.debug("Photo created: %s" % (photo_id))

            def comment_added_cb(photo, comment_id, callback):
                logging.debug("Comment created: %s" % (comment_id))
                callback()
                return False

            photo = FbPhoto(photo_id)
            photo.connect("comment-added", comment_added_cb, callback)
            photo.add_comment("this is a test")
            return False

        photo = FbPhoto()
        photo.connect('photo-created', photo_created_cb, self._finish_test)
        photo.create(self.photo_path)
        self._loop.run()
        assert(self._completed)

    def test_get_comments(self):
        def photo_created_cb(photo, photo_id, callback):
            logging.debug("Photo created: %s" % (photo_id))

            def comment_added_cb(photo, comment_id, callback):
                logging.debug("Comment created: %s" % (comment_id))

                def comments_downloaded_cb(photo, comments, callback):
                    logging.debug("%s comments for photo %s",
                                  len(comments), photo.fb_object_id)

                    for c in comments:
                        logging.debug("Comment from %s with message: %s",
                                      c["from"], c["message"])
                    callback()

                photo.connect('comments-downloaded',
                              comments_downloaded_cb,
                              callback)
                photo.refresh_comments()
                return False

            photo = FbPhoto(photo_id)
            photo.connect("comment-added", comment_added_cb, callback)
            photo.add_comment("this is a test")
            return False

        photo = FbPhoto()
        photo.connect('photo-created', photo_created_cb, self._finish_test)
        photo.create(self.photo_path)
        self._loop.run()
        assert(self._completed)

    def test_transfer_state_changed(self):
        states = []
        states_started = []
        states_completed = []
        def transfer_state_changed_cb(photo, state, callback):
            states.append(state)

            if 'started' in state:
                states_started.append(state)
            elif 'completed' in  state:
                states_completed.append(state)

            if len(states_started) == 1 and len(states_completed) == 1:
                callback()
                return False

            logging.debug("transfer-state-changed events received:")
            for s in states:
                logging.debug("- %s", s)

        photo = FbPhoto()
        photo.connect('transfer-state-changed',
                      transfer_state_changed_cb,
                      self._finish_test)
        photo.create(self.photo_path)
        self._loop.run()
        assert(self._completed)

    def _timeout_cb(self):
        self._loop.quit()
        return False

def _get_params():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug',
                        type=bool,
                        default=False)
    parser.add_argument('access_token',
                        help='token to run the tests with')
    parser.add_argument('test_name',
                        nargs='?',
                        default='')
    return parser.parse_args()

if __name__ == '__main__':
    params = _get_params()

    if params.debug:
        logging.basicConfig(level=logging.DEBUG)

    FbAccount.set_access_token(params.access_token)
    unittest.main(argv=['test_fb_photo'])
