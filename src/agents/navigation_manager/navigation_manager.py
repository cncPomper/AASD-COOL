import asyncio
import logging
import networkx as nx

logging.getLogger().setLevel(logging.INFO)
from src.agents.road_condition_reporter.road_condition_protocols import RoadConditionProtocols
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import OneShotBehaviour
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
import json
from src.agents.traffic_light_controller.messages import TrafficLight, TrafficLightProtocols


class NavigatorManagerAgent(Agent):
    def __init__(self, jid: str, password: str, graph: nx.Graph, verify_security=False):
        super().__init__(jid, password, verify_security)
        self.traffic_light_states: dict[int, TrafficLight] = {}
        self.normal_vehicles_graph = graph
        self.emergency_vehicles_graph = graph
        self.vehicle_positions: dict[int, tuple[str, str]] = {}
        self.idsOfEmergencyVehiclesInNormalGraph = set()
        self.routes_of_emergency_vehicles = {}  # Initialize the routes dictionary of emergency vehicles

    class SetTrafficLightState(OneShotBehaviour):
        """
        Expected message
        {
            "traffic_light_ids": [1, 2, 3, ...]
        }
        """
         
        async def run(self):
            id_: int = 1
            msg = Message(to=f"traffic_light_controller_{id_}@{SERVER_ADDRESS}")
            msg.set_metadata("msg_type", "set_traffic_light")
            msg_body: str = json.dumps({"traffic_light": TrafficLight.GREEN.value})
            msg.body = msg_body
            logging.info(f"[NAVIGATOR MANAGER] Manager changing traffic light state for ID {id_}")
            await self.send(msg)

    class AwaitTrafficLightState(OneShotBehaviour):
        """
        Expected message
        {
            "traffic_light": <RED/GREEN/...>
            "id": <traffic_light_id>
        }
        """

        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                id_: int = msg_json["id"]
                traffic_light: TrafficLight = TrafficLight[msg_json["traffic_light"]]
                self.agent.traffic_light_states[id_] = traffic_light
                logging.info(f"[NAVIGATION MANAGER] Navigation manager received state {traffic_light} from ID {id_}")

    class AwaitVehiclePosition(OneShotBehaviour):
        """
        Expected message
        {
            "node1": 'A',
            "node2": 'B',
            "vehicle_id": 0,
            "isEmergency": True/False
        }
        Vehicle {vehicle_id} is currently od edge A-B
        """

        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                vehicleId = msg_json["vehicle_id"]

                vehicleType = " Emergency" if msg_json["isEmergency"] else " Normal"
                logging.info(f"[NAVIGATION MANAGER] Navigation manager received vehicle position {msg_json} - {vehicleType}")
                
                if(msg_json["isEmergency"]):

                     # Retrieve the current and next traffic light IDs
                    current_edge = (msg_json["node1"], msg_json["node2"])
                    route = self.agent.routes_of_emergency_vehicles[vehicleId]

                    current_traffic_light_id = self.agent.emergency_vehicles_graph.edges[current_edge].get("traffic_light_id", None)
                    logging.info(f"[NAVIGATION MANAGER] Current traffic light ID: {current_traffic_light_id}")
                    next_traffic_light_id = None

                     # Find the next traffic light ID in the route
                    found_current = False
                    for i in range(len(route) - 1):
                        edge = (route[i], route[i + 1])
                        if found_current:
                            next_traffic_light_id = self.agent.emergency_vehicles_graph.edges[edge].get("traffic_light_id", None)
                            if next_traffic_light_id is not None:
                                break
                        if edge == current_edge:
                            found_current = True

                    logging.info(f"[NAVIGATION MANAGER] Current traffic light ID: {current_traffic_light_id}, Next traffic light ID: {next_traffic_light_id}")

                    for id in [current_traffic_light_id, next_traffic_light_id]:
                        if id is None:
                            continue

                        msg = Message(to=f"traffic_light_controller_{id}@{SERVER_ADDRESS}")
                        msg.set_metadata("msg_type", "set_traffic_light")
                        msg_body: str = json.dumps({"traffic_light": TrafficLight.GREEN.value})
                        msg.body = msg_body
                        logging.info(f"[NAVIGATOR MANAGER] Manager changing traffic light state for ID {id}")
                        await self.send(msg)

                self.agent.vehicle_positions[vehicleId] = (msg_json["node1"], msg_json["node2"])

    class SendRoute(OneShotBehaviour):
        """
        Expected message
        {
            "vehicle_id": 0,
            "target": "D",
            "isEmergency": True/False
        }
        """
        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                isEmergency = msg_json["isEmergency"]
                vehicleId = msg_json["vehicle_id"]

                roads_graph = self.agent.normal_vehicles_graph if not isEmergency else self.agent.emergency_vehicles_graph
                route = nx.shortest_path(
                    roads_graph,
                    source=self.agent.vehicle_positions.get(vehicleId, ("A", "A"))[0],
                    target=msg_json["target"],
                    weight="cost",
                )
                if isEmergency:
                    self.agent.routes_of_emergency_vehicles[vehicleId] = route
                    logging.info(f"[NAVIGATION MANAGER] Emergency vehicle {vehicleId} route: {route}")

                # If the vehicle is an emergency vehicle 
                # and the normal graph has not been updated due to increased cost of emergency vehicle route
                if(isEmergency and vehicleId not in self.agent.idsOfEmergencyVehiclesInNormalGraph):
                    for i in range(len(route) - 1):
                        u, v = route[i], route[i + 1]
                        # Increase the cost of the emergency route edges 
                        if self.agent.normal_vehicles_graph.has_edge(u, v):

                            self.agent.normal_vehicles_graph[u][v]['cost'] *= 3

                            if 'numOfEmergencyVehPlanned' not in self.agent.normal_vehicles_graph[u][v]:
                                self.agent.normal_vehicles_graph[u][v]['numOfEmergencyVehPlanned'] = 0
                            else:
                                self.agent.normal_vehicles_graph[u][v]['numOfEmergencyVehPlanned'] += 1

                    self.agent.idsOfEmergencyVehiclesInNormalGraph.add(vehicleId)


                msg = Message(f"vehicle_navigator_{vehicleId}@{SERVER_ADDRESS}")
                msg.set_metadata("msg_type", "route_response")
                msg.body = json.dumps({"route": route})
                vehicleType = " Emergency" if isEmergency else " Normal"
                logging.info(f"[NAVIGATION MANAGER] Generated route: {route} for vehicle {vehicleId} - {vehicleType}")
                await self.send(msg)

    class ReceiveRoadCondition(OneShotBehaviour):
        async def run(self):
            while 1:
                msg = await self.receive(timeout=20)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                updated_graph_with_conditions = nx.readwrite.json_graph.node_link_graph(msg_json["updated_graph"])
                logging.info(f"[NAVIGATION MANAGER] Received updated roads with current conditions")
                self.agent.graph = updated_graph_with_conditions
                self.agent.emergency_vehicles_graph = updated_graph_with_conditions

    class SendEmergencyRoutes(PeriodicBehaviour):
        async def run(self):
            routes = self.agent.routes_of_emergency_vehicles
            msg = Message(f"additional_alerting_agent@{SERVER_ADDRESS}")
            msg.set_metadata("msg_type", "emergency_route_response")
            msg.body = json.dumps({"routes": routes})
            logging.info(f"[NAVIGATION MANAGER] Sending emergency routes to additional alerting manager")
            await self.send(msg)
    
    class AwaitEmergencyAlerts(OneShotBehaviour):
        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                alerts = msg_json["alerts"]
                logging.info(f"[NAVIGATION MANAGER] Received emergency alerts from additional alerting manager: {alerts}")

    async def setup(self):
        b0 = self.ReceiveRoadCondition()
        t0 = Template()
        t0.set_metadata("msg_type", RoadConditionProtocols.REQUEST_ROAD_CONDITION.value)

        b1 = self.AwaitTrafficLightState()
        t1 = Template()
        t1.set_metadata("msg_type", TrafficLightProtocols.SEND_TRAFFIC_LIGHT.value)

        b2 = self.SetTrafficLightState()

        b3 = self.SendRoute()
        t3 = Template()
        t3.set_metadata("msg_type", "send_route")

        b4 = self.AwaitVehiclePosition()
        t4 = Template()
        t4.set_metadata("msg_type", "send_vehicle_position")

        b5 = self.SendEmergencyRoutes(period=1)

        b6 = self.AwaitEmergencyAlerts()
        t6 = Template()
        t6.set_metadata("msg_type", "emergency_alerts_response")

        self.add_behaviour(b0, t0)
        self.add_behaviour(b1, t1)
        self.add_behaviour(b2)
        self.add_behaviour(b3, t3)
        self.add_behaviour(b4, t4)
        self.add_behaviour(b5)
