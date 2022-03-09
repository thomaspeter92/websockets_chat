
import json
import os
import logging
import redis
import gevent
from flask import Flask, render_template, g, request
from flask_sockets import Sockets
from datetime import timedelta

REDIS_URL = os.environ['REDIS_URL']
REDIS_CHAN = 'chat'

app = Flask(__name__)
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)
app.debug = 'DEBUG' in os.environ

sockets = Sockets(app)
redis = redis.from_url(REDIS_URL)

class ChatBackend(object):
    def __init__(self):
        self.clients = list()
        self.pubsub = redis.pubsub()
        self.pubsub.subscribe(REDIS_CHAN)

    def __iter_data(self):
        for message in self.pubsub.listen():
            data = message.get('data')
            if message['type'] == 'message':
                app.logger.info(u'Sending message: {}'.format(data))
                json_data = json.loads(data)
                yield json.dumps(json_data)

    def register(self, client):
        self.clients.append(client)

    def send(self, client, data):
        try:
            client.send(data)

        except Exception:
            self.clients.remove(client)

    def run(self):
        for data in self.__iter_data():
            for client in self.clients:
                gevent.spawn(self.send, client, data)

    def start(self):
        gevent.spawn(self.run)


    """
        -Added rate limiting to the web socket back end. 
        -Uses public IP address to identify users (not reccomended for real production website)
        -Saves IP and limit to a redis database in memory.
    """
    def check_request(self, key, limit, time):
        # USE SETNX TO ADD IP TO REDIS
        if redis.setnx(key, limit):
            print('added to redis')

            # EXPIRE METHOD WILL DELETE THE ENTRY AFTER SPECIFIED TIME
            redis.expire(key, int(timedelta(seconds=time).total_seconds()))

        current_limit = redis.get(key)
        print(current_limit)
        # CHECK THEY HAVE NOT REACHED THEIR LIMIT
        if current_limit and int(current_limit) > 0:
            redis.decrby(key, 1)
            return False
        return True


chats = ChatBackend()
chats.start()


@sockets.route('/submit')
def inbox(ws):
    """Receives incoming chat messages, inserts them into Redis."""



    while not ws.closed:
        gevent.sleep(0.1)
        message = ws.receive()

        # IF THE CHECK REQUEST FUNC RETURNS FALSE, THEN WE SEND MESSAGE.
        # PASS IN THE LIMIT AND TIME FRAME HERE AS PARAMETERS
        if chats.check_request(request.remote_addr,5,20) and message:
            print("Message caught & NOT inserted")
            pass
        else:
            app.logger.info(u'Inserting message: {}'.format(message))
            redis.publish(REDIS_CHAN, message)


@sockets.route('/receive')
def outbox(ws):
    """Sends outgoing chat messages, via `ChatBackend`."""
    chats.register(ws)

    while not ws.closed:
        # Context switch while `ChatBackend.start` is running in the background.
        gevent.sleep(0.1)


@app.route('/')
def chat():
    return render_template('index.html')


