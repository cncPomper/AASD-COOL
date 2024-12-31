import asyncio
import logging

logging.getLogger().setLevel(logging.INFO)
from agents.road_condition_reporter.road_condition_protocols import RoadConditionProtocols
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
import json
import networkx as nx

class AdditionalAlertingAgent(Agent):
    def __init__(self, jid, password, verify_security=False):
        super().__init__(jid, password, verify_security)
