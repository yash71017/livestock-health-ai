import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Typography, Chip
} from '@mui/material';
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined';
import HealingOutlinedIcon from '@mui/icons-material/HealingOutlined';
import WaterDropOutlinedIcon from '@mui/icons-material/WaterDropOutlined';
import PetsOutlinedIcon from '@mui/icons-material/PetsOutlined';
import HubOutlinedIcon from '@mui/icons-material/HubOutlined';
import CircleIcon from '@mui/icons-material/Circle';

import DashboardPage from './pages/Dashboard';
import DiagnosisPage from './pages/DiagnosisForm';
import MilkYieldPage from './pages/MilkYield';
import GraphPage from './pages/GraphVisualization';
import AnimalsPage from './pages/Animals';

const DRAWER_WIDTH = 248;
const PINE = '#1F5244';
const OCHRE_LIGHT = '#E0B06A';

const navItems = [
  { text: 'Dashboard', icon: <DashboardOutlinedIcon />, path: '/' },
  { text: 'Diagnosis', icon: <HealingOutlinedIcon />, path: '/diagnosis' },
  { text: 'Milk Yield', icon: <WaterDropOutlinedIcon />, path: '/milk' },
  { text: 'Animals', icon: <PetsOutlinedIcon />, path: '/animals' },
  { text: 'Knowledge Graph', icon: <HubOutlinedIcon />, path: '/graph' },
];

// Page titles keyed by route, shown in the top bar
const pageTitles = {
  '/': 'Dashboard',
  '/diagnosis': 'Disease Diagnosis',
  '/milk': 'Milk Yield Estimator',
  '/animals': 'Animals',
  '/graph': 'Knowledge Graph',
};

function Sidebar() {
  const location = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: PINE,
          color: '#EAF2EE',
          border: 'none',
          px: 1.75,
          py: 2.75,
        },
      }}
    >
      {/* Brand */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 1.25, pb: 2.75 }}>
        <Box
          sx={{
            width: 34, height: 34, borderRadius: '9px',
            background: `linear-gradient(140deg, #C4893D, #A06F2E)`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 18, flexShrink: 0,
          }}
        >
          🌿
        </Box>
        <Box>
          <Typography sx={{ fontFamily: '"Fraunces", serif', fontWeight: 600, fontSize: 18, lineHeight: 1.1, color: '#fff' }}>
            Livestock Health
          </Typography>
          <Typography sx={{ fontSize: 11, color: 'rgba(234,242,238,0.55)', mt: '1px' }}>
            Decision support
          </Typography>
        </Box>
      </Box>

      {/* Nav */}
      <List sx={{ display: 'flex', flexDirection: 'column', gap: 0.4 }}>
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.text}
              component={Link}
              to={item.path}
              disableRipple
              sx={{
                borderRadius: '10px',
                py: 1.1,
                px: 1.5,
                position: 'relative',
                color: active ? '#fff' : 'rgba(234,242,238,0.72)',
                backgroundColor: active ? 'rgba(255,255,255,0.10)' : 'transparent',
                '&:hover': { backgroundColor: 'rgba(255,255,255,0.06)', color: '#fff' },
                '&::before': active ? {
                  content: '""', position: 'absolute', left: -14, top: 9, bottom: 9,
                  width: 3, borderRadius: '0 3px 3px 0', backgroundColor: OCHRE_LIGHT,
                } : {},
              }}
            >
              <ListItemIcon sx={{ minWidth: 34, color: 'inherit', '& svg': { fontSize: 20 } }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.text}
                primaryTypographyProps={{ fontSize: 14.5, fontWeight: 500 }}
              />
            </ListItemButton>
          );
        })}
      </List>

      <Box sx={{ mt: 'auto', px: 1.25, pt: 1.5 }}>
        <Typography sx={{ fontSize: 11, color: 'rgba(234,242,238,0.4)' }}>
          v1.0 · Prototype
        </Typography>
      </Box>
    </Drawer>
  );
}

function TopBar() {
  const location = useLocation();
  const title = pageTitles[location.pathname] || 'Livestock Health';

  return (
    <Box
      sx={{
        height: 64,
        backgroundColor: 'background.paper',
        borderBottom: '1px solid',
        borderColor: 'divider',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 3.75,
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}
    >
      <Typography sx={{ fontFamily: '"Fraunces", serif', fontWeight: 600, fontSize: 22, letterSpacing: '-0.015em' }}>
        {title}
      </Typography>
      <Chip
        icon={<CircleIcon sx={{ fontSize: '9px !important', color: '#2E7D5B !important' }} />}
        label="Decision support — not veterinary advice"
        variant="outlined"
        size="small"
        sx={{ color: 'text.secondary', fontSize: 12.5 }}
      />
    </Box>
  );
}

function App() {
  return (
    <Router>
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>
        <Sidebar />
        <Box component="main" sx={{ flexGrow: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          <TopBar />
          <Box sx={{ p: { xs: 2, md: 3.75 }, maxWidth: 1200, width: '100%' }}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/diagnosis" element={<DiagnosisPage />} />
              <Route path="/milk" element={<MilkYieldPage />} />
              <Route path="/animals" element={<AnimalsPage />} />
              <Route path="/graph" element={<GraphPage />} />
            </Routes>
          </Box>
        </Box>
      </Box>
    </Router>
  );
}

export default App;
