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
import ast

import classifier


class PublisherProtocolColector(FipaSubscribeProtocol):

    def __init__(self, agent):
        super(PublisherProtocolColector, self).__init__(
            agent, message=None, is_initiator=False)

    def handle_subscribe(self, message):
        self.register(message.sender)
        display_message(self.agent.aid.name, '{} from {}'.format(
            message.content, message.sender.name))
        resposta = message.create_reply()
        resposta.set_performative(ACLMessage.AGREE)
        resposta.set_content('Subscribe message accepted')
        self.agent.send(resposta)

    def handle_cancel(self, message):
        self.deregister(message.sender)
        display_message(self.agent.aid.name, message.content)

    def notify(self, message):
        super(PublisherProtocolColector, self).notify(message)

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
        self.saveUserData(str(status._json))

    def on_error(self, status_code):
        if status_code == 420:
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
        FILE.write(data + '\n')
        FILE.close()

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

class AgentReferee(Agent):

    def __init__(self, aid):
        super(AgentReferee, self).__init__(aid)


    def react(self, message): 
        if str(message.sender.name) in participants:
            display_message(self.aid.name, str(message.sender.name)+ str(message.content))
            content = str(message.content).split(' ')
            self.decide(str(message.sender.name), content[0], content[1])

    def decide(self, agent_id, user_id, user_class):
        string_class = "bot" if int(user_class)  else "human"
        display_message(self.aid.name, user_id + ' is ' + string_class)
        # TODO implement the referee behavior

class AgentColector(Agent):
    # agent attributes
    keys = []
    api = None
    myStreamListener = None
    myStream = None
    inc = 0

    def __init__(self, aid):
        super(AgentColector, self).__init__(aid)
        self.inc = 0

        self.inc += 0.1

        self.protocol = PublisherProtocolColector(self)
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

class SubscriberProtocolClassifier(FipaSubscribeProtocol):

    def __init__(self, agent, message):
        super(SubscriberProtocolClassifier, self).__init__(
            agent, message, is_initiator=True)

    def handle_agree(self, message):
        display_message(self.agent.aid.name, message.content)

    def handle_inform(self, message):
        x = ast.literal_eval(str(message.content))
        classy = self.agent.classify(x['user']['id'], x['user']['statuses_count'], x['user']['followers_count'], x['user']['friends_count'], x['user']['favourites_count'], x['user']['listed_count'])
        
        display_message(self.agent.aid.name, 'class of ' +
                        str(x['user']['id']) + ' is ' + str(classy))
        from pade.acl.messages import ACLMessage, AID

        message = ACLMessage(ACLMessage.INFORM)
        message.set_protocol(ACLMessage.FIPA_REQUEST_PROTOCOL)
        message.add_receiver(agent_referee.aid)
        message.set_content(str(x['user']['id']) + ' ' + str(classy))
        self.agent.send(message)

class AgentClassifier(Agent):

    def __init__(self, aid):
        super(AgentClassifier, self).__init__(aid)
        self.call_later(8.0, self.launch_subscriber_protocol)

    def launch_subscriber_protocol(self):
        msg = ACLMessage(ACLMessage.SUBSCRIBE)
        msg.set_protocol(ACLMessage.FIPA_SUBSCRIBE_PROTOCOL)
        msg.set_content('Subscription request')
        msg.add_receiver(agent_colector.aid)

        self.protocol = SubscriberProtocolClassifier(self, msg)
        self.behaviours.append(self.protocol)
        self.protocol.on_start()

    def classify(self, id, statuses_count, followers_count, friends_count, favourites_count, listed_count):
        print(id, statuses_count, followers_count, friends_count, favourites_count, listed_count)
        return random.randrange(2)

if __name__ == '__main__':

    agents_per_process = 1
    c = 0
    agents = list()
    for i in range(agents_per_process):
        port = int(argv[1]) + c
        k = 10000
        participants = list()

        agent_name = 'agent_colector_{}@localhost:{}'.format(port, port)
        participants.append(agent_name)

        agent_colector = AgentColector(AID(name=agent_name))

        agents.append(agent_colector)

        agent_name = 'agent_classifier_{}@localhost:{}'.format(
            port + k, port + k)
        participants.append(agent_name)
        agent_classifier_1 = AgentClassifier(AID(name=agent_name))

        agents.append(agent_classifier_1)

        agent_name = 'agent_classifier_{}@localhost:{}'.format(
            port - k, port - k)
        agent_classifier_2 = AgentClassifier(AID(name=agent_name))
        participants.append(agent_name)

        agents.append(agent_classifier_2)

        agent_name = 'agent_classifier_{}@localhost:{}'.format(
            port + k + k, port + k + k)
        agent_classifier_3 = AgentClassifier(AID(name=agent_name))
        participants.append(agent_name)

        agents.append(agent_classifier_3)

        agent_name = 'agent_referee_{}@localhost:{}'.format(
            port + k + k + k, port + k + k + k)
        agent_referee = AgentReferee(AID(name=agent_name))
        participants.append(agent_name)

        agents.append(agent_referee)

        c += 1000

    start_loop(agents)
