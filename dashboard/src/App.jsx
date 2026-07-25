import React, { useState, Suspense } from 'react';
import TabNav from './components/TabNav';
import LoadingSpinner from './components/LoadingSpinner';

// ── Lazy-loaded pages ──
const CoachingPage      = React.lazy(() => import('./pages/CoachingPage'));
const RevenuePage       = React.lazy(() => import('./pages/RevenuePage'));
const OpportunityPage   = React.lazy(() => import('./pages/OpportunityPage'));
const KeywordPage       = React.lazy(() => import('./pages/KeywordPage'));
const SitePage          = React.lazy(() => import('./pages/SitePage'));
const ScoutPage         = React.lazy(() => import('./pages/ScoutPage'));
const SeniorPage        = React.lazy(() => import('./pages/SeniorPage'));
const CpcHintPage       = React.lazy(() => import('./pages/CpcHintPage'));

const PAGES = [
  CoachingPage, RevenuePage, OpportunityPage,
  KeywordPage, SitePage, ScoutPage, CpcHintPage, SeniorPage,
];

function App() {
  const [tab, setTab] = useState(0);
  const ActivePage = PAGES[tab];

  return (
    <div style={{
      maxWidth: 1000, margin: '0 auto', padding: '16px 20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    }}>
      <h1 style={{ fontSize: 22, marginBottom: 16, fontWeight: 700 }}>Blogdex</h1>
      <TabNav activeTab={tab} onTabChange={setTab} />
      <Suspense fallback={<LoadingSpinner />}>
        <ActivePage />
      </Suspense>
    </div>
  );
}

export default App;
