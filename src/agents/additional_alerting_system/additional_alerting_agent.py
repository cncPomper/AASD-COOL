import asyncio
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

class AdditionalAlertingAgent(Agent):
    def __init__(self, jid, password, graph: nx.Graph, verify_security=False):
        super().__init__(jid, password, verify_security)
        self.graph = graph
        self.routes = {}

    class SendAlerts(PeriodicBehaviour):
        async def run(self):
            alerts = []
            for vehicle_id, route in self.agent.routes.items():
                for i in range(len(route) - 1):
                    current_edge = route[i]
                    next_edge = route[i + 1]
                    edge_id = self.agent.graph[current_edge][next_edge]['id']
                    alert = {
                        "edgeId": edge_id,
                        "startNode": current_edge,
                        "endNode": next_edge,
                        "alertType": "EMERGENCY_WARNING"
                    }
                    alerts.append(alert)
            logging.info(f"[ADDITIONAL ALERTING AGENT] Generated alerts: {alerts}")
            msg = Message(f"navigation_manager@{SERVER_ADDRESS}")
            msg.set_metadata("msg_type", "emergency_alerts_response")
            msg.body = json.dumps({"alerts": alerts})
            await self.send(msg)

    class RequestEmergencyRoute(OneShotBehaviour):
        async def run(self):
             while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                routes = msg_json["routes"]
                if routes:
                    self.routes = routes
                    logging.info(f"[ADDITIONAL ALERTING AGENT] Received emergency routes: {routes}")

    async def setup(self):
        behaviourSendAlert = self.SendAlerts(period=1)
        self.add_behaviour(behaviourSendAlert)

        behaviourRequestEmergencyRoute = self.RequestEmergencyRoute()
        templateRequestEmergencyRoute = Template()
        templateRequestEmergencyRoute.set_metadata("msg_type", "emergency_route_response")
        self.add_behaviour(behaviourRequestEmergencyRoute)