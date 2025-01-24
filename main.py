import asyncio
import spade
import networkx as nx
import random
from src.agents.road_condition_reporter.road_condition_reporter import RoadConditionReporter
from src.agents.traffic_light_controller.traffic_light_controller import TrafficLightControllerAgent
from src.agents.traffic_light_controller.physical_traffic_light import PhysicalTrafficLight
from src.agents.navigation_manager.navigation_manager import NavigatorManagerAgent
from src.agents.vehicle_navigator.vehicle_simulator import VehicleSimulator
from src.agents.vehicle_navigator.vehicle_navigator import VehicleNavigator
from src.utils import load_graph, load_lights

from src.config import SERVER_ADDRESS, PASSWORD


async def main():
    ptls: dict[int, PhysicalTrafficLight] = load_lights("data/traffic_lights.json")
    traffic_lights_agents = []
    for id_, ptl in ptls.items():
        traffic_lights_agents.append(
            TrafficLightControllerAgent(f"traffic_light_controller_{id_}@{SERVER_ADDRESS}", PASSWORD, ptl)
        )
    for ag in traffic_lights_agents:
        await ag.start(auto_register=True)

    graph: nx.Graph = load_graph("data/graph.json")
    road_condition_reporter = RoadConditionReporter(f"road_condition_reporter@{SERVER_ADDRESS}", PASSWORD, graph)
    await road_condition_reporter.start(auto_register=True)

    manager_agent = NavigatorManagerAgent(jid=f"navigation_manager@{SERVER_ADDRESS}", password=PASSWORD, graph=graph)
    await manager_agent.start(auto_register=True)
    vehicle_navigators = []
    for i in range(3):
        start_node: str = random.choice(list(graph.nodes))
        finish_node: str = random.choice(list(graph.nodes))
        vehicle_simulator = VehicleSimulator(graph, start_node, finish_node)
        vehicle_navigator_agent = VehicleNavigator(
            jid=f"vehicle_navigator_{i}@{SERVER_ADDRESS}",
            password=PASSWORD,
            simulator=vehicle_simulator,
            target_node=finish_node,
            vehicle_id=i,
        )
        vehicle_navigators.append(vehicle_navigator_agent)
    for agent in vehicle_navigators:
        await agent.start(auto_register=True)
    vehicle_navigator_finish_coros = [
        spade.wait_until_finished(vehicle_navigator_agent)
        for vehicle_navigator_agent in vehicle_navigators
    ]
    await asyncio.gather(*vehicle_navigator_finish_coros)
    for ag in traffic_lights_agents:
        await ag.stop()
    await manager_agent.stop()


if __name__ == "__main__":
    spade.run(main())
