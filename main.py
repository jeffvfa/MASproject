#!coding=utf-8
from pade.misc.utility import start_loop
from sys import argv
from pade.acl.aid import AID
# Agents files
from colector import ColectorAgent
from classifier import ClassifierAgent

if __name__ == '__main__':
    agents_per_process = 1
    # c = 0
    agents = list()

    colector_name = 'colector'
    colector = ColectorAgent(AID(name=colector_name))
    agents.append(colector)
    
    for i in range(agents_per_process):
        # port = int(argv[1]) + c
        classifier_name = 'classifier{}'.format(i)
        classifier = ClassifierAgent(AID(name=classifier_name))
        agents.append(classifier)
   
        
        # c += 1000

    start_loop(agents)
