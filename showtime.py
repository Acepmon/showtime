import os
import urlparse
import json
import cvtools
import conf_app as conf
import hashlib
import time
import pagination as pg
import urllib

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader, defaults

from werkzeug.contrib.sessions import SessionMiddleware, FilesystemSessionStore


def get_hostname(url):
    return urlparse.urlparse(url).netloc


def url_for(endpoint, **values):
    url = '/' + str(endpoint)
    if values:
        url += '?' + urllib.urlencode(values)
    return url


class Showtime(object):
    def __init__(self, config):
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path), autoescape=True)
        self.jinja_env.filters['hostname'] = get_hostname

        self.url_map = Map([
            Rule('/', endpoint='index'),
            Rule('/admin_list/', endpoint='admin_list', defaults={'page': 1}),
            Rule('/admin_list/<int:page>', endpoint='admin_list'),
            Rule('/admin_toggle_pin', endpoint='admin_toggle_pin'),
            Rule('/admin_toggle_multiple_pin', endpoint='admin_toggle_multiple_pin'),
            Rule('/admin_remove_image', endpoint='admin_remove_image'),
            Rule('/admin_remove_multiple_image', endpoint='admin_remove_multiple_image'),
            Rule('/admin_multiple_image_action', endpoint='admin_multiple_image_action'),
            # Rule('/new_image', endpoint='new_image'),
            Rule('/upload_image', endpoint='upload_image'),
            Rule('/search_image', endpoint='search_image'),
            Rule('/sign_up', endpoint='sign_up'),
            Rule('/list', endpoint='list'),
            Rule('/recent', endpoint='recent'),
            Rule('/profile', endpoint='profile'),
            Rule('/password', endpoint='password'),
            Rule('/remove_ar', endpoint='remove_ar'),
            Rule('/login', endpoint='login'),
        ])

    def on_index(self, request):
        error = None
        sid = request.cookies.get('cookie_name')
        if sid is None:
            request.session = session_store.new()
        else:
            request.session = session_store.get(sid)
            
        action = request.args.get('action')
        user = request.cookies.get('cookie_user')
        
        if action == "Signout":
            response = redirect('/')
            response.set_cookie('cookie_name', '')
            return response

        username = request.form.get('username')
        password = request.form.get('password')
        logged_in, user_id = cvtools.admin_login(username, password)
        if logged_in:
            session_store.save(request.session)
            response = redirect('/admin_list')
            response.set_cookie('cookie_name', request.session.sid)
            response.set_cookie('cookie_user', username)
            return response
        return self.render_template('index.html', error=error, sid=sid, user=user)

    def on_admin_list(self, request, page):
        if request.cookies.get('cookie_name') is None or request.cookies.get('cookie_name') == '':
            return redirect('/')
        
        sid = request.cookies.get('cookie_name')
        keyword = request.args.get('keyword')
        
        # My changes start here
        user = request.cookies.get('cookie_user')
        if keyword is None:
            keyword = ""
        
        option = request.args.get('option')
        action = request.args.get('action')
        
        types = ['', '', '', '', '', '']
        
        if request.args.get('type-image') is not None:
            types[1] = int(request.args.get('type-image'))
        else:
            types[1] = conf.TAR_TYPE_NOTYPE
            
        if request.args.get('type-video') is not None:
            types[2] = int(request.args.get('type-video'))
        else:
            types[2] = conf.TAR_TYPE_NOTYPE
        
        if request.args.get('type-url') is not None:
            types[3] = int(request.args.get('type-url'))
        else:
            types[3] = conf.TAR_TYPE_NOTYPE
            
        if request.args.get('type-youtube') is not None:
            types[4] = int(request.args.get('type-youtube'))
        else:
            types[4] = conf.TAR_TYPE_NOTYPE
            
        if request.args.get('type-model') is not None:
            types[5] = int(request.args.get('type-model'))
        else:
            types[5] = conf.TAR_TYPE_NOTYPE

        if action == "Signout":
            response = redirect('/')
            response.set_cookie('cookie_name', '')
            return response
        
        search = request.args.get('search')
        # My changes end here
        
        page = cvtools.num(page)
        per_page = 10
        
        # My changes start here
        if option == "type":
            images, count = cvtools.get_list_type(keyword, None, None, 'i.created_at DESC, i.pinned DESC', page, per_page, types)
        elif option == "user":
            images, count = cvtools.get_list_user(keyword, None, None, 'i.created_at DESC, i.pinned DESC', page, per_page, types)
        else:
            images, count = cvtools.get_list(keyword, None, None, 'i.created_at DESC, i.pinned DESC', page, per_page, types)
        # My changes end here
            
        if not images and page != 1:
            return self.error_404()
        pagination = pg.Pagination(page, per_page, count)

        return self.render_template('admin_list.html', error=None, images=images, pagination=pagination,
                                    keyword=keyword, count=count, option=option, selected='true', types=types, search=search, sid=sid, user=user, abs_url=cvtools.get_abs_url, url_for=url_for, conf=conf)

    def on_admin_toggle_pin(self, request):
        if request.cookies.get('cookie_name') is None:
            return redirect('/')
        img_id = request.args.get('id')
        if img_id is not None:
            cvtools.toggle_pinned(img_id)
        return redirect(request.referrer)
    
    def on_admin_toggle_multiple_pin(self, request):
        if request.cookies.get('cookie_name') is None:
            return redirect('/')
        checked = request.args.getlist('checked[]')
        for img_id in checked:
            if img_id is not None:
                cvtools.toggle_pinned(img_id)
                    
        return redirect(request.referrer)

    def on_admin_remove_image(self, request):
        if request.cookies.get('cookie_name') is None:
            return redirect('/')
        error = 0
        img_id = request.args.get('id')
        if img_id is not None:
            image, count = cvtools.get_list(None, None, img_id)
            if len(image) > 0:
                image = image[0]
                if image['target_type'] == conf.TAR_TYPE_IMAGE:
                    tar = conf.UPLOAD_DIR_TAR_IMG + '/' + image['target']
                elif image['target_type'] == conf.TAR_TYPE_VIDEO:
                    tar = conf.UPLOAD_DIR_TAR_VIDEO + '/' + image['target']
                else:
                    tar = None

                if not cvtools.remove_image(img_id, conf.UPLOAD_DIR_SRC + '/' + image['src_name'], tar):
                    error = 1
        else:
            return redirect("/")
        
        return redirect(request.referrer)
    
    # My changes start here
    def on_admin_remove_multiple_image(self, request):
        if request.cookies.get('cookie_name') is None:
            return redirect('/')
        checked = request.args.getlist('checked[]')
        error = 0
        for img_id in checked:
            if img_id is not None:
                image, count = cvtools.get_list(None, None, img_id)
                if len(image) > 0:
                    image = image[0]
                    if image['target_type'] == conf.TAR_TYPE_IMAGE:
                        tar = conf.UPLOAD_DIR_TAR_IMG + '/' + image['target']
                    elif image['target_type'] == conf.TAR_TYPE_VIDEO:
                        tar = conf.UPLOAD_DIR_TAR_VIDEO + '/' + image['target']
                    else:
                        tar = None

                    if not cvtools.remove_image(img_id, conf.UPLOAD_DIR_SRC + '/' + image['src_name'], tar):
                        error = 1
                    
        return redirect(request.referrer)
    
    def on_admin_multiple_image_action(self, request):
        if request.cookies.get('cookie_name') is None:
            return redirect('/')
        
        action = request.args.get('action')
        checked = request.args.getlist('checked[]')
        
        error = 0
        if action == "pin":
            for img_id in checked:
                if img_id is not None:
                    if cvtools.is_pinned(img_id) is False:
                        cvtools.toggle_pinned(img_id)
                    else:
                        continue
        elif action == "unpin":
            for img_id in checked:
                if img_id is not None:
                    if cvtools.is_pinned(img_id) is True:
                        cvtools.toggle_pinned(img_id)
                    else:
                        continue
        elif action == "remove":
            for img_id in checked:
                if img_id is not None:
                    image, count = cvtools.get_list(None, None, img_id)
                    if len(image) > 0:
                        image = image[0]
                        if image['target_type'] == conf.TAR_TYPE_IMAGE:
                            tar = conf.UPLOAD_DIR_TAR_IMG + '/' + image['target']
                        elif image['target_type'] == conf.TAR_TYPE_VIDEO:
                            tar = conf.UPLOAD_DIR_TAR_VIDEO + '/' + image['target']
                        else:
                            tar = None

                        if not cvtools.remove_image(img_id, conf.UPLOAD_DIR_SRC + '/' + image['src_name'], tar):
                            error = 1
        
        return redirect(request.referrer)
    # My changes end here

    def on_new_image(self, request):
        return self.render_template('new_image.html', error=None)

    def on_upload_image(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            session_id = request.form.get('session_id')
            title = request.form.get('title')
            src_img = 'src_img' in request.files and request.files['src_img'] or None
            tar_image = 'target_image' in request.files and request.files['target_image'] or None
            tar_video = 'target_video' in request.files and request.files['target_video'] or None
            tar_type = request.form.get('target_type')
            tar_url = request.form.get('target_url')
            tar_url_yt = request.form.get('target_url_yt')
            tar_model = request.form.get('target_model')
            tar_pos = request.form.get('target_pos')
            vid_w = request.form.get('video_w') is None and "512" or request.form.get('video_w')
            vid_h = request.form.get('video_h') is None and "512" or request.form.get('video_h')

            if tar_type is None:
                tar_type = ''
            else:
                tar_type = int(tar_type)

            if src_img is None:
                res['error_msg'] = 'src_img not found'
            elif tar_type in [None, '']:
                res['error_msg'] = 'target_type missing. valid values: [1,2,3,4]'
            elif tar_type in [conf.TAR_TYPE_IMAGE, conf.TAR_TYPE_VIDEO] and tar_image is None and tar_video is None:
                res['error_msg'] = 'target img/video not found'
            elif tar_type == conf.TAR_TYPE_URL and tar_url in [None, '']:
                res['error_msg'] = 'target_url missing'
            elif tar_type == conf.TAR_TYPE_URL_YT and tar_url_yt in [None, '']:
                res['error_msg'] = 'target_url_yt missing'
            elif tar_type == conf.TAR_TYPE_MODEL and tar_model in [None, '']:
                res['error_msg'] = 'target_model missing'
            elif title in [None, '']:
                res['error_msg'] = 'title missing'
            elif not cvtools.user_logged_in(user_id, session_id):
                res['error'] = 2  # not logged in
                res['error_msg'] = 'please login'
            elif not vid_w.isdigit() or not vid_h.isdigit():
                res['error_msg'] = 'video height and width must be an integer'
            else:
                if tar_type == conf.TAR_TYPE_IMAGE:
                    target = cvtools.upload_file(conf.UPLOAD_DIR_TAR_IMG, tar_image)
                elif tar_type == conf.TAR_TYPE_VIDEO:
                    target = cvtools.upload_file(conf.UPLOAD_DIR_TAR_VIDEO, tar_video)
                    if target is not False:
                        target = cvtools.convert_video(os.path.join(conf.UPLOAD_DIR_TAR_VIDEO, target), vid_w, vid_h)
                elif tar_type == conf.TAR_TYPE_URL:
                    target = tar_url
                elif tar_type == conf.TAR_TYPE_URL_YT:
                    target = tar_url_yt
                elif tar_type == conf.TAR_TYPE_MODEL:
                    target = tar_model
                else:
                    target = False

                src_img_name = cvtools.upload_file(conf.UPLOAD_DIR_SRC, src_img)
                if src_img_name is not False and target != '':
                    file_id = cvtools.insert_file(src_img_name, tar_type, target, user_id, title, tar_pos)
                    if file_id > 0:
                        indexed = cvtools.index_image(conf.UPLOAD_DIR_SRC + '/' + src_img_name, file_id)
                    if indexed is True:
                        res['error'] = 0
                    else:
                        res['error_msg'] = 'image indexing failed'
                else:
                    res['error_msg'] = 'upload failed'
        else:
            res['error_msg'] = 'request is not POST'

        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')

    def on_search_image(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            session_id = request.form.get('session_id')
            search_img = 'img' in request.files and request.files['img'] or None
            if search_img is not None:
                search_img_name = cvtools.upload_file(conf.UPLOAD_DIR_TEMP, search_img)
                if cvtools.resize_image(conf.UPLOAD_DIR_TEMP + '/' + search_img_name):
                    if search_img_name is not False:
                        timer_start = time.clock()
                        search_result = cvtools.search_image(conf.UPLOAD_DIR_TEMP + '/' + search_img_name)
                        res['time'] = time.clock() - timer_start
                        if search_result is not False:
                            search_result = search_result[0]
                            res['error'] = 0
                            res['found'] = 1
                            res['title'] = search_result['title']
                            res['user'] = search_result['username']
                            res['src_img'] = cvtools.get_abs_url(conf.UPLOAD_DIR_SRC[1:], search_result['src_name'])
                            res['target_type'] = search_result['target_type']
                            res['target_pos'] = search_result['pos']
                            if search_result['target_type'] == conf.TAR_TYPE_IMAGE:
                                res['target'] = cvtools.get_abs_url(conf.UPLOAD_DIR_TAR_IMG[1:],
                                                                    search_result['target'])
                            elif search_result['target_type'] == conf.TAR_TYPE_VIDEO:
                                res['target'] = cvtools.get_abs_url(conf.UPLOAD_DIR_TAR_VIDEO[1:],
                                                                    search_result['target'])
                            else:
                                res['target'] = search_result['target']
                            # adding views
                            if cvtools.user_logged_in(user_id, session_id):
                                cvtools.insert_user_view(user_id, search_result['id'])
                        else:
                            res['error'] = 0
                            res['found'] = 0
                    else:
                        res['error_msg'] = 'search image upload failed'
                else:
                    res['error_msg'] = 'error while resizing image'
            else:
                res['error_msg'] = 'img not recieved'
        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')

    def on_remove_ar(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            session_id = request.form.get('session_id')
            ar_id = request.form.get('ar_id')

            if ar_id is not None:
                if cvtools.user_logged_in(user_id, session_id):
                    image, count = cvtools.get_list(None, None, ar_id)
                    if len(image) > 0:
                        image = image[0]
                        if image['user_id'] != int(user_id):
                            res['error_msg'] = 'this ar is not yours'
                        else:
                            if image['target_type'] == conf.TAR_TYPE_IMAGE:
                                tar = conf.UPLOAD_DIR_TAR_IMG + '/' + image['target']
                            elif image['target_type'] == conf.TAR_TYPE_VIDEO:
                                tar = conf.UPLOAD_DIR_TAR_VIDEO + '/' + image['target']
                            else:
                                tar = None

                            if cvtools.remove_image(ar_id, conf.UPLOAD_DIR_SRC + '/' + image['src_name'], tar):
                                res['error'] = 0
                            else:
                                res['error_msg'] = 'delete unsuccessful'
                    else:
                        res['error_msg'] = 'image with id (' + ar_id + ') not found'
                else:
                    res['error'] = 2
                    res['error_msg'] = 'please login'
            else:
                res['error_msg'] = 'ar_id missing'
        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')

    def on_profile(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            session_id = request.form.get('session_id')
            find_user_id = request.form.get('find_user_id')

            if find_user_id is None:
                find_user_id = user_id

            if cvtools.user_logged_in(user_id, session_id):
                user = cvtools.get_user(find_user_id)
                result = {}
                if len(user) > 0:
                    res['found'] = 1
                    result['user_id'] = user[0]['id']
                    result['username'] = user[0]['username']
                    result['email'] = user[0]['email']
                    result['registered_at'] = user[0]['created_at'].isoformat()
                else:
                    res['found'] = 0

                res['error'] = 0
                res['result'] = result
            else:
                res['error'] = 2
                res['error_msg'] = 'session ended. please login'
        else:
            res['error_msg'] = 'request is not GET'

        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')

    def on_password(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            session_id = request.form.get('session_id')
            password = request.form.get('password')
            new_password = request.form.get('new_password')

            if new_password is None:
                res['error_msg'] = 'new_password required'
            else:
                if cvtools.user_logged_in(user_id, session_id):
                    user = cvtools.get_user(user_id)
                    if len(user) > 0:
                        pw_user = str(user[0]['password'])
                        pw_input = str(hashlib.md5(password).hexdigest())
                        if pw_user != pw_input:
                            res['error_msg'] = 'incorrect password'
                        else:
                            cvtools.update_user_password(user_id, new_password)
                            res['error'] = 0
                    else:
                        res['found'] = 0
                        res['error_msg'] = 'user not found'
                else:
                    res['error'] = 2
                    res['error_msg'] = 'session ended. please login'
        else:
            res['error_msg'] = 'request is not GET'

        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')


    def on_list(self, request):
        res = {'error': 1}
        if request.method == 'GET':
            keyword = request.args.get('keyword')
            user_id = request.args.get('user_id')
            page = cvtools.num(request.args.get('page'))
            per_page = cvtools.num(request.args.get('per_page'))
            images, count = cvtools.get_list(keyword, user_id, None, "i.created_at DESC", page, per_page)
            result = []
            for img in images:
                temp = {}
                temp['ar_id'] = img['id']
                temp['src_img'] = cvtools.get_abs_url(conf.UPLOAD_DIR_SRC[1:], img['src_name'])
                temp['target_type'] = img['target_type']
                if temp['target_type'] == conf.TAR_TYPE_IMAGE:
                    temp['target'] = cvtools.get_abs_url(conf.UPLOAD_DIR_TAR_IMG[1:], img['target'])
                elif temp['target_type'] == conf.TAR_TYPE_VIDEO:
                    temp['target'] = cvtools.get_abs_url(conf.UPLOAD_DIR_TAR_VIDEO[1:], img['target'])
                else:
                    temp['target'] = img['target']
                temp['title'] = img['title']
                temp['user'] = img['username']
                temp['created_at'] = img['created_at'].isoformat()
                result.append(temp)

            res['error'] = 0
            res['result'] = result
            res['total'] = count
        else:
            res['error_msg'] = 'request is not GET'

        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')

    def on_recent(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            session_id = request.form.get('session_id')

            if cvtools.user_logged_in(user_id, session_id):
                images = cvtools.get_recent_images(user_id)
                result = []
                for img in images:
                    temp = {}
                    temp['ar_id'] = img['id']
                    temp['src_img'] = cvtools.get_abs_url(conf.UPLOAD_DIR_SRC[1:], img['src_name'])
                    temp['target_type'] = img['target_type']
                    if temp['target_type'] == conf.TAR_TYPE_IMAGE:
                        temp['target'] = cvtools.get_abs_url(conf.UPLOAD_DIR_TAR_IMG[1:], img['target'])
                    elif temp['target_type'] == conf.TAR_TYPE_VIDEO:
                        temp['target'] = cvtools.get_abs_url(conf.UPLOAD_DIR_TAR_VIDEO[1:], img['target'])
                    else:
                        temp['target'] = img['target']
                    temp['title'] = img['title']
                    temp['user'] = img['username']
                    temp['viewed_at'] = img['created_at'].isoformat()
                    result.append(temp)

                res['error'] = 0
                res['result'] = result
            else:
                res['error'] = 2
                res['error_msg'] = 'session ended. please login'
        else:
            res['error_msg'] = 'request is not POST'

        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')


    def on_sign_up(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            password_confirm = request.form.get('password_confirm')
            email = request.form.get('email')

            if (username is None or email is None or password is None):
                res['error_msg'] = 'missing field (username,email,password)'
            elif (password != password_confirm):
                res['error_msg'] = 'password and password_confirm dont match'
            elif (cvtools.username_exists(username)):
                res['error_msg'] = 'username already exists'
            elif (cvtools.useremail_exists(email)):
                res['error_msg'] = 'user email already exists'
            else:
                inserted_id, session_id = cvtools.insert_user(username, email, password)
                if inserted_id != 0:
                    res['error'] = 0
                    res['user_id'] = inserted_id
                    res['session_id'] = session_id
                else:
                    res['error_msg'] = 'error @user_creation'
        else:
            res['error_msg'] = 'request is not POST'

        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')

    def on_login(self, request):
        res = {'error': 1}
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('username')
            password = request.form.get('password')
            if username is None:
                res['error_msg'] = 'username or email required'
            elif password is None:
                res['error_msg'] = 'password required'
            else:
                logged_in, session_id, user_id = cvtools.do_login(username, email, password)
                if logged_in == True:
                    res['error'] = 0
                    res['session_id'] = session_id
                    res['user_id'] = user_id
                else:
                    res['error_msg'] = 'username or password is wrong'
        else:
            res['error_msg'] = 'request is not POST'

        response_str = json.dumps([res])
        return Response(response_str, mimetype='application/json')

    def error_404(self):
        response = self.render_template('404.html')
        response.status_code = 404
        return response

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html')

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **values)
        except NotFound, e:
            return self.error_404()
        except HTTPException, e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def create_app():
    app = Showtime({})
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/static': os.path.join(os.path.dirname(__file__), 'static')
    })
    # open the session support using SessionMiddleware
    global session_store
    session_store = FilesystemSessionStore(path="./sess", renew_missing=True)
    app = SessionMiddleware(app, session_store)
    return app


if __name__ == '__main__':
    from werkzeug.serving import run_simple

    app = create_app()
    run_simple(conf.HOSTIP, conf.HOSTPORT, app, use_debugger=True, use_reloader=True, threaded=True)
