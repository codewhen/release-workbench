import { useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  ControlButton,
  MiniMap,
  applyNodeChanges,
  useReactFlow,
  type Connection,
  type Edge as FlowEdge,
  MarkerType,
} from "@xyflow/react";
import { Plus, Minus, Maximize2 } from "lucide-react";
import { CardNode, type FlowNode } from "../cards/CardNode";
import { visibleCards } from "./model";
import type { CardMeta, Workflow } from "../shared/types";
import { AreaNode, type AreaFlowNode } from "./AreaNode";
const nodeTypes = { card: CardNode, area: AreaNode };
type CanvasNode = FlowNode | AreaFlowNode;
export interface CanvasActions {
  onConfig: (id: string, key: string, value: unknown) => void;
  onOpenFunction: (id: string) => void;
  onNewFunction: (returns?: string) => void;
  onDetails: (id: string) => void;
  onInvalid?: (id: string, error: string) => void;
}
export function FlowCanvas({
  workflow,
  graphId,
  catalog,
  editing,
  selected,
  statuses,
  focus,
  following,
  onInspect,
  onSelect,
  onConnect,
  onMove,
  onMenu,
  onArea,
  ...actions
}: {
  workflow: Workflow;
  graphId: string;
  catalog: CardMeta[];
  editing: boolean;
  selected: string | null;
  statuses: Record<string, string>;
  focus: string | null;
  following: boolean;
  onInspect: () => void;
  onSelect: (id: string) => void;
  onConnect: (connection: Connection) => void;
  onMove: (id: string, position: { x: number; y: number }) => void;
  onArea: (
    id: string,
    change: { width?: number; height?: number; collapsed?: boolean },
  ) => void;
  onMenu: (
    event: Pick<MouseEvent, "preventDefault" | "clientX" | "clientY">,
    target: {
      kind: "canvas" | "card" | "edge" | "area";
      id?: string;
      point?: { x: number; y: number };
    },
  ) => void;
} & CanvasActions) {
  const flow = useReactFlow<CanvasNode>();
  const graph = workflow.graphs[graphId];
  const [nodes, setNodes] = useState<CanvasNode[]>([]);
  const visible = useMemo(
    () => visibleCards(workflow, graphId),
    [workflow, graphId],
  );
  useEffect(() => {
    setNodes([
      ...(workflow.layout?.[graphId]?.areas ?? []).map((a) => ({
        id: a.id,
        type: "area" as const,
        position: a.position,
        style: { width: a.width, height: a.collapsed ? 62 : a.height },
        zIndex: -1,
        selected: a.id === selected,
        data: {
          name: a.name,
          kind: a.kind,
          collapsed: a.collapsed ?? false,
          editing,
          onCollapse: () => onArea(a.id, { collapsed: !a.collapsed }),
          onResize: (width: number, height: number) =>
            onArea(a.id, { width, height }),
        },
      })),
      ...visible.map((card, i) => ({
        id: card.id,
        type: "card" as const,
        position: workflow.layout?.[graphId]?.positions?.[card.id] ?? {
          x: i * 340,
          y: 0,
        },
        selected: card.id === selected,
        data: {
          card,
          meta: catalog.find((m) => m.kind === card.kind)!,
          workflow,
          editing,
          status: statuses[card.id] ?? "pending",
          selected: card.id === selected,
          ...actions,
        },
      })),
    ]);
  }, [workflow, graphId, catalog, editing, selected, JSON.stringify(statuses)]);
  useEffect(() => {
    if (!following || !focus) return;
    const node = flow.getNode(focus);
    if (node)
      flow.setCenter(node.position.x + 134, node.position.y + 100, {
        zoom: 0.95,
        duration: matchMedia("(prefers-reduced-motion:reduce)").matches
          ? 0
          : 200,
      });
  }, [focus, following]);
  const edges: FlowEdge[] = graph.edges
    .filter(
      (e) =>
        visible.some((c) => c.id === e.source) &&
        visible.some((c) => c.id === e.target),
    )
    .map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle:
        e.kind === "value" ? "value" : "flow:" + (e.source_port ?? "next"),
      targetHandle:
        (e.kind === "value" ? "value:" : "flow:") + (e.target_port ?? "entry"),
      label:
        e.kind === "value"
          ? "Value" + (e.path ? " · " + e.path : "")
          : e.target_port === "next_iteration"
            ? "Next iteration"
            : e.source_port && e.source_port !== "next"
              ? e.source_port
              : undefined,
      type: "smoothstep",
      style: {
        stroke: e.kind === "value" ? "#735214" : "#57717d",
        strokeWidth: 1.5,
        strokeDasharray: e.kind === "value" ? "4 4" : undefined,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        color: e.kind === "value" ? "#735214" : "#57717d",
      },
    }));
  return (
    <ReactFlow<CanvasNode>
      key={graphId}
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={(changes) =>
        setNodes((old) => applyNodeChanges(changes, old))
      }
      onNodeDragStop={(_, node) => onMove(node.id, node.position)}
      nodesDraggable={editing}
      nodesConnectable={editing}
      deleteKeyCode={null}
      onConnect={onConnect}
      onNodeClick={(_, node) => onSelect(node.id)}
      onPaneContextMenu={(e) => {
        e.preventDefault();
        onMenu(e, {
          kind: "canvas",
          point: flow.screenToFlowPosition({ x: e.clientX, y: e.clientY }),
        });
      }}
      onNodeContextMenu={(e, node) => {
        e.preventDefault();
        onMenu(e, {
          kind: node.type === "area" ? "area" : "card",
          id: node.id,
        });
      }}
      onEdgeContextMenu={(e, edge) => {
        e.preventDefault();
        onMenu(e, { kind: "edge", id: edge.id });
      }}
      onMoveStart={(event) => {
        if (event) onInspect();
      }}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.2}
      maxZoom={1.5}
    >
      <Background gap={24} size={1} />
      <Controls
        showZoom={false}
        showFitView={false}
        showInteractive={false}
        orientation="horizontal"
      >
        <ControlButton aria-label="Zoom in" onClick={() => flow.zoomIn()}>
          <Plus size={20} />
        </ControlButton>
        <ControlButton aria-label="Zoom out" onClick={() => flow.zoomOut()}>
          <Minus size={20} />
        </ControlButton>
        <ControlButton
          aria-label="Fit workflow"
          onClick={() => flow.fitView({ padding: 0.2 })}
        >
          <Maximize2 size={20} />
        </ControlButton>
      </Controls>
      <MiniMap
        pannable
        zoomable
        style={{ width: 130, height: 80 }}
        nodeColor={(n) =>
          n.data.status === "failed"
            ? "#a12424"
            : ["passed", "recorded", "running"].includes(String(n.data.status))
              ? "#146040"
              : "#9aafb6"
        }
      />
    </ReactFlow>
  );
}
