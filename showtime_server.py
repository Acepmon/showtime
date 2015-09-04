import cherrypy
from showtime import create_app

# server = wsgiserver.CherryPyWSGIServer(('202.70.46.184', 44000), create_app())
# try:
    # server.start()
# except KeyboardInterrupt:
    # server.stop()

if __name__ == '__main__':

    # Mount the application
    cherrypy.tree.graft(create_app(), "/")

    # Unsubscribe the default server
    cherrypy.server.unsubscribe()

    # Instantiate a new server object
    server = cherrypy._cpserver.Server()

    # Configure the server object
    ip = "127.0.0.1"
    port = 44000
    server.socket_host = ip
    server.socket_port = port
    server.thread_pool = 100
    
    appserver_error_log = './log/error.log'
    appserver_access_log = './log/access.log'
    cherrypy.config.update({
        'server.socket_host': ip,
        'server.socket_port': port,
        'log.error_file': appserver_error_log,
        'log.access_file': appserver_access_log
    })

    # For SSL Support
    # server.ssl_module            = 'pyopenssl'
    # server.ssl_certificate       = 'ssl/certificate.crt'
    # server.ssl_private_key       = 'ssl/private.key'
    # server.ssl_certificate_chain = 'ssl/bundle.crt'

    # Subscribe this server
    server.subscribe()

    # Example for a 2nd server (same steps as above):
    # Remember to use a different port

    # server2             = cherrypy._cpserver.Server()

    # server2.socket_host = "0.0.0.0"
    # server2.socket_port = 8081
    # server2.thread_pool = 30
    # server2.subscribe()

    # Start the server engine (Option 1 *and* 2)

    cherrypy.engine.start()
    cherrypy.engine.block()
