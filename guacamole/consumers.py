# -*- coding: utf-8 -*-
from channels.generic.websockets import WebsocketConsumer
try:
    import simplejson as json
except ImportError:
    import json
import sys
from django.utils.encoding import smart_unicode
from guacamole.guacamolethreading import get_redis_instance
from guacamole.client import GuacamoleClient
import uuid
from django.conf import settings
from guacamole.guacamolethreading import GuacamoleThread,GuacamoleThreadWrite
try:
    import simplejson as json
except ImportError:
    import json
from django.core.exceptions import ObjectDoesNotExist
from webterminal.models import ServerInfor,Log
from django.utils.timezone import now
from django.contrib.auth.models import User
from webterminal.settings import MEDIA_ROOT
import os
from guacamole.instruction import GuacamoleInstruction as Instruction


def mkdir_p(path):
    """
    Pythonic version of "mkdir -p".  Example equivalents::

        >>> mkdir_p('/tmp/test/testing') # Does the same thing as...
        >>> from subprocess import call
        >>> call('mkdir -p /tmp/test/testing')

    .. note:: This doesn't actually call any external commands.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        pass

class GuacamoleWebsocket(WebsocketConsumer):
    
    http_user = True
    #http_user_and_session = True
    channel_session = True
    channel_session_user = True

    @property
    def authenticate(self):
        if self.message.user.is_authenticated():
            return True
        else:
            return False

    def connect(self, message,id):
        self.message.reply_channel.send({"accept": True})
        if not self.authenticate:
            self.message.reply_channel.send({"text":json.dumps({'status':False,'message':'You must login to the system!'})},immediately=True)
            self.message.reply_channel.send({"accept":False})
        else:
            client = GuacamoleClient(settings.GUACD_HOST, settings.GUACD_PORT)
            try:
                data = ServerInfor.objects.get(id=id)
                if data.credential.protocol in ['vnc','rdp','telnet']:
                    pass
                else:
                    self.message.reply_channel.send({"accept":False})
            except ObjectDoesNotExist:
                #server info not exist
                self.message.reply_channel.send({"accept":False})
            cache_key = str(uuid.uuid4())

            directory_date_time = now()
            recording_path = os.path.join(MEDIA_ROOT,'{0}-{1}-{2}'.format(directory_date_time.year,directory_date_time.month,directory_date_time.day))
            drive_path = os.path.join(recording_path,self.message.reply_channel.name)
            """
            Create recording media file and drive path
            """
            mkdir_p(recording_path)
            mkdir_p(drive_path)

            client.handshake(width=data.credential.width,
                             height=data.credential.height,
                             protocol=data.credential.protocol,
                             hostname=data.ip,
                             port=data.credential.port,
                             username=data.credential.username,
                             password=data.credential.password,
                             recording_path=recording_path,
                             recording_name=cache_key,
                             create_recording_path='true',
                             enable_wallpaper='true',
                             ignore_cert='true',)
                             #enable_drive='true',
                             #drive_path=recording_path,
                             #create_drive_path='true')
                             #security='tls',)

            self.message.reply_channel.send({"text":'0.,{0}.{1};'.format(len(cache_key),cache_key)},immediately=True)
           #'0.,36.83940151-b2f9-4743-b5e4-b6eb85a97743;'

            audit_log = Log.objects.create(user=User.objects.get(username=self.message.user),server=data,channel=self.message.reply_channel.name,width=data.credential.width,height=data.credential.height,log=cache_key,gucamole_client_id=client._id)
            audit_log.save()
            guacamolethread=GuacamoleThread(self.message,client)
            guacamolethread.setDaemon = True
            guacamolethread.start()

            guacamolethreadwrite=GuacamoleThreadWrite(self.message,client)
            guacamolethreadwrite.setDaemon = True
            guacamolethreadwrite.start()

    def disconnect(self, message,id):
        #close threading
        print 'disconnect'
        try:
            audit_log = Log.objects.get(channel=self.message.reply_channel.name)
            audit_log.is_finished = True
            audit_log.end_time = now()
            audit_log.save()
            cache_key = audit_log.gucamole_client_id
            client = GuacamoleClient(settings.GUACD_HOST, settings.GUACD_PORT)
            client.send_instruction(Instruction('select',cache_key))
            instruction=client.read_instruction()
            kwargs = {'width':1024,'height':768,'read_only':'true'}
            connection_args = [
                kwargs.get(arg.replace('-', '_'), '') for arg in instruction.args
            ]
            client.send_instruction(Instruction('size', 1024, 768, 96))
            client.send_instruction(Instruction('audio', *list()))
            client.send_instruction(Instruction('video', *list()))
            client.send_instruction(Instruction('image', *list()))
            client.send_instruction(Instruction('connect', *connection_args))
            client.send_instruction(Instruction('disconnect', *connection_args))
        except:
            pass
        finally:
            self.message.reply_channel.send({"accept":False})
    
    def queue(self):
        queue = get_redis_instance()
        channel = queue.pubsub()
        return queue
        
    def receive(self,text=None, bytes=None, **kwargs):
        self.queue().publish(self.message.reply_channel.name, text)


class GuacamoleMonitor(GuacamoleWebsocket):

    def connect(self, message,id):
        self.message.reply_channel.send({"accept": True})
        if not self.authenticate:
            self.message.reply_channel.send({"text":json.dumps({'status':False,'message':'You must login to the system!'})},immediately=True)
            self.message.reply_channel.send({"accept":False})
        else:
            client = GuacamoleClient(settings.GUACD_HOST, settings.GUACD_PORT)
            log_object = Log.objects.get(id=id)
            cache_key = str(log_object.gucamole_client_id)


            data = log_object.server

            #draft version for real time monitor
            client.send_instruction(Instruction('select',cache_key))
            instruction=client.read_instruction()
            kwargs = {'width':1024,'height':768,'read_only':'true'}
            connection_args = [
                kwargs.get(arg.replace('-', '_'), '') for arg in instruction.args
            ]
            client.send_instruction(Instruction('size', 1024, 768, 96))
            client.send_instruction(Instruction('audio', *list()))
            client.send_instruction(Instruction('video', *list()))
            client.send_instruction(Instruction('image', *list()))
            client.send_instruction(Instruction('connect', *connection_args))

            #self.message.reply_channel.send({"text":'0.,{0}.{1};'.format(len(cache_key),cache_key)},immediately=True)
            guacamolethread=GuacamoleThread(self.message,client)
            guacamolethread.setDaemon = True
            guacamolethread.start()

            guacamolethreadwrite=GuacamoleThreadWrite(self.message,client)
            guacamolethreadwrite.setDaemon = True
            guacamolethreadwrite.start()

    def disconnect(self, message,id):
        #close threading
        print 'disconnect'
        try:
            log_object = Log.objects.get(id=id)
            cache_key = log_object.gucamole_client_id
            client = GuacamoleClient(settings.GUACD_HOST, settings.GUACD_PORT)
            client.send_instruction(Instruction('select',cache_key))
            instruction=client.read_instruction()
            kwargs = {'width':1024,'height':768,'read_only':'true'}
            connection_args = [
                kwargs.get(arg.replace('-', '_'), '') for arg in instruction.args
            ]
            client.send_instruction(Instruction('size', 1024, 768, 96))
            client.send_instruction(Instruction('audio', *list()))
            client.send_instruction(Instruction('video', *list()))
            client.send_instruction(Instruction('image', *list()))
            client.send_instruction(Instruction('connect', *connection_args))
            client.send_instruction(Instruction('disconnect', *connection_args))
        except:
            pass
        finally:
            self.message.reply_channel.send({"accept":False})