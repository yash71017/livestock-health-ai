import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Alert, CircularProgress,
  Chip, FormControl, InputLabel, Select, MenuItem, Grid, Paper
} from '@mui/material';
import { graphAPI } from '../services/api';

function GraphVisualization() {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterType, setFilterType] = useState('');

  useEffect(() => {
    setLoading(true);
    graphAPI.getGraphData(filterType || undefined)
      .then((res) => setGraphData(res.data))
      .catch(() => setError('Could not load graph data.'))
      .finally(() => setLoading(false));
  }, [filterType]);

  const nodesByType = {};
  if (graphData?.nodes) {
    graphData.nodes.forEach((n) => {
      const label = n.label || 'Unknown';
      if (!nodesByType[label]) nodesByType[label] = [];
      nodesByType[label].push(n);
    });
  }

  const relTypes = {};
  if (graphData?.links) {
    graphData.links.forEach((l) => {
      const t = l.relationship || 'UNKNOWN';
      relTypes[t] = (relTypes[t] || 0) + 1;
    });
  }

  return (
    <Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        Neo4j-backed graph showing relationships between animals, diseases, and symptoms.
        This data powers the graph-enriched diagnosis results.
      </Alert>

      <FormControl sx={{ mb: 3, minWidth: 200 }}>
        <InputLabel>Filter by Node Type</InputLabel>
        <Select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          label="Filter by Node Type"
        >
          <MenuItem value="">All (sampled)</MenuItem>
          <MenuItem value="Animal">Animals</MenuItem>
          <MenuItem value="Disease">Diseases</MenuItem>
          <MenuItem value="Symptom">Symptoms</MenuItem>
          <MenuItem value="MilkRecord">Milk Records</MenuItem>
        </Select>
      </FormControl>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {/* Summary stats */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Graph Summary</Typography>
                <Typography>Nodes: {graphData?.nodes?.length || 0}</Typography>
                <Typography>Relationships: {graphData?.links?.length || 0}</Typography>

                <Typography variant="subtitle2" sx={{ mt: 2 }}>
                  Node Types
                </Typography>
                {Object.entries(nodesByType).map(([type, nodes]) => (
                  <Chip
                    key={type}
                    label={`${type}: ${nodes.length}`}
                    sx={{ m: 0.5 }}
                    variant="outlined"
                    color={
                      type === 'Animal' ? 'primary' :
                      type === 'Disease' ? 'error' :
                      type === 'Symptom' ? 'warning' : 'default'
                    }
                  />
                ))}

                <Typography variant="subtitle2" sx={{ mt: 2 }}>
                  Relationship Types
                </Typography>
                {Object.entries(relTypes).map(([type, count]) => (
                  <Chip
                    key={type}
                    label={`${type}: ${count}`}
                    sx={{ m: 0.5 }}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </CardContent>
            </Card>
          </Grid>

          {/* Node list */}
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Nodes</Typography>
                <Box sx={{ maxHeight: 500, overflow: 'auto' }}>
                  {Object.entries(nodesByType).map(([type, nodes]) => (
                    <Box key={type} sx={{ mb: 2 }}>
                      <Typography variant="subtitle2" color="primary" gutterBottom>
                        {type} ({nodes.length})
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {nodes.slice(0, 50).map((n) => (
                          <Chip
                            key={n.id}
                            label={n.name}
                            size="small"
                            variant="outlined"
                          />
                        ))}
                        {nodes.length > 50 && (
                          <Chip label={`+${nodes.length - 50} more`} size="small" />
                        )}
                      </Box>
                    </Box>
                  ))}
                </Box>

                <Paper sx={{ p: 2, mt: 2, textAlign: 'center', backgroundColor: '#f5f5f5' }}>
                  <Typography variant="body2" color="textSecondary">
                    Interactive D3.js force graph visualization planned for Tier 2.
                    Current view shows graph structure and contents.
                  </Typography>
                </Paper>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default GraphVisualization;
