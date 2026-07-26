import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Alert,
  CircularProgress, Chip, FormControl, InputLabel, Select, MenuItem,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper
} from '@mui/material';
import { animalAPI } from '../services/api';
import { ANIMAL_TYPES } from '../utils/constants';

function AnimalsPage() {
  const [animals, setAnimals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterType, setFilterType] = useState('');

  useEffect(() => {
    setLoading(true);
    animalAPI.getAll(filterType || undefined)
      .then((res) => setAnimals(res.data || []))
      .catch(() => setError('Could not load animals. Is the backend running?'))
      .finally(() => setLoading(false));
  }, [filterType]);

  return (
    <Box>

      <FormControl sx={{ mb: 3, minWidth: 200 }}>
        <InputLabel>Filter by Type</InputLabel>
        <Select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          label="Filter by Type"
        >
          <MenuItem value="">All</MenuItem>
          {ANIMAL_TYPES.map((t) => (
            <MenuItem key={t} value={t}>{t}</MenuItem>
          ))}
        </Select>
      </FormControl>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box display="flex" justifyContent="center" mt={4}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><strong>ID</strong></TableCell>
                <TableCell><strong>Type</strong></TableCell>
                <TableCell><strong>Breed</strong></TableCell>
                <TableCell><strong>Age</strong></TableCell>
                <TableCell><strong>Gender</strong></TableCell>
                <TableCell><strong>Weight (kg)</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {animals.map((a) => (
                <TableRow key={a.id} hover>
                  <TableCell>{a.id}</TableCell>
                  <TableCell>
                    <Chip label={a.type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>{a.breed}</TableCell>
                  <TableCell>{a.age}</TableCell>
                  <TableCell>{a.gender}</TableCell>
                  <TableCell>{a.weight}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
        {animals.length} animals{filterType ? ` (${filterType})` : ''}
      </Typography>
    </Box>
  );
}

export default AnimalsPage;
