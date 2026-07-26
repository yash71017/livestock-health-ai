import React, { useState, useEffect } from 'react';
import {
  Grid, Card, CardContent, Typography, Box, Alert, CircularProgress
} from '@mui/material';
import PetsOutlinedIcon from '@mui/icons-material/PetsOutlined';
import CoronavirusOutlinedIcon from '@mui/icons-material/CoronavirusOutlined';
import VaccinesOutlinedIcon from '@mui/icons-material/VaccinesOutlined';
import WaterDropOutlinedIcon from '@mui/icons-material/WaterDropOutlined';
import { statsAPI } from '../services/api';

// Colour tokens (kept local so this page is self-contained)
const PINE = '#1F5244';
const PINE_LIGHT = '#3C7A68';
const OCHRE = '#C4893D';
const SEG_COLORS = [PINE, PINE_LIGHT, OCHRE, '#7BA895', '#D9B77A'];

function StatCard({ icon, label, value, tint, iconColor }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box
          sx={{
            width: 40, height: 40, borderRadius: '11px', mb: 1.75,
            backgroundColor: tint, display: 'flex', alignItems: 'center', justifyContent: 'center',
            '& svg': { fontSize: 21, color: iconColor },
          }}
        >
          {icon}
        </Box>
        <Typography sx={{ fontSize: 12.5, color: 'text.secondary', fontWeight: 500, mb: 0.6 }}>
          {label}
        </Typography>
        <Typography sx={{ fontFamily: '"Fraunces", serif', fontWeight: 600, fontSize: 34, letterSpacing: '-0.02em', lineHeight: 1 }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    statsAPI.getStats()
      .then((res) => setStats(res.data))
      .catch(() => setError('Could not load dashboard stats. Is the backend running?'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" mt={6}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const cards = [
    { label: 'Total animals', value: stats?.totalAnimals ?? '—', tint: 'rgba(31,82,68,0.12)', iconColor: PINE, icon: <PetsOutlinedIcon /> },
    { label: 'Diseases tracked', value: stats?.totalDiseases ?? '—', tint: 'rgba(180,67,44,0.12)', iconColor: '#B4432C', icon: <CoronavirusOutlinedIcon /> },
    { label: 'Symptoms', value: stats?.totalSymptoms ?? '—', tint: 'rgba(196,137,61,0.14)', iconColor: '#A06F2E', icon: <VaccinesOutlinedIcon /> },
    {
      label: 'Avg milk yield',
      value: stats?.avgMilkYield
        ? <>{stats.avgMilkYield}<Typography component="span" sx={{ fontSize: 16, fontWeight: 600, color: 'text.secondary', ml: 0.4 }}>L/day</Typography></>
        : '—',
      tint: 'rgba(46,125,91,0.12)', iconColor: '#2E7D5B', icon: <WaterDropOutlinedIcon />,
    },
  ];

  const types = stats?.animalTypes || [];
  const total = types.reduce((s, t) => s + t.count, 0) || 1;

  return (
    <Box>
      <Alert severity="info" sx={{ mb: 3 }}>
        Decision-support prototype built on synthetic data. Predictions should not replace professional veterinary advice.
      </Alert>

      {/* Stat cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {cards.map((c) => (
          <Grid item xs={12} sm={6} md={3} key={c.label}>
            <StatCard {...c} />
          </Grid>
        ))}
      </Grid>

      {/* Animals by type — segmented bar */}
      {types.length > 0 && (
        <Card>
          <CardContent>
            <Typography sx={{ fontSize: 15, fontWeight: 700, mb: 2 }}>
              Animals by type
            </Typography>

            <Box sx={{ display: 'flex', height: 12, borderRadius: 999, overflow: 'hidden', mb: 2 }}>
              {types.map((t, i) => (
                <Box
                  key={t.type}
                  sx={{ width: `${(t.count / total) * 100}%`, backgroundColor: SEG_COLORS[i % SEG_COLORS.length] }}
                />
              ))}
            </Box>

            <Box sx={{ display: 'flex', gap: 2.5, flexWrap: 'wrap' }}>
              {types.map((t, i) => (
                <Box key={t.type} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box sx={{ width: 11, height: 11, borderRadius: '3px', backgroundColor: SEG_COLORS[i % SEG_COLORS.length] }} />
                  <Typography sx={{ fontSize: 13, color: 'text.secondary' }}>
                    {t.type} <Box component="span" sx={{ color: 'text.primary', fontWeight: 600 }}>{t.count}</Box>
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

export default Dashboard;
