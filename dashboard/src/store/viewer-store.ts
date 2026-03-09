import { create } from 'zustand';
import type { ExplodeDirection, ModelManifest } from '../types/viewer';

interface ViewerState {
  glbUrl: string | null;
  manifest: ModelManifest | null;
  selectedMeshName: string | null;
  hiddenMeshes: Set<string>;
  explodeFactor: number;
  explodeDirection: ExplodeDirection;
  animating: boolean;
  viewMode: '3d' | 'graph';

  loadModel: (glbUrl: string, manifest: ModelManifest) => void;
  selectPart: (meshName: string | null) => void;
  toggleVisibility: (meshName: string) => void;
  setExplodeFactor: (factor: number) => void;
  toggleExplodeDirection: () => void;
  toggleExplode: () => void;
  resetExplode: () => void;
  setAnimating: (animating: boolean) => void;
  setViewMode: (mode: '3d' | 'graph') => void;
  reset: () => void;
}

export const useViewerStore = create<ViewerState>((set, get) => ({
  glbUrl: null,
  manifest: null,
  selectedMeshName: null,
  hiddenMeshes: new Set<string>(),
  explodeFactor: 0,
  explodeDirection: 'radial' as ExplodeDirection,
  animating: false,
  viewMode: 'graph',

  loadModel: (glbUrl, manifest) =>
    set({ glbUrl, manifest, selectedMeshName: null, hiddenMeshes: new Set(), explodeFactor: 0, viewMode: '3d' }),

  selectPart: (meshName) => set({ selectedMeshName: meshName }),

  toggleVisibility: (meshName) => {
    const { hiddenMeshes } = get();
    const next = new Set(hiddenMeshes);
    if (next.has(meshName)) {
      next.delete(meshName);
    } else {
      next.add(meshName);
    }
    set({ hiddenMeshes: next });
  },

  setExplodeFactor: (factor) => set({ explodeFactor: Math.max(0, Math.min(100, factor)) }),

  toggleExplodeDirection: () =>
    set((state) => ({
      explodeDirection: state.explodeDirection === 'radial' ? 'axial' : 'radial',
    })),

  toggleExplode: () => {
    const current = get().explodeFactor;
    set({ explodeFactor: current > 0 ? 0 : 100, animating: true });
  },

  resetExplode: () => set({ explodeFactor: 0, animating: true }),

  setAnimating: (animating) => set({ animating }),

  setViewMode: (mode) => set({ viewMode: mode }),

  reset: () =>
    set({
      glbUrl: null,
      manifest: null,
      selectedMeshName: null,
      hiddenMeshes: new Set(),
      explodeFactor: 0,
      viewMode: 'graph',
    }),
}));
