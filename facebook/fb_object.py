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

import logging
import pycurl
import urllib

from gi.repository import GObject

import fb_types
from fb_account import FbAccount


class FbObject(GObject.GObject):

    __gsignals__ = {
        'transfer-started': (GObject.SignalFlags.RUN_FIRST, None, ([int, int])),
        'transfer-progress': (GObject.SignalFlags.RUN_FIRST, None, ([int, int, float])),
        'transfer-completed': (GObject.SignalFlags.RUN_FIRST, None, ([int, int])),
        'transfer-failed': (GObject.SignalFlags.RUN_FIRST, None, ([int, int, str])),
        'transfer-state-changed': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
    }

    def __init__(self, fb_object_id=None):
        GObject.GObject.__init__(self)
        self.fb_object_id = fb_object_id

    def _http_call(self, url, params, write_cb, post, fb_type):
        logging.debug('_http_call')

        app_auth_params = [('access_token', FbAccount.access_token())]

        def f(*args):
            logging.debug('will call _http_progress_cb')
            try:
                args = list(args) + [fb_type]
                self._http_progress_cb(*args)
            except Exception as ex:
                logging.debug("oops %s" % (str(ex)))

        c = pycurl.Curl()
        c.setopt(c.NOPROGRESS, 0)
        c.setopt(c.PROGRESSFUNCTION, f)
        c.setopt(c.WRITEFUNCTION, write_cb)

        if post:
            c.setopt(c.POST, 1)
            c.setopt(c.HTTPPOST, app_auth_params + params)
            transfer_type = fb_types.FB_TRANSFER_UPLOAD
            transfer_str = "Upload"
        else:
            c.setopt(c.HTTPGET, 1)
            params_str = urllib.urlencode(app_auth_params + params)
            url = "%s?%s" % (url, params_str)
            transfer_type = fb_types.FB_TRANSFER_DOWNLOAD
            transfer_str = "Download"

        logging.debug("_http_call: %s" % (url))

        c.setopt(c.URL, url)
        c.perform()

        result = c.getinfo(c.HTTP_CODE)
        if result != 200:
            error_reason = "HTTP Code %d" % (result)
            self.emit('transfer-failed', fb_type, transfer_type, error_reason)
            self.emit('transfer-state-changed', "%s failed: %s" % (transfer_str, error_reason))

        c.close()

        return result

    def _http_progress_cb(self, download_total, download_done,
                          upload_total, upload_done, fb_type):
        logging.debug('_http_progress_cb')

        if download_total != 0:
            total = download_total
            done = download_done
            transfer_type = fb_types.FB_TRANSFER_DOWNLOAD
            transfer_str = "Download"
        else:
            total = upload_total
            done = upload_done
            transfer_type = fb_types.FB_TRANSFER_UPLOAD
            transfer_str = "Upload"

        if done == 0:
            self.emit('transfer-started', fb_type, transfer_type)
            state = "started"
        elif done == total:
            self.emit('transfer-completed', fb_type, transfer_type)
            self.emit('transfer-state-changed', "%s completed" % (transfer_str))
            state = "completed"
        else:
            if total != 0:
                self.emit('transfer-progress', fb_type, transfer_type,
                          float(done) / float(total))
                perc = int((float(done) / float(total))*100)
                state = "%d% done" % (perc)

        self.emit('transfer-state-changed', "%s %s" % (transfer_str, state))
