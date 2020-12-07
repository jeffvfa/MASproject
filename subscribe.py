from pade.misc.utility import display_message, start_loop
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.behaviours.protocols import FipaSubscribeProtocol, TimedBehaviour
from sys import argv


import tweepy
from queue import Queue
from threading import Thread
import os
import time
import random


class SubscriberProtocol(FipaSubscribeProtocol):

    def __init__(self, agent, message):
        super(SubscriberProtocol, self).__init__(
            agent, message, is_initiator=True)

    def handle_agree(self, message):
        display_message(self.agent.aid.name, message.content)

    def handle_inform(self, message):
        display_message(self.agent.aid.name, message.content)


class PublisherProtocol(FipaSubscribeProtocol):

    def __init__(self, agent):
        super(PublisherProtocol, self).__init__(
            agent, message=None, is_initiator=False)

    def handle_subscribe(self, message):
        self.register(message.sender)
        display_message(self.agent.aid.name, '{} from {}'.format(message.content, message.sender.name))
        resposta = message.create_reply()
        resposta.set_performative(ACLMessage.AGREE)
        resposta.set_content('Subscribe message accepted')
        self.agent.send(resposta)

    def handle_cancel(self, message):
        self.deregister(self, message.sender)
        display_message(self.agent.aid.name, message.content)

    def notify(self, message):
        super(PublisherProtocol, self).notify(message)


class Time(TimedBehaviour):

    def __init__(self, agent, notify):
        super(Time, self).__init__(agent, 0.5)
        self.notify = notify
        self.inc = 0

    def on_time(self):
        super(Time, self).on_time()
        message = ACLMessage(ACLMessage.INFORM)
        message.set_protocol(ACLMessage.FIPA_SUBSCRIBE_PROTOCOL)
        
        message.set_content(str(self.funcname()))
        self.notify(message)
        self.inc += 0.1
    

    def funcname(self):
        """
        docstring
        """
        try:
            f = open('data/user_data.json', 'r')
            lines = f.readlines()
            f.close()
        except:
            print('no lines')
        
        if len(lines) > 0:
            try:
                f = open('data/user_data.json', 'w')
                f.write(''.join(lines[1:]))
                f.close()
            except:
                pass
        else: 
            print('\nNODAATA')
        
        return lines[1]
            
            
            


class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        # print(status.text)
        self.saveUserData(str(status._json))

    def on_error(self, status_code):
        if status_code == 420:
            # print("on_error disconnects the stream")
            return False

    def __init__(self, q=Queue()):
        super().__init__()
        self.q = q
        for i in range(4):
            t = Thread(target=self.do_stuff)
            t.daemon = True
            t.start()

    def do_stuff(self):
        while True:
            self.q.get()
            self.q.task_done()

    def saveUserData(self, data):
        FILE = open("data/user_data.json", "a")
        FILE.write(data + ',\n')
        FILE.close()
        # statinfo = os.stat("data/user_data.json")

        # if statinfo.st_size >= 25000000:
        #     self.backupUserData(data)

    def backupUserData(self, data):
        FILE = open("data/user_data.json", "r")
        data = FILE.read()
        FILE.close()

        ts = str(time.time()).replace(".", "") + '.json'

        FILE = open("data/bkp/" + ts, "a")
        FILE.write(data)
        FILE.close()

        # FILE = open("data/bkp/" + ts, "rb")
        # dbx.files_upload(FILE.read(), "/bkp/" + ts)
        # FILE.close()

        FILE = open("data/user_data.json", "w")
        FILE.close()


class AgentSubscriber(Agent):

    def __init__(self, aid):
        super(AgentSubscriber, self).__init__(aid)

        self.call_later(8.0, self.launch_subscriber_protocol)

    def launch_subscriber_protocol(self):
        msg = ACLMessage(ACLMessage.SUBSCRIBE)
        msg.set_protocol(ACLMessage.FIPA_SUBSCRIBE_PROTOCOL)
        msg.set_content('Subscription request')
        msg.add_receiver(agent_pub_1.aid)

        self.protocol = SubscriberProtocol(self, msg)
        self.behaviours.append(self.protocol)
        self.protocol.on_start()


class AgentPublisher(Agent):
    # agent attributes
    keys = []
    api = None
    myStreamListener = None
    myStream = None
    inc = 0

    def __init__(self, aid):
        super(AgentPublisher, self).__init__(aid)
        self.inc = 0


        self.inc += 0.1

        self.protocol = PublisherProtocol(self)
        self.timed = Time(self, self.protocol.notify)

        self.behaviours.append(self.protocol)
        self.behaviours.append(self.timed)

        self.keys = self.getKeys()
        self.api = {}

        for key in self.keys:
            self.api = self.authenticate(key[0], key[1], key[2], key[3])

        print(self.api["auth"])
        self.myStreamListener = MyStreamListener()
        self.myStream = tweepy.Stream(
            auth=self.api["auth"], listener=self.myStreamListener)

        self.myStream.filter(track=["pizza"], is_async=True)

    def getKeys(self):
        FILE = open("data/keys.txt", "r")
        keys0 = FILE.read()
        keys1 = []
        FILE.close()

        keys0 = keys0.split("\n")

        for key in keys0:
            keys1.append(key.split("@"))

        last = len(keys1) - 1

        del keys1[last]
        return keys1

    def authenticate(self, CONSUMER_TOKEN, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET):
        auth = tweepy.OAuthHandler(CONSUMER_TOKEN, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

        # Construct the API instance
        api = tweepy.API(
            auth,
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True,
            compression=True,
            retry_count=9080,
            retry_delay=15,
        )

        dct = {}
        dct["api"] = api
        dct["auth"] = auth
        return dct


if __name__ == '__main__':

    agents_per_process = 1
    c = 0
    agents = list()
    for i in range(agents_per_process):
        port = int(argv[1]) + c
        k = 10000
        participants = list()

        agent_name = 'agent_publisher_{}@localhost:{}'.format(port, port)
        participants.append(agent_name)
        agent_pub_1 = AgentPublisher(AID(name=agent_name))
        agents.append(agent_pub_1)

        agent_name = 'agent_subscriber_{}@localhost:{}'.format(
            port + k, port + k)
        participants.append(agent_name)
        agent_sub_1 = AgentSubscriber(AID(name=agent_name))
        agents.append(agent_sub_1)

        agent_name = 'agent_subscriber_{}@localhost:{}'.format(
            port - k, port - k)
        agent_sub_2 = AgentSubscriber(AID(name=agent_name))
        agents.append(agent_sub_2)

        agent_name = 'agent_subscriber_{}@localhost:{}'.format(
            port + k + k, port + k + k)
        agent_sub_3 = AgentSubscriber(AID(name=agent_name))
        agents.append(agent_sub_3)

        c += 1000

    start_loop(agents)
