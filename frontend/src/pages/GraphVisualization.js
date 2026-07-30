import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Alert, CircularProgress,
  Chip, Grid, Tabs, Tab
} from '@mui/material';
import { graphAPI, networkAPI } from '../services/api';
import ForceGraph from '../components/ForceGraph';

function GraphVisualization() {
  const [tab, setTab] = useState(0);

  // Network view (force graph)
  const [network, setNetwork] = useState(null);
  const [netLoading, setNetLoading] = useState(true);
  const [netError, setNetError] = useState('');

  // Structure view (counts and contents)
  const [graphData, setGraphData] = useState(null);
  const [structLoading, setStructLoading] = useState(true);

  useEffect(() => {
    networkAPI.getNetwork()
      .then((res) => setNetwork(res.data))
      .catch(() => setNetError('Could not load the graph network.'))
      .finally(() => setNetLoading(false));

    graphAPI.getGraphData()
      .then((res) => setGraphData(res.data))
      .catch(() => {})
      .finally(() => setStructLoading(false));
  }, []);

  const nodesByType = {};
  if (graphData?.nodes) {
    graphData.nodes.forEach((n) => {
      const label = n.label || 'Unknown';
      if (!nodesByType[label]) nodesByType[label] = [];
      nodesByType[label].push(n);
    });
  }

  // Hub symptoms — the ones shared by the most diseases
  const hubs = network?.nodes
    ? network.nodes
        .filter((n) => n.type === 'symptom')
        .sort((a, b) => b.degree - a.degree)
    : [];

  return (
    <Box>
      <Alert severity="info" sx={{ mb: 2 }}>
        Live view of the Neo4j knowledge graph. Diseases connect to the symptoms
        they present with — the denser the centre, the harder those diseases are
        to tell apart from symptoms alone.
      </Alert>

      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Network" />
        <Tab label="Contents" />
      </Tabs>

      {/* ── Network view ── */}
      {tab === 0 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                {netLoading ? (
                  <Box display="flex" justifyContent="center" py={8}>
                    <CircularProgress />
                  </Box>
                ) : netError ? (
                  <Alert severity="error">{netError}</Alert>
                ) : (
                  <ForceGraph data={network} />
                )}
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography sx={{ fontSize: 15, fontWeight: 700, mb: 1.5 }}>
                  Network
                </Typography>
                {network?.summary && (
                  <>
                    <Row label="Diseases" value={network.summary.diseases} />
                    <Row label="Symptoms" value={network.summary.symptoms} />
                    <Row label="Connections" value={network.summary.connections} />
                  </>
                )}
              </CardContent>
            </Card>

            {hubs.length > 0 && (
              <Card>
                <CardContent>
                  <Typography sx={{ fontSize: 15, fontWeight: 700, mb: 0.5 }}>
                    Symptom reach
                  </Typography>
                  <Typography sx={{ fontSize: 12.5, color: 'text.secondary', mb: 1.5 }}>
                    How many diseases each symptom appears in. Widely shared
                    symptoms carry little diagnostic information.
                  </Typography>
                  {hubs.map((h) => (
                    <Box key={h.id} sx={{ mb: 0.9 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.3 }}>
                        <Typography sx={{ fontSize: 12.5 }}>{h.label}</Typography>
                        <Typography sx={{ fontSize: 12.5, color: 'text.secondary' }}>
                          {h.degree}
                        </Typography>
                      </Box>
                      <Box sx={{ height: 5, borderRadius: 999, backgroundColor: 'rgba(27,36,31,.08)' }}>
                        <Box
                          sx={{
                            height: '100%', borderRadius: 999,
                            width: `${(h.degree / (hubs[0]?.degree || 1)) * 100}%`,
                            backgroundColor: h.degree > 15 ? '#C4893D' : '#3C7A68',
                          }}
                        />
                      </Box>
                    </Box>
                  ))}
                </CardContent>
              </Card>
            )}
          </Grid>
        </Grid>
      )}

      {/* ── Contents view ── */}
      {tab === 1 && (
        <Card>
          <CardContent>
            {structLoading ? (
              <Box display="flex" justifyContent="center" py={6}>
                <CircularProgress />
              </Box>
            ) : (
              <Box sx={{ maxHeight: 560, overflow: 'auto' }}>
                {Object.entries(nodesByType).map(([type, nodes]) => (
                  <Box key={type} sx={{ mb: 2.5 }}>
                    <Typography sx={{ fontSize: 13, fontWeight: 700, color: 'primary.main', mb: 1 }}>
                      {type} ({nodes.length})
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                      {nodes.slice(0, 60).map((n) => (
                        <Chip key={n.id} label={n.name} size="small" variant="outlined" />
                      ))}
                      {nodes.length > 60 && (
                        <Chip label={`+${nodes.length - 60} more`} size="small" />
                      )}
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
}

function Row({ label, value }) {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
      <Typography sx={{ fontSize: 13.5, color: 'text.secondary' }}>{label}</Typography>
      <Typography sx={{ fontSize: 13.5, fontWeight: 600 }}>{value}</Typography>
    </Box>
  );
}

export default GraphVisualization;
