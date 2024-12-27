import spade
import traceback
import networkx as nx
from src.agents.traffic_light_controller.traffic_light_controller import TrafficLightControllerAgent
from src.agents.traffic_light_controller.physical_traffic_light import PhysicalTrafficLight
from src.agents.navigation_manager.navigation_manager import NavigatorManagerAgent
from src.agents.vehicle_navigator.vehicle_simulator import VehicleSimulator
from src.utils import load_graph, load_lights

from src.config import SERVER_ADDRESS, PASSWORD


async def main():
    ptls: dict[int, PhysicalTrafficLight] = load_lights("data/traffic_lights.json")
    traffic_lights_agents = []
    for id, ptl in ptls.items():
        traffic_lights_agents.append(
            TrafficLightControllerAgent(f"traffic_light_controller_{id}@{SERVER_ADDRESS}", PASSWORD, ptl)
        )
    for ag in traffic_lights_agents:
        await ag.start(auto_register=True)
    manager_agent = NavigatorManagerAgent(f"navigation_manager@{SERVER_ADDRESS}", PASSWORD)
    await manager_agent.start(auto_register=True)

    graph: nx.Graph = load_graph("data/graph.json")
    start_node: str = graph.start_node
    finish_node: str = graph.finish_node
    vehicle_simulator_agent = VehicleSimulator(f"vehicle_simulator@{SERVER_ADDRESS}", PASSWORD, graph, start_node, finish_node)
    await vehicle_simulator_agent.start(auto_register=True)

    await spade.wait_until_finished(vehicle_simulator_agent)
    for ag in traffic_lights_agents:
        await ag.stop()
    await manager_agent.stop()


if __name__ == "__main__":
    spade.run(main())
