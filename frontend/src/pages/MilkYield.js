import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, TextField, Button,
  Grid, Alert, CircularProgress, FormControl, InputLabel,
  Select, MenuItem
} from '@mui/material';
import { milkAPI, vocabAPI } from '../services/api';

function MilkYieldPage() {
  const [breed, setBreed] = useState('');
  const [age, setAge] = useState('');
  const [weight, setWeight] = useState('');
  const [breeds, setBreeds] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Try to load known breeds from a previous result or hardcode common ones
    setBreeds(['Holstein', 'Jersey', 'Sahiwal', 'Gir', 'Hereford', 'Angus', 'Murrah']);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!age || !weight) {
      setError('Age and weight are required');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const res = await milkAPI.estimate({
        breed: breed || 'Unknown',
        age: parseFloat(age),
        weight: parseFloat(weight),
      });
      setResult(res.data);
      // Update breeds list from API response
      if (res.data.knownBreeds) {
        setBreeds(res.data.knownBreeds);
      }
    } catch (err) {
      setError('Estimation failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setBreed('');
    setAge('');
    setWeight('');
    setResult(null);
    setError('');
  };

  return (
    <Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        Estimates daily milk yield based on breed, age, and weight.
        Actual yield depends on nutrition, lactation stage, health, and environment.
      </Alert>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3}>
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Animal Details
              </Typography>

              <Box component="form" onSubmit={handleSubmit}>
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Breed</InputLabel>
                  <Select
                    value={breed}
                    onChange={(e) => setBreed(e.target.value)}
                    label="Breed"
                  >
                    {breeds.map((b) => (
                      <MenuItem key={b} value={b}>{b}</MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  label="Age (years)"
                  type="number"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  sx={{ mb: 2 }}
                  inputProps={{ min: 1, max: 20 }}
                />

                <TextField
                  fullWidth
                  label="Weight (kg)"
                  type="number"
                  value={weight}
                  onChange={(e) => setWeight(e.target.value)}
                  sx={{ mb: 3 }}
                  inputProps={{ min: 5, max: 1200 }}
                />

                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={loading}
                    size="large"
                  >
                    {loading ? <CircularProgress size={24} /> : 'Estimate Yield'}
                  </Button>
                  <Button variant="outlined" onClick={handleReset}>
                    Reset
                  </Button>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={7}>
          {result && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Estimated Daily Yield
                </Typography>

                <Box
                  sx={{
                    p: 4,
                    textAlign: 'center',
                    backgroundColor: '#e8f5e9',
                    borderRadius: 2,
                    border: '2px solid #4caf50',
                    mb: 2,
                  }}
                >
                  <Typography variant="h2" sx={{ fontWeight: 'bold', color: '#2e7d32' }}>
                    {result.estimatedYield}
                  </Typography>
                  <Typography variant="h6" color="textSecondary">
                    litres / day
                  </Typography>
                </Box>

                {result.datasetRange && (
                  <Typography variant="body2" color="textSecondary" sx={{ mb: 1 }}>
                    Dataset range: {result.datasetRange.min} – {result.datasetRange.max} L/day
                    (mean: {result.datasetRange.mean?.toFixed(1)})
                  </Typography>
                )}

                {!result.breedRecognized && (
                  <Alert severity="warning" sx={{ mt: 1 }}>
                    Breed "{result.breed}" was not in the training data.
                    Estimate may be less reliable.
                  </Alert>
                )}

                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="caption">{result.disclaimer}</Typography>
                </Alert>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}

export default MilkYieldPage;
