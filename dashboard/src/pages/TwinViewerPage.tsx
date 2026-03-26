import { useState, useRef, useCallback, useEffect } from 'react';
import { ChevronDown, Eye } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/shared/StatusBadge';
import { EmptyState } from '../components/ui/EmptyState';
import { formatRelativeTime } from '../utils/format-time';
import { useTwinNodes, useTwinNode } from '../hooks/use-twin';
import { useScopedChat } from '../hooks/use-scoped-chat';
import { NodeChatPanel } from '../components/chat/integrations/NodeChatPanel';
import { R3FViewer } from '../components/viewer/R3FViewer';
import { ComponentTree } from '../components/viewer/ComponentTree';
import { BomAnnotationPanel } from '../components/viewer/BomAnnotationPanel';
import { ExplodedViewControls } from '../components/viewer/ExplodedViewControls';
import { useViewerStore } from '../store/viewer-store';
import { useUploadAndConvert } from '../hooks/use-conversion';
import { getMockManifest, getMockGlbUrl } from '../api/endpoints/convert';
import { getNodeModel } from '../api/endpoints/twin';
import type { TwinNode } from '../types/twin';
import type { ModelManifest, PartInfo, PartTreeNode } from '../types/viewer';

// ── Node type → Material Symbol icon name ──────────────────────────────────
const TYPE_ICONS: Record<TwinNode['type'], string> = {
  work_product: 'description',
  constraint: 'lock',
  relationship: 'link',
  version: 'label',
};

// ── Node type label ─────────────────────────────────────────────────────────
const TYPE_LABELS: Record<TwinNode['type'], string> = {
  work_product: 'WP',
  constraint: 'CON',
  relationship: 'REL',
  version: 'VER',
};

// ── Status dot color (6 px circle) ─────────────────────────────────────────
function StatusDot({ status }: { status: string }) {
  const color =
    status === 'running'
      ? '#f59e0b'
      : status === 'active' || status === 'completed' || status === 'valid' || status === 'ready'
      ? '#3dd68c'
      : '#6b7280';
  return (
    <span
      aria-hidden="true"
      style={{
        display: 'inline-block',
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: color,
        flexShrink: 0,
      }}
    />
  );
}

// ── NodeDetail ──────────────────────────────────────────────────────────────
function NodeDetail({ node }: { node: TwinNode }) {
  const chat = useScopedChat({
    scopeKind: 'digital-twin-node',
    entityId: node.id,
    label: node.name,
  });
  const loadModel = useViewerStore((s) => s.loadModel);
  const setViewMode = useViewerStore((s) => s.setViewMode);
  const [loading3d, setLoading3d] = useState(false);

  const isCAD = node.properties.wp_type === 'cad_model';

  const handleView3D = useCallback(async () => {
    setLoading3d(true);
    try {
      const result = await getNodeModel(node.id);
      const manifest: ModelManifest = {
        parts: result.metadata.parts.map((p) => ({
          name: p.name,
          meshName: p.meshName ?? p.name,
          children: (p.children ?? []) as ModelManifest['parts'],
          boundingBox: p.boundingBox as PartTreeNode['boundingBox'],
        })),
        meshToNodeMap: {},
        materials: result.metadata.materials ?? [],
        stats: result.metadata.stats ?? { triangleCount: 0, fileSize: 0 },
      };
      const glbUrl = result.glb_url.startsWith('/v1/')
        ? `/api${result.glb_url}`
        : result.glb_url;
      loadModel(glbUrl, manifest);
      setViewMode('3d');
    } catch (err) {
      console.error('Failed to load 3D model:', err);
    } finally {
      setLoading3d(false);
    }
  }, [node.id, loadModel, setViewMode]);

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Node header */}
      <div
        className="px-4 py-3 flex-shrink-0"
        style={{ borderBottom: '1px solid rgba(65,72,90,0.2)' }}
      >
        <div className="flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined" style={{ color: '#9a9aaa', fontSize: 16 }}>
            {TYPE_ICONS[node.type]}
          </span>
          <span className="font-mono text-xs font-medium" style={{ color: '#e2e2eb' }}>
            {node.name}
          </span>
          <StatusDot status={node.status} />
        </div>
        <div className="text-xs font-mono" style={{ color: '#9a9aaa' }}>
          {node.domain} &middot; {node.type} &middot; {formatRelativeTime(node.updatedAt)}
        </div>
        <div className="mt-2">
          <StatusBadge status={node.status} />
        </div>
      </div>

      {/* View 3D button */}
      {isCAD && (
        <div className="px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid rgba(65,72,90,0.2)' }}>
          <Button
            variant="primary"
            size="sm"
            onClick={handleView3D}
            disabled={loading3d}
            className="text-xs"
          >
            <Eye size={13} className="mr-1.5" />
            {loading3d ? 'Converting...' : 'View 3D Model'}
          </Button>
        </div>
      )}

      {/* Properties table */}
      <div className="px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid rgba(65,72,90,0.2)' }}>
        <div
          className="font-mono text-xs mb-2 uppercase tracking-widest"
          style={{ color: '#9a9aaa', fontSize: 10, letterSpacing: '0.1em' }}
        >
          Properties
        </div>
        <table className="w-full" style={{ borderCollapse: 'collapse' }}>
          <tbody>
            {Object.entries(node.properties).map(([key, value]) => (
              <tr key={key} style={{ borderBottom: '1px solid rgba(65,72,90,0.1)' }}>
                <td
                  className="py-1 pr-3 font-mono text-xs align-top"
                  style={{ color: '#9a9aaa', width: '40%' }}
                >
                  {key}
                </td>
                <td
                  className="py-1 font-mono text-xs align-top"
                  style={{ color: '#e2e2eb' }}
                >
                  {String(value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Chat panel */}
      <div className="px-4 py-3 flex-1 min-h-0">
        <NodeChatPanel
          nodeId={node.id}
          nodeName={node.name}
          thread={chat.thread}
          messages={chat.messages}
          isTyping={chat.isTyping}
          onSendMessage={chat.sendMessage}
          onCreateThread={chat.createThread}
        />
      </div>
    </div>
  );
}

// ── GraphView (two-panel: node list + node detail) ──────────────────────────
function GraphView() {
  const { data: nodes, isLoading } = useTwinNodes();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data: selectedNode } = useTwinNode(selectedId ?? undefined);

  if (isLoading) {
    return (
      <div
        className="flex-1 flex items-center justify-center font-mono text-xs"
        style={{ color: '#9a9aaa' }}
      >
        Loading twin graph...
      </div>
    );
  }

  const items = nodes ?? [];

  if (items.length === 0) {
    return (
      <EmptyState
        title="Empty twin"
        description="Digital Twin nodes will appear here when work_products are created."
      />
    );
  }

  return (
    <div className="flex h-full">
      {/* Left panel — node list */}
      <div
        className="glass flex flex-col overflow-hidden flex-shrink-0"
        style={{
          width: 260,
          background: 'rgba(30,31,38,0.85)',
          border: '1px solid rgba(65,72,90,0.2)',
          borderRadius: 8,
          margin: '12px 0 12px 12px',
        }}
      >
        {/* Panel header */}
        <div
          className="px-3 py-2 flex-shrink-0 flex items-center gap-2"
          style={{ borderBottom: '1px solid rgba(65,72,90,0.2)' }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 14, color: '#9a9aaa' }}>
            hub
          </span>
          <span
            className="font-mono uppercase tracking-widest"
            style={{ fontSize: 10, color: '#9a9aaa', letterSpacing: '0.1em' }}
          >
            Nodes
          </span>
          <span
            className="ml-auto font-mono rounded px-1.5"
            style={{
              fontSize: 10,
              background: 'rgba(40,42,48,1)',
              color: '#9a9aaa',
            }}
          >
            {items.length}
          </span>
        </div>

        {/* Node list */}
        <ul className="flex-1 overflow-y-auto" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {items.map((node) => {
            const isActive = selectedId === node.id;
            return (
              <li key={node.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(node.id)}
                  className="flex w-full items-center gap-2 text-left transition-colors"
                  style={{
                    height: 36,
                    padding: '0 12px',
                    background: isActive ? 'rgba(40,42,48,1)' : 'transparent',
                    borderLeft: isActive ? '2px solid #e67e22' : '2px solid transparent',
                    cursor: 'pointer',
                    border: 'none',
                    outline: 'none',
                    width: '100%',
                    borderLeftWidth: 2,
                    borderLeftStyle: 'solid',
                    borderLeftColor: isActive ? '#e67e22' : 'transparent',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLButtonElement).style.background = 'rgba(40,42,48,0.6)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                    }
                  }}
                >
                  <StatusDot status={node.status} />
                  <span
                    className="material-symbols-outlined flex-shrink-0"
                    style={{
                      fontSize: 14,
                      color: isActive ? '#e67e22' : '#9a9aaa',
                    }}
                  >
                    {TYPE_ICONS[node.type]}
                  </span>
                  <span
                    className="flex-1 truncate font-mono text-xs"
                    style={{ color: isActive ? '#e2e2eb' : '#9a9aaa' }}
                  >
                    {node.name}
                  </span>
                  <span
                    className="font-mono rounded flex-shrink-0"
                    style={{
                      fontSize: 10,
                      background: 'rgba(40,42,48,1)',
                      color: '#9a9aaa',
                      padding: '0 6px',
                    }}
                  >
                    {TYPE_LABELS[node.type]}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Right panel — node detail */}
      <div
        className="glass flex flex-col overflow-hidden flex-1"
        style={{
          background: 'rgba(30,31,38,0.85)',
          border: '1px solid rgba(65,72,90,0.2)',
          borderRadius: 8,
          margin: '12px 12px 12px 8px',
        }}
      >
        {selectedNode ? (
          <NodeDetail node={selectedNode} />
        ) : (
          <div
            className="flex flex-1 items-center justify-center font-mono text-xs"
            style={{ color: '#9a9aaa' }}
          >
            Select a node to view details
          </div>
        )}
      </div>
    </div>
  );
}

// ── ConversionPhase ─────────────────────────────────────────────────────────
type ConversionPhase = 'idle' | 'uploading' | 'converting' | 'loading';

// ── ViewerToolbar ───────────────────────────────────────────────────────────
function ViewerToolbar({
  onToggleImport,
  importOpen,
}: {
  onToggleImport: () => void;
  importOpen: boolean;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadMutation = useUploadAndConvert();
  const viewMode = useViewerStore((s) => s.viewMode);
  const setViewMode = useViewerStore((s) => s.setViewMode);
  const loadModel = useViewerStore((s) => s.loadModel);
  const glbUrl = useViewerStore((s) => s.glbUrl);
  const [quality, setQuality] = useState('standard');
  const [conversionPhase, setConversionPhase] = useState<ConversionPhase>('idle');

  useEffect(() => {
    if (!uploadMutation.isPending) {
      if (uploadMutation.isSuccess && conversionPhase === 'converting') {
        setConversionPhase('loading');
        const t = setTimeout(() => setConversionPhase('idle'), 800);
        return () => clearTimeout(t);
      }
      if (!uploadMutation.isSuccess) {
        setConversionPhase('idle');
      }
    }
  }, [uploadMutation.isPending, uploadMutation.isSuccess, conversionPhase]);

  const handleUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setConversionPhase('uploading');
        const t = setTimeout(() => setConversionPhase('converting'), 1200);
        uploadMutation.mutate(
          { file, quality },
          { onSettled: () => clearTimeout(t) },
        );
      }
    },
    [uploadMutation, quality],
  );

  const handleLoadMock = useCallback(() => {
    loadModel(getMockGlbUrl(), getMockManifest());
  }, [loadModel]);

  const toolbarBtn =
    'bg-surface-high text-on-surface-variant hover:text-on-surface text-xs rounded px-2 py-1 transition-colors border-0 cursor-pointer';

  return (
    <div className="flex items-center gap-2">
      {/* Import toggle */}
      <button
        type="button"
        onClick={onToggleImport}
        className={toolbarBtn}
        style={
          importOpen
            ? { background: 'rgba(230,126,34,0.15)', color: '#e67e22' }
            : undefined
        }
      >
        <span className="material-symbols-outlined" style={{ fontSize: 14, verticalAlign: 'middle', marginRight: 4 }}>
          file_upload
        </span>
        Import
      </button>

      {/* View mode toggle */}
      <div
        className="flex items-center overflow-hidden rounded"
        style={{ border: '1px solid rgba(65,72,90,0.3)' }}
      >
        <button
          type="button"
          onClick={() => setViewMode('3d')}
          className="text-xs px-2 py-1 transition-colors border-0 cursor-pointer"
          style={{
            background: viewMode === '3d' ? 'rgba(230,126,34,0.15)' : 'rgba(40,42,48,0.9)',
            color: viewMode === '3d' ? '#e67e22' : '#9a9aaa',
            fontFamily: "'Roboto Mono', monospace",
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 13, verticalAlign: 'middle', marginRight: 3 }}>
            view_in_ar
          </span>
          3D
        </button>
        <div style={{ width: 1, height: 16, background: 'rgba(65,72,90,0.4)' }} />
        <button
          type="button"
          onClick={() => setViewMode('graph')}
          className="text-xs px-2 py-1 transition-colors border-0 cursor-pointer"
          style={{
            background: viewMode === 'graph' ? 'rgba(230,126,34,0.15)' : 'rgba(40,42,48,0.9)',
            color: viewMode === 'graph' ? '#e67e22' : '#9a9aaa',
            fontFamily: "'Roboto Mono', monospace",
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 13, verticalAlign: 'middle', marginRight: 3 }}>
            hub
          </span>
          Graph
        </button>
      </div>

      {viewMode === '3d' && (
        <>
          {/* Quality selector */}
          <div className="relative">
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
              className="appearance-none rounded text-xs px-2 py-1 pr-6 font-mono cursor-pointer"
              style={{
                background: 'rgba(40,42,48,0.9)',
                border: '1px solid rgba(65,72,90,0.3)',
                color: '#9a9aaa',
              }}
            >
              <option value="preview">Preview</option>
              <option value="standard">Standard</option>
              <option value="fine">Fine</option>
            </select>
            <ChevronDown
              size={11}
              className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2"
              style={{ color: '#9a9aaa' }}
            />
          </div>

          {/* Upload button / progress */}
          {conversionPhase !== 'idle' ? (
            <div
              className="flex items-center gap-1.5 rounded px-2 py-1 text-xs font-mono"
              style={{
                background: 'rgba(40,42,48,0.9)',
                border: '1px solid rgba(65,72,90,0.3)',
                color: '#9a9aaa',
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 13, color: '#e67e22' }}>
                sync
              </span>
              {conversionPhase === 'uploading'
                ? 'Uploading...'
                : conversionPhase === 'converting'
                ? 'Converting...'
                : 'Loading...'}
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
              className={toolbarBtn}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 13, verticalAlign: 'middle', marginRight: 3 }}>
                upload_file
              </span>
              Upload STEP
            </button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".step,.stp,.iges,.igs"
            className="hidden"
            onChange={handleUpload}
          />

          {/* Load demo */}
          {!glbUrl && (
            <button
              type="button"
              onClick={handleLoadMock}
              className="text-xs rounded px-2 py-1 cursor-pointer transition-colors border-0"
              style={{
                background: 'transparent',
                border: '1px dashed rgba(65,72,90,0.4)',
                color: '#9a9aaa',
              }}
            >
              Demo
            </button>
          )}
        </>
      )}
    </div>
  );
}

// ── TwinViewerPage ──────────────────────────────────────────────────────────
export function TwinViewerPage() {
  const viewMode = useViewerStore((s) => s.viewMode);
  const manifest = useViewerStore((s) => s.manifest);
  const glbUrl = useViewerStore((s) => s.glbUrl);
  const selectPart = useViewerStore((s) => s.selectPart);
  const selectedMeshName = useViewerStore((s) => s.selectedMeshName);
  const { data: nodes } = useTwinNodes();
  const [importOpen, setImportOpen] = useState(false);

  const handlePartClick = useCallback(
    (part: PartInfo) => {
      selectPart(part.meshName);
    },
    [selectPart],
  );

  const items = nodes ?? [];

  return (
    <div
      className="flex flex-col"
      style={{
        height: 'calc(100vh - 4rem)',
        background: '#111319',
      }}
    >
      {/* ── Header ── */}
      <div
        className="flex items-center justify-between px-4 flex-shrink-0"
        style={{
          height: 52,
          borderBottom: '1px solid rgba(65,72,90,0.2)',
          background: 'rgba(25,27,34,0.95)',
        }}
      >
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined" style={{ color: '#e67e22', fontSize: 18 }}>
            hub
          </span>
          <div>
            <span
              className="font-mono text-xs uppercase tracking-widest"
              style={{ color: '#e2e2eb', letterSpacing: '0.1em' }}
            >
              Digital Twin
            </span>
            <span
              className="ml-3 font-mono text-xs"
              style={{ color: '#9a9aaa' }}
            >
              {items.length} node{items.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>

        <ViewerToolbar
          onToggleImport={() => setImportOpen((prev) => !prev)}
          importOpen={importOpen}
        />
      </div>

      {/* ── Import slide-in panel ── */}
      {importOpen && (
        <div
          className="flex-shrink-0 px-4 py-3"
          style={{
            borderBottom: '1px solid rgba(65,72,90,0.2)',
            background: 'rgba(30,31,38,0.95)',
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <span
              className="font-mono text-xs uppercase tracking-widest"
              style={{ color: '#9a9aaa', letterSpacing: '0.1em' }}
            >
              Import Work Product
            </span>
            <button
              type="button"
              aria-label="Close import panel"
              onClick={() => setImportOpen(false)}
              className="flex items-center justify-center rounded transition-colors cursor-pointer border-0 p-1"
              style={{ background: 'transparent', color: '#9a9aaa' }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = '#e2e2eb';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = '#9a9aaa';
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                close
              </span>
            </button>
          </div>

          {/* Drop zone */}
          <div
            className="flex flex-col items-center justify-center rounded cursor-pointer transition-colors"
            style={{
              border: '2px dashed rgba(65,72,90,0.4)',
              padding: '24px 16px',
              color: '#9a9aaa',
              textAlign: 'center',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(230,126,34,0.4)';
              (e.currentTarget as HTMLDivElement).style.background = 'rgba(230,126,34,0.04)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(65,72,90,0.4)';
              (e.currentTarget as HTMLDivElement).style.background = 'transparent';
            }}
          >
            <span className="material-symbols-outlined mb-2" style={{ fontSize: 28, color: '#9a9aaa' }}>
              file_upload
            </span>
            <p className="font-mono text-xs" style={{ color: '#e2e2eb', marginBottom: 4 }}>
              Drag &amp; drop a file here, or click to browse
            </p>
            <p className="font-mono" style={{ fontSize: 10, color: '#9a9aaa' }}>
              .step .stp .iges .igs .kicad_sch .kicad_pcb .fcstd &middot; max 100 MB
            </p>
          </div>
        </div>
      )}

      {/* ── Content ── */}
      {viewMode === 'graph' ? (
        <div className="flex flex-1 overflow-hidden">
          <GraphView />
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Component Tree Sidebar */}
          {manifest && (
            <div
              className="flex-shrink-0"
              style={{
                width: 240,
                borderRight: '1px solid rgba(65,72,90,0.2)',
              }}
            >
              <ComponentTree />
            </div>
          )}

          {/* 3D Viewer (center) */}
          <div className="relative flex-1">
            <R3FViewer onPartClick={handlePartClick} />
            {glbUrl && <ExplodedViewControls />}
          </div>

          {/* BOM Annotation Panel (right) */}
          {selectedMeshName && manifest && (
            <div
              className="flex-shrink-0"
              style={{
                width: 320,
                borderLeft: '1px solid rgba(65,72,90,0.2)',
              }}
            >
              <BomAnnotationPanel />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
