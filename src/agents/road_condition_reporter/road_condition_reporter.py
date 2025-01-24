import logging

logging.getLogger().setLevel(logging.INFO)
from src.agents.road_condition_reporter.road_condition_protocols import RoadConditionProtocols
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
import json
import networkx as nx


class RoadConditionReporter(Agent):
    def __init__(self, jid, password, graph: nx.Graph, verify_security=False):
        super().__init__(jid, password, verify_security)
        self.graph = graph
        self.busy_edges_count = 3  # Hardcoded parameter for the number of busy edges

    def mark_busy_edges(self):
        graph_copy = self.graph.copy()
        path = nx.shortest_path(graph_copy, source=graph_copy.start_node, target=graph_copy.finish_node, weight='distance')
        for i in range(min(self.busy_edges_count, len(path) - 1)):
            node1 = path[i]
            node2 = path[i + 1]
            graph_copy[node1][node2]['is_busy'] = True
        return graph_copy

    class SendRoadCondition(OneShotBehaviour):
        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg = Message(f"navigation_manager@{SERVER_ADDRESS}")
                msg.set_metadata("msg_type", RoadConditionProtocols.REQUEST_ROAD_CONDITION.value)
                # invoke a method that will return the road condition
                updated_graph_with_busy_edges = self.agent.mark_busy_edges()
                #not sure if the networkx graph is serialized -> to be confirmed
                msg.body = json.dumps({"updated_graph": updated_graph_with_busy_edges})
                await self.send(msg)

    async def setup(self):
        behaviourSendRoadCondition = self.SendRoadCondition()
        templateSendRoadCondition = Template()
        templateSendRoadCondition.set_metadata("msg_type", RoadConditionProtocols.SEND_ROAD_CONDITION.value)
        self.add_behaviour(behaviourSendRoadCondition, templateSendRoadCondition)
