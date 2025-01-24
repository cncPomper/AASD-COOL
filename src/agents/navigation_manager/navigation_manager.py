import asyncio
import logging
import networkx as nx

logging.getLogger().setLevel(logging.INFO)
from src.agents.road_condition_reporter.road_condition_protocols import RoadConditionProtocols
from spade.agent import Agent
from spade.template import Template
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from ...config import SERVER_ADDRESS
import json
from src.agents.traffic_light_controller.messages import TrafficLight, TrafficLightProtocols


class NavigatorManagerAgent(Agent):
    def __init__(self, jid: str, password: str, graph: nx.Graph, verify_security=False):
        super().__init__(jid, password, verify_security)
        self.traffic_light_states: dict[int, TrafficLight] = {}
        self.graph_with_road_conditions = graph
        self.vehicle_positions: dict[int, tuple[str, str]] = {}

    class SetTrafficLightState(OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(15)
            return
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
            "vehicle_id": 0
        }
        Vehicle {vehicle_id} is currently od edge A-B
        """

        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                logging.info(f"[NAVIGATION MANAGER] Navigation manager received vehicle position {msg_json}")
                self.agent.vehicle_positions[msg_json["vehicle_id"]] = (msg_json["node1"], msg_json["node2"])

    class SendRoute(OneShotBehaviour):
        """
        Expected message
        {
            "vehicle_id": 0,
            "target": "D"
        }
        """
        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                route = nx.shortest_path(
                    self.agent.graph_with_road_conditions,
                    source=self.agent.vehicle_positions.get(msg_json["vehicle_id"], ("A", "A"))[0],
                    target=msg_json["target"],
                    weight="distance",
                )
                msg = Message(f"vehicle_navigator_{msg_json['vehicle_id']}@{SERVER_ADDRESS}")
                msg.set_metadata("msg_type", "route_response")
                msg.body = json.dumps({"route": route})
                logging.info(f"[NAVIGATION MANAGER] Generated route: {route} for vehicle {msg_json['vehicle_id']}")
                await self.send(msg)

    class ReceiveRoadCondition(OneShotBehaviour):
        async def run(self):
            while 1:
                msg = await self.receive(timeout=10)
                if not msg:
                    continue
                msg_json = json.loads(msg.body)
                updated_graph = msg_json["updated_graph"]
                logging.info(f"[NAVIGATION MANAGER] Received road condition: {updated_graph}")

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

        self.add_behaviour(b0, t0)
        self.add_behaviour(b1, t1)
        self.add_behaviour(b2)
        self.add_behaviour(b3, t3)
        self.add_behaviour(b4, t4)
