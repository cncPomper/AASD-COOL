import logging

logging.getLogger().setLevel(logging.INFO)
from src.agents.road_condition_reporter.road_condition_protocols import RoadConditionProtocols
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import OneShotBehaviour
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
import json
import networkx as nx
import random


class RoadConditionReporter(Agent):
    def __init__(self, jid, password, graph: nx.Graph, verify_security=False):
        super().__init__(jid, password, verify_security)
        self.graph = graph
        self.busy_edges_count = 3  # Hardcoded parameter for the number of busy edges

    def update_graph_with_curr_conditions(self):

        # Define conditions and their probabilities
        conditions = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        probabilities = [0.5, 0.3, 0.15, 0.04, 0.01]  # Adjust probabilities as needed

        condition_multipliers = {
            "NONE": 1,
            "LOW": 1.5,
            "MEDIUM": 3,
            "HIGH": 5,
            "CRITICAL": 10
        }

        for u, v, data in self.graph.edges(data=True):
            # Select a condition based on the defined probabilities
            condition = random.choices(conditions, probabilities)[0]
            logging.info(f"[ROAD CONDITION MANAGER] Edge {u} -> {v} has condition {condition}: {self.graph[u][v]}")
            self.graph[u][v]["condition"] = condition
            self.graph[u][v]["cost"] *= condition_multipliers[condition]

        return self.graph

    class SendRoadCondition(OneShotBehaviour):
        async def run(self):
                msg = Message(f"navigation_manager@{SERVER_ADDRESS}")
                msg.set_metadata("msg_type", RoadConditionProtocols.REQUEST_ROAD_CONDITION.value)
                # invoke a method that will return the road condition
                updated_graph_with_busy_edges = self.agent.update_graph_with_curr_conditions()
                graph_data = nx.readwrite.json_graph.node_link_data(updated_graph_with_busy_edges)
                msg.body = json.dumps({"updated_graph": graph_data})
                logging.info(f"[ROAD CONDITION MANAGER] Road condition: {graph_data}")
                await self.send(msg)

    async def setup(self):
        behaviourSendRoadCondition = self.SendRoadCondition()
        templateSendRoadCondition = Template()
        templateSendRoadCondition.set_metadata("msg_type", RoadConditionProtocols.SEND_ROAD_CONDITION.value)
        self.add_behaviour(behaviourSendRoadCondition)
