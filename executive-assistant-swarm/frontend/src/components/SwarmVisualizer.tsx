import React, { useMemo, useEffect } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Background,
  MarkerType,
  Handle,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './SwarmVisualizer.css';

// Custom Node to support our styling
const CustomNode = ({ data }: any) => {
  return (
    <div className={`swarm-node ${data.isActive ? 'active-node' : ''}`}>
      <Handle type="target" position={Position.Top} className="hidden-handle" />
      <div className="node-icon">{data.icon}</div>
      <div className="node-label">{data.label}</div>
      {data.status && data.isActive && <div className="node-status" title={data.status}>{data.status}</div>}
      <Handle type="source" position={Position.Bottom} className="hidden-handle" />
    </div>
  );
};

const nodeTypes = {
  custom: CustomNode,
};

interface SwarmVisualizerProps {
  logs: { agent: string, status: string }[];
}

export const SwarmVisualizer: React.FC<SwarmVisualizerProps> = ({ logs }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    // Process logs to build nodes and edges
    const uniqueAgents = Array.from(new Set(logs.map(log => log.agent)));
    
    // Ensure Orchestrator is first if it exists
    const orchestratorIdx = uniqueAgents.findIndex(a => a.toLowerCase().includes('orchestrator'));
    if (orchestratorIdx > 0) {
      const orch = uniqueAgents.splice(orchestratorIdx, 1)[0];
      uniqueAgents.unshift(orch);
    }

    const activeAgent = logs.length > 0 ? logs[logs.length - 1].agent : '';
    const activeStatus = logs.length > 0 ? logs[logs.length - 1].status : '';

    const newNodes = uniqueAgents.map((agent, index) => {
      const isOrch = index === 0;
      
      // Calculate position
      let x = 250;
      let y = 50;
      
      if (!isOrch) {
        // Space them out below the orchestrator
        const totalOthers = uniqueAgents.length - 1;
        const spacing = 180;
        const startX = 250 - ((totalOthers - 1) * spacing) / 2;
        x = startX + ((index - 1) * spacing);
        y = 200;
      }

      return {
        id: agent,
        type: 'custom',
        position: { x, y },
        data: { 
          label: agent.replace(/_/g, ' '), 
          isActive: agent === activeAgent,
          status: agent === activeAgent ? activeStatus : '',
          icon: isOrch ? '🧠' : '🤖'
        }
      };
    });

    // Create edges from Orchestrator to everyone else
    const newEdges = uniqueAgents.slice(1).map((agent) => {
      const isActiveEdge = agent === activeAgent;
      return {
        id: `e-${uniqueAgents[0]}-${agent}`,
        source: uniqueAgents[0],
        target: agent,
        animated: isActiveEdge,
        style: { stroke: isActiveEdge ? '#FACC15' : 'rgba(255,255,255,0.2)', strokeWidth: isActiveEdge ? 3 : 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: isActiveEdge ? '#FACC15' : 'rgba(255,255,255,0.2)',
        },
      };
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [logs, setNodes, setEdges]);

  return (
    <div className="swarm-visualizer-container">
      <div className="visualizer-header">
        <div className="pulse-indicator"></div>
        <span>Swarm Network Active</span>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.5, maxZoom: 1.2 }}
        attributionPosition="bottom-right"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#ffffff" gap={16} size={1} opacity={0.05} />
      </ReactFlow>
    </div>
  );
};
