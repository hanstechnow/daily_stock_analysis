
import { create } from 'zustand';
import axios from 'axios';

const API_BASE = '/api/v1/quant';

interface Strategy {
  id: string;
  name: string;
  description: string;
  code: string;
  status: 'active' | 'inactive';
  created_at: string;
}

interface QuantStore {
  strategies: Strategy[];
  loading: boolean;
  generatedCode: string;
  
  fetchStrategies: () => Promise<void>;
  generateStrategy: (desc: string) => Promise<void>;
  saveStrategy: (name: string, desc: string, code: string) => Promise<void>;
  deleteStrategy: (id: string) => Promise<void>;
  toggleStrategy: (id: string, status: 'active' | 'inactive') => Promise<void>;
  clearGeneratedCode: () => void;
}

export const useQuantStore = create<QuantStore>((set, get) => ({
  strategies: [],
  loading: false,
  generatedCode: '',

  fetchStrategies: async () => {
    set({ loading: true });
    try {
      const res = await axios.get(`${API_BASE}/strategies`);
      set({ strategies: res.data });
    } catch (e) {
      console.error(e);
    } finally {
      set({ loading: false });
    }
  },

  generateStrategy: async (desc: string) => {
    set({ loading: true });
    try {
      const res = await axios.post(`${API_BASE}/strategies/generate`, { description: desc });
      set({ generatedCode: res.data.code });
    } catch (e) {
      console.error(e);
    } finally {
      set({ loading: false });
    }
  },

  saveStrategy: async (name, desc, code) => {
    try {
      await axios.post(`${API_BASE}/strategies`, { name, description: desc, code });
      get().fetchStrategies();
    } catch (e) {
      console.error(e);
    }
  },

  deleteStrategy: async (id) => {
    try {
      await axios.delete(`${API_BASE}/strategies/${id}`);
      get().fetchStrategies();
    } catch (e) {
      console.error(e);
    }
  },

  toggleStrategy: async (id, status) => {
    try {
      await axios.patch(`${API_BASE}/strategies/${id}/status`, { status });
      // Optimistic update
      set(state => ({
        strategies: state.strategies.map(s => 
          s.id === id ? { ...s, status } : s
        )
      }));
    } catch (e) {
      console.error(e);
      get().fetchStrategies(); // Revert on error
    }
  },
  
  clearGeneratedCode: () => set({ generatedCode: '' })
}));
