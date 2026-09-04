import { create } from 'zustand';

interface UIState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  setSidebar: (v: boolean) => void;
  watchlist: string;
  setWatchlist: (w: string) => void;
  searchOpen: boolean;
  setSearchOpen: (v: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebar: (v) => set({ sidebarCollapsed: v }),
  watchlist: 'Energy Core',
  setWatchlist: (w) => set({ watchlist: w }),
  searchOpen: false,
  setSearchOpen: (v) => set({ searchOpen: v }),
}));
