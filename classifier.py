#!coding=utf-8
from pade.misc.utility import display_message
from pade.core.agent import Agent
from pade.acl.aid import AID



class ClassifierAgent(Agent):
     
    def __init__(self, aid):
        super(ClassifierAgent, self).__init__(aid=aid)
        display_message(self.aid.localname, 'Hello World!')

    def react(self, message):
        display_message(self.aid.localname, ('Mensagem recebida -> '+ message.content))