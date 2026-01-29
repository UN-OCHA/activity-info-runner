import type { TreeNodeInfo } from "@blueprintjs/core";
import {
  Card,
  Divider,
  Elevation,
  EntityTitle,
  HTMLTable,
  SegmentedControl,
  Tree,
} from "@blueprintjs/core";
import type { BlueprintIcons_16 } from "@blueprintjs/icons/lib/esm/generated/16px/blueprint-icons-16";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from "d3-force";
import { useEffect, useMemo, useState } from "react";
import { Group, Panel } from "react-resizable-panels";
import type {
  FieldDefinition,
  MaterializedBoundary,
  MaterializedDatabase,
  MaterializedForm,
} from "../types";

type NodeType = Node<{
  label: string;
  subTitle?: string;
  icon: BlueprintIcons_16;
  bg: string;
}>;

/* -----------------------------
   Custom Node Component
------------------------------ */

const CardNode = ({ data, selected }: NodeProps<NodeType>) => {
  return (
    <Card
      compact
      interactive
      elevation={selected ? Elevation.THREE : Elevation.ZERO}
      style={{
        border: selected ? "2px solid #2B95D6" : "1px solid #C5CED6",
        background: (data.bg as string) || "#ffffff",
        fontWeight: selected ? "bold" : "normal",
      }}
    >
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
      <EntityTitle
        title={data.label}
        subtitle={data.subTitle}
        icon={data.icon}
        className="whitespace-nowrap"
      />
    </Card>
  );
};

const nodeTypes = {
  card: CardNode,
};

/* -----------------------------
   Types
------------------------------ */

type ViewMode = "fields" | "records";

interface D3Node extends SimulationNodeDatum {
  id: string;
  type: "db" | "form" | "field" | "record";
  label: string;
  subTitle?: string;
}

interface D3Link extends SimulationLinkDatum<D3Node> {
  source: string | D3Node;
  target: string | D3Node;
}

/* -----------------------------
   Tree Builders
------------------------------ */

const makeFieldNode = (
  field: FieldDefinition,
  formId: string,
  selectedId: string | null,
): TreeNodeInfo => {
  const nodeId = `field:${formId}:${field.id}`;
  return {
    id: nodeId,
    label: field.code,
    icon: "text-highlight",
    hasCaret: false,
    isSelected: nodeId === selectedId,
  };
};

const makeFormChildren = (
  form: MaterializedForm,
  viewMode: ViewMode,
  selectedId: string | null,
): TreeNodeInfo[] => {
  if (viewMode === "fields") {
    return form.fields.map((f) => makeFieldNode(f, form.id, selectedId));
  }

  const allRecordsId = `records:${form.id}:all`;
  return [
    {
      id: allRecordsId,
      label: `${form.records} records`,
      icon: "layers",
      hasCaret: false,
      isSelected: allRecordsId === selectedId,
    },
  ];
};

const makeFormNode = (
  form: MaterializedForm,
  expanded: Record<string, boolean>,
  viewMode: ViewMode,
  selectedId: string | null,
): TreeNodeInfo => {
  const nodeId = `form:${form.id}`;
  return {
    id: nodeId,
    label: form.label,
    icon: "application",
    isExpanded: !!expanded[nodeId],
    isSelected: nodeId === selectedId,
    childNodes: makeFormChildren(form, viewMode, selectedId),
  };
};

const makeDatabaseNode = (
  db: MaterializedDatabase,
  expanded: Record<string, boolean>,
  viewMode: ViewMode,
  selectedId: string | null,
): TreeNodeInfo => {
  const nodeId = `db:${db.databaseId}`;
  return {
    id: nodeId,
    label: db.label,
    icon: "database",
    isExpanded: !!expanded[nodeId],
    isSelected: nodeId === selectedId,
    childNodes: db.forms.map((form) =>
      makeFormNode(form, expanded, viewMode, selectedId),
    ),
  };
};

/* -----------------------------
   D3 Force Layout Builder
------------------------------ */

function buildFlowFromBoundaries(
  boundaries: MaterializedBoundary,
  viewMode: ViewMode,
): {
  nodes: Node[];
  edges: Edge[];
} {
  const d3Nodes: D3Node[] = [];
  const d3Links: D3Link[] = [];

  const GALAXY_RADIUS = 600;
  let totalForms = 0;
  boundaries.databases.forEach((db) => (totalForms += db.forms.length));
  let formIndex = 0;

  boundaries.databases.forEach((db) => {
    const dbId = `db:${db.databaseId}`;
    d3Nodes.push({
      id: dbId,
      type: "db",
      label: `DB: ${db.databaseId}`,
      x: 0,
      y: 0,
    });

    db.forms.forEach((form) => {
      const formId = `form:${form.id}`;

      const angle = (formIndex / Math.max(1, totalForms)) * 2 * Math.PI;
      const initialX = Math.cos(angle) * GALAXY_RADIUS;
      const initialY = Math.sin(angle) * GALAXY_RADIUS;

      d3Nodes.push({
        id: formId,
        type: "form",
        label: form.label,
        x: initialX,
        y: initialY,
      });

      d3Links.push({ source: dbId, target: formId });

      if (viewMode === "fields") {
        form.fields.forEach((field) => {
          const fieldId = `field:${form.id}:${field.id}`;
          d3Nodes.push({
            id: fieldId,
            type: "field",
            label: field.code,
            x: initialX + (Math.random() * 50 - 25),
            y: initialY + (Math.random() * 50 - 25),
            subTitle: field.label,
          });
          d3Links.push({ source: formId, target: fieldId });
        });
      } else {
        const allRecId = `records:${form.id}:all`;
        d3Nodes.push({
          id: allRecId,
          type: "record",
          label: `${form.records} records`,
          x: initialX + (Math.random() * 50 - 25),
          y: initialY + (Math.random() * 50 - 25),
        });
        d3Links.push({ source: formId, target: allRecId });
      }
      formIndex++;
    });
  });

  const simulation = forceSimulation(d3Nodes)
    .force(
      "link",
      forceLink(d3Links)
        .id((d) => (d as D3Node).id)
        .distance((link) => {
          const source = link.source as D3Node;
          const target = link.target as D3Node;
          if (source.type === "db" || target.type === "db") return 400;
          return 150;
        })
        .strength((link) => {
          const source = link.source as D3Node;
          if (source.type === "db") return 0.2;
          return 1;
        }),
    )
    .force("charge", forceManyBody().strength(-1000))
    .force(
      "collide",
      forceCollide((d) => {
        const node = d as D3Node;
        if (node.type === "db") return 200;
        if (node.type === "form") return 200;
        const base = 60;
        const extra =
          node.label.length * 2 + ((node as any).subTitle?.length ?? 0) * 1.8;
        return base + extra;
      }).strength(1),
    )
    .force("x", forceX(0).strength(0.04))
    .force("y", forceY(0).strength(0.04))
    .stop();

  simulation.tick(300);

  const getIcon = (type: string): BlueprintIcons_16 => {
    switch (type) {
      case "db":
        return "database" as BlueprintIcons_16;
      case "form":
        return "application" as BlueprintIcons_16;
      case "field":
        return "text-highlight" as BlueprintIcons_16;
      case "record":
        return "th-derived" as BlueprintIcons_16;
      default:
        return "symbol-circle" as BlueprintIcons_16;
    }
  };

  const nodes: NodeType[] = d3Nodes.map((node) => ({
    id: node.id,
    type: "card",
    position: { x: (node.x ?? 0) - 100, y: (node.y ?? 0) - 30 },
    data: {
      label: node.label,
      subTitle: node.subTitle,
      icon: getIcon(node.type),
      bg:
        node.type === "db"
          ? "#d9ecff"
          : node.type === "form"
            ? "#FFFFFF"
            : "#F5F8FA",
    },
    selected: false,
  }));

  const edges: Edge[] = d3Links.map((link) => {
    const sourceId = (link.source as D3Node).id;
    const targetId = (link.target as D3Node).id;
    const isChildLink =
      targetId.startsWith("field:") ||
      targetId.startsWith("record:") ||
      targetId.startsWith("records:");

    return {
      id: `e-${sourceId}-${targetId}`,
      source: sourceId,
      target: targetId,
      style: {
        stroke: isChildLink ? "#D1D5DB" : "#9AA5B1",
        strokeWidth: isChildLink ? 1 : 2,
      },
    };
  });

  return { nodes, edges };
}

/* -----------------------------
   Inspector Utils
------------------------------ */

const PropertyRow = ({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) => (
  <tr>
    <td className="text-gray-500 text-xs py-1 pr-2 align-top">{label}</td>
    <td className="text-gray-900 text-xs py-1 font-mono break-all">{value}</td>
  </tr>
);

const InspectorContent = ({
  selection,
}: {
  selection: { type: string; data: unknown } | null;
}) => {
  if (!selection) {
    return (
      <div className="flex flex-col h-full justify-center text-gray-400 text-sm italic text-center">
        Select an element to view details
      </div>
    );
  }

  const { type, data } = selection;

  const renderProperties = () => {
    // Database
    if (type === "Database") {
      const db = data as MaterializedDatabase;
      return (
        <>
          <PropertyRow label="DB ID" value={db.databaseId} />
          <PropertyRow label="Description" value={db.description} />
          <PropertyRow label="Forms" value={db.forms.length} />
        </>
      );
    }

    // Form
    if (type === "Form") {
      const form = data as MaterializedForm;
      return (
        <>
          <PropertyRow label="ID" value={form.id} />
          <PropertyRow label="Label" value={form.label} />
          <PropertyRow label="DB Ref" value={form.databaseId} />
          <PropertyRow label="Fields" value={form.fields.length} />
          <PropertyRow label="Records" value={form.records.toString()} />
        </>
      );
    }

    // Field
    if (type === "Field") {
      const field = data as FieldDefinition;
      return (
        <>
          <PropertyRow label="ID" value={field.id} />
          <PropertyRow label="Code" value={field.code} />
          <PropertyRow label="Type" value={field.type} />
          <PropertyRow label="Label" value={field.label} />
          <PropertyRow label="Key" value={field.key ? "Yes" : "No"} />
          <PropertyRow label="Required" value={field.required ? "Yes" : "No"} />
          {field.relevance_condition && (
            <PropertyRow label="Relevance" value={field.relevance_condition} />
          )}
          {field.validation_condition && (
            <PropertyRow
              label="Validation"
              value={field.validation_condition}
            />
          )}
          {field.type_parameters &&
            Object.keys(field.type_parameters).length > 0 && (
              <PropertyRow
                label="Params"
                value={JSON.stringify(field.type_parameters)}
              />
            )}
        </>
      );
    }

    // Record
    if (type === "Record") {
      const rec = data as { id: string };
      return <PropertyRow label="Record ID" value={rec.id} />;
    }

    // Default (Group or Unknown)
    const label = (data as Record<string, unknown>).label as string | undefined;
    return <PropertyRow label="Info" value={label || JSON.stringify(data)} />;
  };

  return (
    <div className="p-2">
      <HTMLTable className="w-full" compact>
        <tbody>{renderProperties()}</tbody>
      </HTMLTable>
    </div>
  );
};

/* -----------------------------
   Component
------------------------------ */

function BoundariesFlowContent({
  boundaries,
}: {
  boundaries: MaterializedBoundary;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [viewMode, setViewMode] = useState<ViewMode>("fields");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const { fitView } = useReactFlow();

  const selectionDetails = (() => {
    if (!selectedId) return null;

    if (selectedId.startsWith("db:")) {
      const dbId = selectedId.replace("db:", "");
      const db = boundaries.databases.find((d) => d.databaseId === dbId);
      return db ? { type: "Database", data: db } : null;
    }

    if (selectedId.startsWith("form:")) {
      const formId = selectedId.replace("form:", "");
      for (const db of boundaries.databases) {
        const form = db.forms.find((f) => f.id === formId);
        if (form) return { type: "Form", data: form };
      }
    }

    if (selectedId.startsWith("field:")) {
      // ID format: field:formId:fieldId
      const parts = selectedId.split(":");
      const formId = parts[1];
      const fieldId = parts[2];
      for (const db of boundaries.databases) {
        const form = db.forms.find((f) => f.id === formId);
        if (form) {
          const field = form.fields.find((f) => f.id === fieldId);
          if (field) return { type: "Field", data: field };
        }
      }
    }

    if (selectedId.startsWith("record:")) {
      const recordId = selectedId.replace("record:", "");
      return { type: "Record", data: { id: recordId } };
    }

    if (selectedId.startsWith("records:")) {
      return { type: "Group", data: { label: "All Records" } };
    }

    return null;
  })();

  const toggleNode = (id: string | number) => {
    const key = String(id);
    setExpanded((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handlePaneClick = () => {
    setSelectedId(null);
  };

  const parentMap = useMemo(() => {
    const map = new Map<string, string>();
    boundaries.databases.forEach((db) => {
      const dbNodeId = `db:${db.databaseId}`;
      db.forms.forEach((form) => {
        const formNodeId = `form:${form.id}`;
        map.set(formNodeId, dbNodeId);
        form.fields.forEach((field) => {
          const fieldNodeId = `field:${form.id}:${field.id}`;
          map.set(fieldNodeId, formNodeId);
        });
        const allRecId = `records:${form.id}:all`;
        map.set(allRecId, formNodeId);
      });
    });
    return map;
  }, [boundaries]);

  const treeContents = useMemo<ReadonlyArray<TreeNodeInfo>>(
    () =>
      boundaries.databases.map((db) =>
        makeDatabaseNode(db, expanded, viewMode, selectedId),
      ),
    [boundaries, expanded, viewMode, selectedId],
  );

  const layout = useMemo(
    () => buildFlowFromBoundaries(boundaries, viewMode),
    [boundaries, viewMode],
  );

  useEffect(() => {
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [layout, setNodes, setEdges]);

  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        selected: node.id === selectedId,
      })),
    );

    if (selectedId) {
      fitView({
        nodes: [{ id: selectedId }],
        duration: 800,
        padding: 0.5,
        maxZoom: 1.5,
      });
    }
  }, [selectedId, fitView, setNodes]);

  const handleTreeClick = (node: TreeNodeInfo) => {
    const id = String(node.id);
    setSelectedId(id);
    expandParents(id);
  };

  const handleFlowClick = (_: React.MouseEvent, node: Node) => {
    setSelectedId(node.id);
    expandParents(node.id);
  };

  const expandParents = (id: string) => {
    setExpanded((prev) => {
      const next = { ...prev };
      let currentId: string | undefined = id;
      let changed = false;
      while (currentId && parentMap.has(currentId)) {
        const parentId: string = parentMap.get(currentId)!;
        if (!next[parentId]) {
          next[parentId] = true;
          changed = true;
        }
        currentId = parentId;
      }
      return changed ? next : prev;
    });
  };

  return (
    <Group className="h-full">
      <Panel
        className="h-full flex flex-col"
        minSize={285}
        defaultSize={285}
        collapsible
        collapsedSize={0}
      >
        <div className="flex flex-row gap-2 justify-between mx-2 mt-1">
          <EntityTitle
            title="Tree view"
            icon="diagram-tree"
            className="whitespace-nowrap"
          />
          <SegmentedControl
            size="small"
            options={[
              { label: "Fields", value: "fields", icon: "text-highlight" },
              { label: "Records", value: "records", icon: "th-derived" },
            ]}
            value={viewMode}
            onValueChange={(value) => setViewMode(value as ViewMode)}
          />
        </div>
        <Divider />
        <Tree
          compact
          contents={treeContents}
          onNodeExpand={(node) => toggleNode(node.id)}
          onNodeCollapse={(node) => toggleNode(node.id)}
          onNodeClick={handleTreeClick}
          className="h-full overflow-y-auto"
        />
      </Panel>
      <Divider />
      <Panel className="h-full relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleFlowClick}
          onPaneClick={handlePaneClick}
          fitView
          nodesDraggable={false}
        >
          <Background />
          <MiniMap pannable zoomable />
          <Controls />
        </ReactFlow>
        <EntityTitle
          title="Graph view"
          icon="graph"
          className="absolute top-0 left-0 whitespace-nowrap bg-white p-2"
        />
      </Panel>
      <Divider />
      <Panel
        className="h-full flex flex-col bg-white"
        minSize={200}
        defaultSize={200}
        maxSize={400}
        collapsible
        collapsedSize={0}
      >
        <EntityTitle
          title="Inspector"
          icon="info-sign"
          className="whitespace-nowrap my-2 mx-1 mb-0"
        />
        <div className="overflow-y-auto flex-1">
          <InspectorContent selection={selectionDetails} />
        </div>
      </Panel>
    </Group>
  );
}

export default function BoundariesView(props: {
  boundaries: MaterializedBoundary;
}) {
  return (
    <ReactFlowProvider>
      <BoundariesFlowContent {...props} />
    </ReactFlowProvider>
  );
}
