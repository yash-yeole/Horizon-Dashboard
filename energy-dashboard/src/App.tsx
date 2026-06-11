import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AlertsProvider } from '@/context/AlertsProvider';
import { AppShell } from '@/components/layout/AppShell';
import { Dashboard } from '@/pages/Dashboard';
import { Crude } from '@/pages/Crude';
import { Products } from '@/pages/Products';
import { Freight } from '@/pages/Freight';
import { Macro } from '@/pages/Macro';
import { Weather } from '@/pages/Weather';
import { Inventories } from '@/pages/Inventories';
import { News } from '@/pages/News';
import { Analytics } from '@/pages/Analytics';
import { Alerts } from '@/pages/Alerts';
import { Settings } from '@/pages/Settings';

export default function App() {
  return (
    <AlertsProvider>
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/crude" element={<Crude />} />
          <Route path="/products" element={<Products />} />
          <Route path="/freight" element={<Freight />} />
          <Route path="/macro" element={<Macro />} />
          <Route path="/weather" element={<Weather />} />
          <Route path="/inventories" element={<Inventories />} />
          <Route path="/news" element={<News />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </AlertsProvider>
  );
}
