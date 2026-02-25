"use client";

import { useMemo } from "react";

export type RouteGraphNode = {
  id: string;
  node_type: "decision" | "milestone" | "task";
  title: string;
  status: "todo" | "in_progress" | "done" | "cancelled";
  order_hint: number;
};

export type RouteGraphEdge = {
  id: string;
  from_node_id: string;
  to_node_id: string;
  relation: "depends_on" | "blocks";
};

type Props = {
  nodes: RouteGraphNode[];
  edges: RouteGraphEdge[];
  t: (key: string) => string;
};

type LinkedNode = {
  id: string;
  title: string;
};

export function RouteGraphPreview({ nodes, edges, t }: Props) {
  const orderedNodes = useMemo(
    () => [...nodes].sort((a, b) => a.order_hint - b.order_hint || a.title.localeCompare(b.title)),
    [nodes]
  );

  const { incomingByNode, outgoingByNode } = useMemo(() => {
    const nodeById = new Map(orderedNodes.map((node) => [node.id, node]));
    const incomingMap = new Map<string, LinkedNode[]>();
    const outgoingMap = new Map<string, LinkedNode[]>();

    for (const edge of edges) {
      const fromNode = nodeById.get(edge.from_node_id);
      const toNode = nodeById.get(edge.to_node_id);
      if (!fromNode || !toNode) continue;

      const incoming = incomingMap.get(toNode.id) ?? [];
      incoming.push({ id: fromNode.id, title: fromNode.title });
      incomingMap.set(toNode.id, incoming);

      const outgoing = outgoingMap.get(fromNode.id) ?? [];
      outgoing.push({ id: toNode.id, title: toNode.title });
      outgoingMap.set(fromNode.id, outgoing);
    }

    return { incomingByNode: incomingMap, outgoingByNode: outgoingMap };
  }, [orderedNodes, edges]);

  if (!orderedNodes.length) {
    return <div className="meta">{t("routes.graphEmpty")}</div>;
  }

  return (
    <div className="routeGraphList">
      {orderedNodes.map((node) => {
        const incoming = incomingByNode.get(node.id) ?? [];
        const outgoing = outgoingByNode.get(node.id) ?? [];
        return (
          <article key={node.id} className="routeGraphNode">
            <header className="routeGraphNodeHead">
              <div>
                <div className="routeGraphTitle">{node.title}</div>
                <div className="meta">#{node.order_hint}</div>
              </div>
              <div className="badges">
                <span className="badge">{t(`routes.nodeType.${node.node_type}`)}</span>
                <span className="badge">{t(`routes.nodeStatus.${node.status}`)}</span>
              </div>
            </header>

            <section className="routeGraphSection">
              <div className="routeGraphLabel">{t("routes.graphDependsOn")}</div>
              <div className="routeGraphChips">
                {incoming.length ? (
                  incoming.map((item) => (
                    <span key={item.id} className="badge">
                      {item.title}
                    </span>
                  ))
                ) : (
                  <span className="meta">{t("routes.graphNoDependsOn")}</span>
                )}
              </div>
            </section>

            <section className="routeGraphSection">
              <div className="routeGraphLabel">{t("routes.graphBlocks")}</div>
              <div className="routeGraphChips">
                {outgoing.length ? (
                  outgoing.map((item) => (
                    <span key={item.id} className="badge">
                      {item.title}
                    </span>
                  ))
                ) : (
                  <span className="meta">{t("routes.graphNoBlocks")}</span>
                )}
              </div>
            </section>
          </article>
        );
      })}
    </div>
  );
}
