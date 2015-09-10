from datetime import time
import os
import io
import cv2
import sys
import numpy as np
import uuid
import sqlite3
import mysql.connector
import conf_app as conf
import conf_db as db
import subprocess as sp
import time

from pyflann import *
from numpy import *
from numpy.random import *
# from matplotlib import pyplot as plt


def num(s):
    if s is None:
        return 0
    try:
        return int(s)
    except ValueError:
        return float(s)


def adapt_array(arr):
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return buffer(out.read())


def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


def sqlite_connect(db):
    con = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
    return con


def mysql_connect():
    con = mysql.connector.connect(user=db.MYSQL_USER, password=db.MYSQL_PASS, host=db.MYSQL_HOST, database=db.MYSQL_DB)
    return con


def mysql_exec(query, data):
    last_inserted_id = 0
    con = mysql_connect()
    try:
        cursor = con.cursor()
        cursor.execute((query), data)
        con.commit()
        last_inserted_id = cursor.lastrowid
        if last_inserted_id is 0 and cursor.rowcount > 0:
            last_inserted_id = True
    finally:
        cursor.close()
        con.close()
    return last_inserted_id


def mysql_fetch(query, data):
    result = False
    con = mysql_connect()
    try:
        cursor = con.cursor(dictionary=True)
        cursor.execute((query), data)
        result = cursor.fetchall()
    finally:
        cursor.close()
        con.close()
    return result


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in conf.ALLOWED_EXTENSIONS

# Converts np.array to TEXT when inserting
sqlite3.register_adapter(np.ndarray, adapt_array)
# Converts TEXT to np.array when selecting
sqlite3.register_converter("array", convert_array)


def upload_file(upload_dir, file):
    if file and allowed_file(str(file.filename).lower()):
        f, ext = os.path.splitext(file.filename)
        filename = str(uuid.uuid4()) + ext.lower()
        file.save(os.path.join(upload_dir, filename))
        return filename
    return False


def get_abs_url(directory, filename, serve_media=True):
    return 'http://' + conf.HOSTIP + ':' + str(
        conf.HOSTPORT_SERVE if serve_media is True else conf.HOSTPORT) + directory + '/' + filename


def insert_file(src_img_name, tar_type, target, user_id, title, pos):
    if user_id is None:
        user_id = 0
    if pos is None:
        pos = ''
    query = "INSERT INTO image (src_name, target_type, target, user_id, title, pos) VALUES (%s, %s, %s, %s, %s, %s)"
    data = (src_img_name, tar_type, target, user_id, title, pos)
    return mysql_exec(query, data)


def extract_image(img, rotated=False):
    img = cv2.imread(img, cv2.IMREAD_UNCHANGED)
    if img is not None:
        images = []
        descriptors = []
        if len(img.shape) in [3, 4]:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            images.append(gray)
            if rotated:
                img90 = rotate_image(gray)
                images.append(img90)
                img180 = rotate_image(img90)
                images.append(img180)
                img270 = rotate_image(img180)
                images.append(img270)
            for im in images:
                if conf.ALGORITHM == 'fast':
                    fast = cv2.FastFeatureDetector()  # threshold=10, suppress=false
                    kp = fast.detect(im, None)
                elif conf.ALGORITHM == 'sift':
                    sift = cv2.SIFT()
                    kp = sift.detect(im, None)
                    desc = sift.compute(im, kp)
                elif conf.ALGORITHM == 'surf':
                    surf = cv2.SURF(800)
                    surf.upright = True
                    # surf.extended = False  # False to get 64-dim descriptors.
                    kp, desc = surf.detectAndCompute(im, None)
                if rotated is False:
                    return desc
                descriptors.append(desc)
            return descriptors
    return False


def resize_image(img_path, keep_aspect_ratio=False):
    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    if img is not None:
        max_size = conf.IMAGE_MAX_SIZE
        if keep_aspect_ratio:
            if img.shape[0] > img.shape[1]:
                dim = (int(max_size / float(img.shape[0]) * img.shape[1]), max_size)
            else:
                dim = (max_size, int(max_size / float(img.shape[1]) * img.shape[0]))
        else:
            dim = (max_size, max_size)
        res = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
        cv2.imwrite(img_path, res)
        return True
    return False


def rotate_image(img, deg=90):
    if img is not None:
        # grab the dimensions of the image and calculate the center
        # of the image
        (h, w) = img.shape[:2]
        center = (w / 2, h / 2)

        # rotate the image by 180 degrees
        M = cv2.getRotationMatrix2D(center, deg, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h))
        return rotated
    return False


def convert_video(vid_path, w, h):
    f, ext = os.path.splitext(os.path.basename(vid_path))
    dir = os.path.abspath(vid_path + '/..')

    if ext.lower() == '.mov':
        # command = ["/usr/local/bin/ffmpeg", "-i", dir + "/" + f + ext, "-codec:v", "libx264", "-profile:v", "main",
        # "-refs", "11", "-preset", "slow", "-b:v", "500k", "-maxrate", "400k", "-bufsize", "800k", "-vf",
        # "scale=iw:ih", "-threads", "0", "-codec:a", "libfdk_aac", "-b:a", "128k", dir + "/" + f + ".mp4"]
        command = ["/usr/local/bin/ffmpeg", "-i", dir + "/" + f + ext, "-c:v", "libx264", "-profile:v", "baseline",
                   "-vf", "scale=iw:ih", "-threads", "0", "-codec:a", "libfdk_aac", "-b:a", "128k", "-movflags",
                   "faststart", dir + "/" + f + ".mp4"]
        output, error = sp.Popen(command, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE).communicate()
        ext = '.mp4'

    command = ["/usr/local/bin/ffmpeg", "-i", dir + "/" + f + ext, "-r", "20", "-codec:v", "mpeg4", "-b:v", "150k",
               "-s", w + "x" + h, "-codec:a", "libfdk_aac", "-b:a", "48k", "-ar", "22050",
               dir + "/" + f + ".3g2"]
    output, error = sp.Popen(command, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE).communicate()
    return f + '.3g2'


def index_image(src_img, mysql_id):
    if resize_image(src_img, False):
        desc = extract_image(src_img)
        if desc is None:
            desc = np.zeros((1, 128), dtype='f')
        if desc is not False:
            conn = sqlite_connect(db.SQLITE_DB + '_' + conf.ALGORITHM + '.db')
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS descriptor(mysql_id INTEGER, arr array)")
            cur.execute("INSERT INTO descriptor (mysql_id, arr) VALUES (?, ?)", (mysql_id, desc))
            conn.commit()
            return True
    return False


def remove_image(img_id, img_src, tar):
    if int(img_id) > 0:
        conn = sqlite_connect(db.SQLITE_DB + '_' + conf.ALGORITHM + '.db')
        cur = conn.cursor()
        cur.execute("DELETE FROM descriptor WHERE mysql_id = ?", (img_id,))
        conn.commit()

        mysql_exec("DELETE FROM showtime.image WHERE id = %(id)s", {'id': img_id})

        if img_src is not None:
            try:
                os.remove(img_src)
            except:
                pass
        if tar is not None:
            try:
                os.remove(tar)
                os.remove(os.path.splitext(tar)[0] + '.mp4')
                os.remove(os.path.splitext(tar)[0] + '.mov')
                os.remove(os.path.splitext(tar)[0] + '.3g2')
            except:
                pass

        return True
    return False


def search_image(img):
    desc = extract_image(img, conf.ENABLE_ROTATED_SEARCH)
    if desc is not False and desc is not None:
        con = sqlite_connect(db.SQLITE_DB + '_' + conf.ALGORITHM + '.db')
        cur = con.cursor()
        cur.execute("SELECT mysql_id, arr FROM descriptor")
        data = cur.fetchall()

        idx = np.array([])
        dataset = None
        for i in data:
            if dataset is None:
                dataset = i[1]
                idx = np.linspace(i[0], i[0], len(i[1]))
            else:
                dataset = np.concatenate((dataset, i[1]))
                idx = np.concatenate((idx, np.linspace(i[0], i[0], len(i[1]))))

        flann = FLANN()
        params = flann.build_index(dataset, algorithm="kdtree", trees=1, target_precision=conf.SEARCH_PRECISION,
                                   log_level="info", cores=4)

        if conf.ENABLE_ROTATED_SEARCH is False:
            desc = [desc]

        arr = []
        for d in desc:
            timer_start = time.clock()
            result, dists = flann.nn_index(d, 5, checks=params["checks"])
            print 'time for every search:', time.clock() - timer_start

            uniq, idx_count = np.unique(idx[result], return_counts=True)
            top_results = np.argwhere(idx_count > len(d) * conf.SEARCH_PRECISION)
            top_counts = idx_count[top_results]
            top_ids = uniq[top_results]
            # print uniq
            # print idx_count
            # print len(d)

            t = np.hstack((top_ids, top_counts))  # getting [id,count] array
            if len(t) > 0:
                arr.append(t)

        flann.delete_index()

        if len(arr) > 0:
            sub_case = ''
            list_ids = []
            list_sub = []
            for i in arr:
                list_sub.append((str(int(i[0][0])), str(int(i[0][1]))))
                list_ids.append((str(int(i[0][0]))))
            ids = ",".join(list_ids)

            # print 'ids', ids
            # print 'sub', list_sub
            # print 'listIDs', list_ids

            for i in list_sub:
                sub_case += " WHEN i2.id = " + i[0] + " THEN " + i[1]  # adding rank

            q = "SELECT i.id, i.src_name, i.target_type, i.target, i.user_id, i.title, u.username, i.pos, i.pinned " \
                "FROM image i " \
                "LEFT JOIN user u ON u.id = i.user_id " \
                "LEFT JOIN (" \
                "SELECT i2.id, (CASE " + sub_case + " ELSE 0 END) AS rank " \
                                                    "FROM image i2 " \
                                                    "WHERE i2.id IN (" + ids + ")) AS sub ON sub.id = i.id " \
                                                                               "WHERE i.id IN (" + ids + ") " \
                                                                                                         "ORDER BY i.pinned DESC, sub.rank DESC LIMIT 1"

            result = mysql_fetch(q, {})

            return result
    return False

def get_list(keyword=None, user_id=None, image_id=None, order_by="i.created_at DESC", page=1, per_page=30):
    arr = []
    if keyword is not None:
        arr.append('i.title LIKE %(kw)s')
    else:
        keyword = ""

    if user_id is not None:
        arr.append('i.user_id = %(uid)s')
    else:
        user_id = ""

    if image_id is not None:
        arr.append('i.id = %(id)s')
    else:
        image_id = ""

    if page in [None, 0]:
        page = 1

    if per_page in [None, 0]:
        per_page = 30

    where = ""
    if (len(arr) > 0):
        where = "WHERE " + " AND ".join(arr)

    query = "SELECT i.id, i.src_name, i.target_type, i.target, i.user_id, i.title, u.username, i.created_at, i.pinned " \
            "FROM image i " \
            "LEFT JOIN showtime.user u ON u.id = i.user_id " \
            "" + where + " ORDER BY " + order_by + " LIMIT " + str((page - 1) * int(per_page)) + ", " + str(per_page)
    query_count = "SELECT COUNT(i.id) as 'numrows' " \
                  "FROM image i " \
                  "LEFT JOIN showtime.user u ON u.id = i.user_id " + where
    data = {'kw': keyword + "%", 'uid': user_id, 'id': image_id}
    result = mysql_fetch(query, data)
    result_count = mysql_fetch(query_count, data)
    return result, result_count[0]['numrows']

# My changes start here
def get_list_type(keyword=None, user_id=None, image_id=None, order_by="i.created_at DESC", page=1, per_page=30):
    arr = []
    if keyword is not None:
        arr.append('i.target_type LIKE %(kw)s')
    else:
        keyword = ""

    if user_id is not None:
        arr.append('i.user_id = %(uid)s')
    else:
        user_id = ""

    if image_id is not None:
        arr.append('i.id = %(id)s')
    else:
        image_id = ""

    if page in [None, 0]:
        page = 1

    if per_page in [None, 0]:
        per_page = 30

    where = ""
    if (len(arr) > 0):
        where = "WHERE " + " AND ".join(arr)

    query = "SELECT i.id, i.src_name, i.target_type, i.target, i.user_id, i.title, u.username, i.created_at, i.pinned " \
            "FROM image i " \
            "LEFT JOIN showtime.user u ON u.id = i.user_id " \
            "" + where + " ORDER BY " + order_by + " LIMIT " + str((page - 1) * int(per_page)) + ", " + str(per_page)
    query_count = "SELECT COUNT(i.id) as 'numrows' " \
                  "FROM image i " \
                  "LEFT JOIN showtime.user u ON u.id = i.user_id " + where
    data = {'kw': keyword + "%", 'uid': user_id, 'id': image_id}
    result = mysql_fetch(query, data)
    result_count = mysql_fetch(query_count, data)
    return result, result_count[0]['numrows']

def get_list_user(keyword=None, user_id=None, image_id=None, order_by="i.created_at DESC", page=1, per_page=30):
    arr = []
    if keyword is not None:
        arr.append('u.username LIKE %(kw)s')
    else:
        keyword = ""

    if user_id is not None:
        arr.append('i.user_id = %(uid)s')
    else:
        user_id = ""

    if image_id is not None:
        arr.append('i.id = %(id)s')
    else:
        image_id = ""

    if page in [None, 0]:
        page = 1

    if per_page in [None, 0]:
        per_page = 30

    where = ""
    if (len(arr) > 0):
        where = "WHERE " + " AND ".join(arr)

    query = "SELECT i.id, i.src_name, i.target_type, i.target, i.user_id, i.title, u.username, i.created_at, i.pinned " \
            "FROM image i " \
            "LEFT JOIN showtime.user u ON u.id = i.user_id " \
            "" + where + " ORDER BY " + order_by + " LIMIT " + str((page - 1) * int(per_page)) + ", " + str(per_page)
    query_count = "SELECT COUNT(i.id) as 'numrows' " \
                  "FROM image i " \
                  "LEFT JOIN showtime.user u ON u.id = i.user_id " + where
    data = {'kw': keyword + "%", 'uid': user_id, 'id': image_id}
    result = mysql_fetch(query, data)
    result_count = mysql_fetch(query_count, data)
    return result, result_count[0]['numrows']
# My changes end here


def toggle_pinned(img_id):
    if not img_id.isdigit():
        return False
    query = "UPDATE image SET pinned = ABS(pinned-1) WHERE id = %(id)s"
    data = {'id': img_id}
    res = mysql_exec(query, data)
    if res:
        return True
    return False


def get_user(user_id):
    if user_id.isdigit():
        query = "SELECT id, username, email, created_at, password FROM showtime.user WHERE id = %(id)s"
        data = {'id': user_id}
        return mysql_fetch(query, data)
    return None


def update_user_password(user_id, newpass):
    query = "UPDATE user SET password = MD5(%s) WHERE id = %s"
    data = (newpass, user_id)
    mysql_exec(query, data)
    return True


def get_recent_images(user_id):
    result = mysql_fetch(
        "SELECT i.id, i.src_name, i.target_type, i.target, i.user_id, i.title, u.username, uv.created_at "
        "FROM image i "
        "LEFT JOIN showtime.user u ON u.id = i.user_id "
        "LEFT JOIN user_view uv ON uv.image_id = i.id "
        "WHERE uv.user_id = %(id)s "
        "ORDER BY uv.created_at DESC "
        "LIMIT 0, 30", {'id': user_id})
    return result


def username_exists(username):
    if len(username) >= conf.USERNAME_MIN_LENGTH:
        res = mysql_fetch("SELECT * FROM user WHERE username = %(username)s", {'username': username})
        if len(res) > 0:
            return True
    return False


def useremail_exists(email):
    res = mysql_fetch("SELECT * FROM user WHERE email = %(email)s", {'email': email})
    if len(res) > 0:
        return True
    return False


def insert_user(username, email, password):
    if len(username) >= conf.USERNAME_MIN_LENGTH:
        sess_id = str(uuid.uuid4())
        query = "INSERT INTO user (username, email, password, session_id) VALUES (%s, %s, MD5(%s), %s)"
        data = (username, email, password, sess_id)
        return mysql_exec(query, data), sess_id  # return inserted id
    return 0, ''


def do_login(username, email, password):
    if username is not None or email is not None:
        res = mysql_fetch("SELECT * FROM user WHERE (username = %(username)s AND password = MD5(%(password1)s)) "
                          "OR (email = %(email)s AND password = MD5(%(password2)s)) ",
                          {'username': username, 'password1': password, 'email': email, 'password2': password})
    if len(res) > 0:
        sess_id = str(uuid.uuid4())
        query = "UPDATE user SET session_id = %s WHERE id = %s"
        data = (sess_id, res[0]['id'])
        mysql_exec(query, data)
        return True, sess_id, res[0]['id']
    return False, '', 0

# My changes start here
def get_id_by_sess(session_id):
    if session_id is not None:
        user = mysql_fetch("SELECT * FROM user WHERE session_id = %(session_id)s limit 1", {'session_id' : session_id})
        return True, user[0]['id']
    return False, ''

def do_logout(user_id):
    if user_id is not None:
        query = "UPDATE user SET session_id = %s WHERE id = %s"
        data = ('', user_id)
        mysql_exec(query,data)
        return True
    return False
# My changes end here

def user_logged_in(user_id, session_id):
    res = mysql_fetch("SELECT * FROM user WHERE id = %(id)s AND session_id = %(sess)s",
                      {'id': user_id, 'sess': session_id})
    if len(res) > 0:
        return True
    return False


def insert_user_view(user_id, image_id):
    if user_id > 0 and image_id > 0:
        query = "INSERT INTO user_view (user_id, image_id) VALUES (%s, %s) ON DUPLICATE KEY UPDATE created_at = NOW()"
        data = (user_id, image_id)
        return mysql_exec(query, data)  # return inserted id
    return False


def admin_login(username, password):
    if username is not None:
        res = mysql_fetch("SELECT * FROM user WHERE (username = %(username)s AND password = MD5(%(password)s)) ",
                          {'username': username, 'password': password})
        if len(res) > 0:
            return True, res[0]['id']
    return False, 0