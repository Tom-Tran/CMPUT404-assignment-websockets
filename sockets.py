#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle, Tom Tran
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect, Response
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        #self.update_listeners( entity )
        self.update_listeners( json.dumps({'entity': entity, 'data': self.space[entity]}) )

    def set(self, entity, data):
        self.space[entity] = data
        #self.update_listeners( entity )
        self.update_listeners( json.dumps({'entity': entity, 'data': self.space[entity]}) )

    def update_listeners(self, message):
        '''update the set listeners'''
        for listener in self.listeners:
            #listener(entity, self.get(entity))
            listener.put( message )

    def clear(self):
        # Unimplemented: Other clients will not know that the world has been cleared
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space
    
class Client:
    def __init__(self):
        self.queue = queue.Queue()
    
    def put(self, msg):
        self.queue.put_nowait(msg)
        
    def get(self):
        return self.queue.get()


myWorld = World()        

#def set_listener( entity, data ):
#    ''' do something with the update ! '''

#myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect("/static/index.html")

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            msg = ws.receive()
            if (msg is not None):
                packet = json.loads(msg)
                myWorld.set(packet.get('entity'), packet.get('data'))
            else:
                break
    except:
        '''Done'''
    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    client = Client()
    myWorld.add_set_listener(client)
    g = gevent.spawn( read_ws, ws, client )
    try:
        while True:
            # Block here
            # Wait for a message and then send it
            msg = client.get()
            ws.send(msg)           
    except Exception as e:
        # WebSocketError as e
        print "WS Error %s" % e
    finally:
        myWorld.listeners.remove(client)
        gevent.kill(g)
    return None



def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    jsonData = flask_post_json()
    
    '''update the elements in entity'''
    for key in jsonData:
        myWorld.update(entity, key, jsonData.get(key))    
    
    return flask.jsonify(myWorld.world().get(entity)), 200

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return flask.jsonify(myWorld.world()), 200

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return flask.jsonify(myWorld.get(entity)), 200

@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!'''
    # Unimplemented: Other clients will not know that the world has been cleared
    myWorld.clear()
    return Response("<h1>CLEARED</h1>", status=200, mimetype="text/html")



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
