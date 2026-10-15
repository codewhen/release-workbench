import { NodeResizer, type Node, type NodeProps } from "@xyflow/react";
import { ChevronDown, ChevronRight } from "lucide-react";
export interface AreaData extends Record<string, unknown> {
  name: string;
  kind: string;
  collapsed: boolean;
  editing: boolean;
  onCollapse: () => void;
  onResize: (width: number, height: number) => void;
}
export type AreaFlowNode = Node<AreaData, "area">;
export function AreaNode({ data, selected }: NodeProps<AreaFlowNode>) {
  return (
    <div
      className={`layout-area ${data.kind} ${selected ? "chosen" : ""} ${data.collapsed ? "collapsed" : ""}`}
    >
      <NodeResizer
        isVisible={selected && data.editing && !data.collapsed}
        minWidth={300}
        minHeight={150}
        onResizeEnd={(_, p) => data.onResize(p.width, p.height)}
      />
      <div className="area-heading">
        <strong>{data.name}</strong>
        {data.kind === "collapsible" && (
          <button
            className="nodrag"
            disabled={!data.editing}
            aria-label={data.collapsed ? "Expand area" : "Collapse area"}
            aria-expanded={!data.collapsed}
            onClick={data.onCollapse}
          >
            {data.collapsed ? (
              <ChevronRight size={16} />
            ) : (
              <ChevronDown size={16} />
            )}
          </button>
        )}
      </div>
    </div>
  );
}
