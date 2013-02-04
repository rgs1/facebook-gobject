#!/usr/bin/env python
#
# Copyright (c) 2012 Raul Gutierrez S. - rgs@itevenworks.net

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import json
import logging
import pycurl

from gi.repository import GObject

import fb_error
from fb_object import FbObject
import fb_types


class FbPhoto(FbObject):
    PHOTOS_URL = "https://graph.facebook.com/me/photos"
    COMMENTS_URL = "https://graph.facebook.com/%s/comments"

    __gsignals__ = {
        'photo-created': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
        'photo-create-failed': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
        'comment-added': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
        'comment-add-failed': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
        'comments-downloaded': (GObject.SignalFlags.RUN_FIRST, None, ([object])),
        'comments-download-failed': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
        'likes-downloaded': (GObject.SignalFlags.RUN_FIRST, None, ([object])),
    }

    def create(self, image_path):
        GObject.idle_add(self._create, image_path)

    def add_comment(self, comment):
        self.check_created('add_comment')
        GObject.idle_add(self._add_comment, comment)

    def refresh_comments(self):
        """ raise an exception if no one is listening """
        self.check_created('refresh_comments')
        GObject.idle_add(self._refresh_comments)

    def check_created(self, method_name):
        if self.fb_object_id is None:
            errmsg = "Need to call create before calling %s" % (method_name)
            raise fb_error.FbObjectNotCreatedException(errmsg)

    def _add_comment(self, comment):
        url = self.COMMENTS_URL % (self.fb_object_id)

        response = []
        def write_cb(buf):
            response.append(buf)

        res = self._http_call(url, [('message', comment)], write_cb, True,
                              fb_types.FB_COMMENT)
        if res == 200:
            try:
                comment_id = self._id_from_response("".join(response))
                self.emit('comment-added', comment_id)
            except fb_error.FbBadCall as ex:
                self.emit('comment-add-failed', str(ex))
        else:
            logging.debug("_add_comment failed, HTTP resp code: %d" % (res))
            self.emit('comment-add-failed', "Add comment failed: %d" % (res))

    def _create(self, image_path):
        c = pycurl.Curl()
        params = [('source', (c.FORM_FILE, image_path))]

        response = []
        def write_cb(buf):
            response.append(buf)

        result = self._http_call(self.PHOTOS_URL, params, write_cb,
                                 True, fb_types.FB_PHOTO)
        if result == 200:
            photo_id = self._id_from_response("".join(response))
            self.fb_object_id = photo_id
            self.emit('photo-created', photo_id)
        else:
            logging.debug("_create failed, HTTP resp code: %d" % result)

            if result == 400:
                failed_reason = "Expired access token."
            elif result == 6:
                failed_reason = "Network is down."
                failed_reason += \
                    "Please connect to the network and try again."
            else:
                failed_reason = "Failed reason unknown: %s" % (str(result))

            self.emit('photo-create-failed', failed_reason)

    def _id_from_response(self, response_str):
        response_object = json.loads(response_str)

        if not "id" in response_object:
            raise fb_error.FbBadCall(response_str)

        fb_object_id = response_object['id'].encode('ascii', 'replace')
        return fb_object_id

    def _refresh_comments(self):
        """ this blocks """
        url = self.COMMENTS_URL % (self.fb_object_id)

        logging.debug("_refresh_comments fetching %s" % (url))

        response_comments = []
        def write_cb(buf):
            response_comments.append(buf)

        ret =  self._http_call(url, [], write_cb, False, fb_types.FB_COMMENT)
        if ret != 200:
            logging.debug("_refresh_comments failed, HTTP resp code: %d" % ret)
            self.emit('comments-download-failed',
                      "Comments download failed: %d" % (ret))
            return

        logging.debug("_refresh_comments: %s" % ("".join(response_comments)))

        try:
            response_data = json.loads("".join(response_comments))
            if 'data' not in response_data:
                logging.debug("No data inside the FB response")
                self.emit('comments-download-failed',
                          "Comments download failed with no data")
                return
        except Exception as ex:
            logging.debug("Couldn't parse FB response: %s" % str(ex))
            self.emit('comments-download-failed',
                      "Comments download failed: %s" % (str(ex)))
            return

        comments = []
        for c in response_data['data']:
            comment = {}  # this should be an Object
            comment['from'] = c['from']['name']
            comment['message'] = c['message']
            comment['created_time'] = c['created_time']
            comment['like_count'] = c['like_count']
            comment['id'] = c['id']
            comments.append(comment)

        if len(comments) > 0:
            self.emit('comments-downloaded', comments)
        else:
            self.emit('comments-download-failed', 'No comments found')
