import networkx
import json
import matplotlib.pyplot as plt
from src.utils import load_graph


if __name__ == "__main__":
    g = load_graph("data/graph.json")
    labels = networkx.get_node_attributes(g, "traffic_light_id")
    pos = networkx.spring_layout(g)
    networkx.draw(g, with_labels=True, node_size=1000, pos=pos)
    networkx.draw_networkx_edge_labels(g, pos=pos, font_size=10)
    plt.show()
