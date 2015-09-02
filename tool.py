import os
import urlparse
import json
import cvtools as tools
import conf_app as conf
import conf_db as db
import cv2


def resize_images(imgPath):
    image = cv2.imread(imgPath, cv2.IMREAD_UNCHANGED)
    if image is not None:
        maxSize = conf.IMAGE_MAX_SIZE
        if image.shape[0] > image.shape[1]:
            dim = (int(maxSize / float(image.shape[0]) * image.shape[1]), maxSize)
        else:
            dim = (maxSize, int(maxSize / float(image.shape[1]) * image.shape[0]))
        resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
        cv2.imwrite(imgPath, resized)
        return True
    return False


def reindex_images(mysqlid, imgPath):
    image = cv2.imread(imgPath, cv2.IMREAD_UNCHANGED)
    if image is not None:
        surf = cv2.SURF(800)
        # surf.extended = False
        surf.upright = True
        kp, desc = surf.detectAndCompute(image, None)

        if desc.size > 0:
            conn = tools.sqlite_connect(db.SQLITE_DB + '_surf.db')
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS descriptor(mysql_id INTEGER, arr array)")
            cur.execute("INSERT INTO descriptor (mysql_id, arr) VALUES (?, ?)", (mysqlid, desc))
            conn.commit()
        return True


if __name__ == '__main__':
    # dbclean
    # conn = tools.sqlite_connect(db.SQLITE_DB + '_surf.db')
    # cur = conn.cursor()
    # cur.execute("DELETE FROM descriptor WHERE 1=1")
    # conn.commit()

    images = tools.mysql_fetch("SELECT id, src_name FROM image", {})
    for img in images:
        # resize_images(conf.UPLOAD_DIR_SRC + '/' + img[1])
        reindex_images(img[0], conf.UPLOAD_DIR_SRC + '/' + img[1])
    print 'k'